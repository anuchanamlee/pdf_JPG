from fastapi import FastAPI, UploadFile, File, Query, HTTPException
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool

import io, zipfile, logging, gc, tempfile
from PIL import Image

# --- Safe import PyMuPDF ---
try:
    import fitz  # PyMuPDF
except ImportError:
    import pymupdf as fitz

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pdf2jpg")

app = FastAPI(title="PDF to JPG API (PyMuPDF)")

MAX_MB = 50  # กันไฟล์ใหญ่เกิน

# ---- Safety limits (กัน RAM แตก) ----
DEFAULT_DPI = 250
MAX_DPI = 600  # ยังรับ param ได้ แต่จะ scale ให้ไม่เกิน limit
MAX_WIDTH_PX  = 2500
MAX_HEIGHT_PX = 3500
MAX_PIXELS    = 12_000_000  # ~12MP ต่อหน้า (กันหน้าละ 100MB+)
SPOOL_MAX_MB  = 64          # zip เกินนี้จะ spill ลง disk

def safe_pixmap(page: fitz.Page, dpi: int, grayscale: bool) -> fitz.Pixmap:
    """
    Render pixmap แบบคุมขนาดสูงสุดต่อหน้า
    - ใช้ matrix แทน dpi เพื่อปรับ scale ลงได้
    - เลือก colorspace ตาม grayscale
    """
    # clamp dpi เบื้องต้น (กันคนยิง dpi บ้าๆ)
    dpi = max(72, min(dpi, MAX_DPI))
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)

    rect = page.rect
    w = int(rect.width * zoom)
    h = int(rect.height * zoom)

    # scale ตาม max width/height
    scale_wh = min(MAX_WIDTH_PX / w, MAX_HEIGHT_PX / h, 1.0)

    # scale ตาม max pixels
    px = w * h
    scale_px = (MAX_PIXELS / px) ** 0.5 if px > MAX_PIXELS else 1.0

    scale = min(scale_wh, scale_px)
    if scale < 1.0:
        mat = fitz.Matrix(zoom * scale, zoom * scale)
        w = int(w * scale)
        h = int(h * scale)

    cs = fitz.csGRAY if grayscale else fitz.csRGB
    return page.get_pixmap(matrix=mat, colorspace=cs, alpha=False)

def pixmap_to_pil(pix: fitz.Pixmap, grayscale: bool) -> Image.Image:
    """
    Pixmap -> PIL
    - ถ้า grayscale เรากำหนด csGRAY มาแล้ว => mode L ได้เลย
    - ถ้า RGB ไม่ใช่ 3 ช่อง/มี alpha => แปลงเป็น RGB
    """
    if grayscale:
        # pix จะเป็น Gray อยู่แล้ว
        return Image.frombytes("L", (pix.width, pix.height), pix.samples)

    # RGB path
    try:
        if pix.alpha or pix.n >= 4 or pix.colorspace is None or pix.colorspace.n != 3:
            pix = fitz.Pixmap(fitz.csRGB, pix)
    except Exception:
        pix = fitz.Pixmap(fitz.csRGB, pix)

    return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

def pdf_to_jpg_zip( 
    pdf_bytes: bytes,
    dpi: int,
    quality: int,
    grayscale: bool,
    page_start: int | None = None,
    page_end: int | None = None,
):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        # password protected?
        if getattr(doc, "needs_pass", False):
            ok = doc.authenticate("")
            if not ok:
                raise ValueError("PDF is password-protected")

        total_pages = doc.page_count

        # normalize range (1-based inclusive)
        ps = page_start or 1
        pe = page_end or total_pages
        if ps < 1 or pe < 1 or ps > pe:
            raise ValueError("Invalid page range")
        if ps > total_pages:
            raise ValueError("page_start exceeds page count")
        pe = min(pe, total_pages)

        # clamp quality (กันไฟล์ใหญ่เกินจำเป็น)
        quality = max(60, min(quality, 95))

        # zip buffer แบบ spooled (spill ลง disk ถ้าใหญ่)
        zip_buf = tempfile.SpooledTemporaryFile(
            max_size=SPOOL_MAX_MB * 1024 * 1024, mode="w+b"
        )

        with zipfile.ZipFile(zip_buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for idx in range(ps - 1, pe):
                page = doc[idx]

                pix = safe_pixmap(page, dpi=dpi, grayscale=grayscale)
                img = pixmap_to_pil(pix, grayscale=grayscale)

                # เขียนลง zip ตรงๆ ไม่ผ่าน img_buf.getvalue()
                name = f"page_{idx+1:03d}.jpg"
                with zf.open(name, "w") as fp:
                    img.save(
                        fp,
                        format="JPEG",
                        quality=quality,
                        optimize=True,
                        progressive=True,
                    )

                # free memory per-page
                del img, pix, page
                if (idx + 1) % 5 == 0:
                    gc.collect()

        zip_buf.seek(0)
        return zip_buf

    finally:
        doc.close()

@app.post(
    "/convert/pdf-to-jpg",
    responses={
        200: {
            "content": {"application/zip": {}},
            "description": "ZIP of JPG images for all pages",
        }
    },
)
async def convert_pdf_to_jpg(
    file: UploadFile = File(...),
    dpi: int = Query(DEFAULT_DPI, ge=72, le=MAX_DPI),
    quality: int = Query(90, ge=50, le=100),
    grayscale: bool = Query(False),
    page_start: int | None = Query(None, ge=1),
    page_end: int | None = Query(None, ge=1),
):
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(400, "Only PDF files are supported")

    pdf_bytes = await file.read()
    if len(pdf_bytes) > MAX_MB * 1024 * 1024:
        raise HTTPException(413, f"PDF too large (> {MAX_MB}MB)")
    if not pdf_bytes.startswith(b"%PDF"):
        raise HTTPException(400, "Invalid PDF header")

    try:
        zip_buf = await run_in_threadpool(
            pdf_to_jpg_zip,
            pdf_bytes,
            dpi,
            quality,
            grayscale,
            page_start,
            page_end,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    except fitz.FileDataError:
        raise HTTPException(400, "Corrupted or unreadable PDF")
    except Exception as e:
        logger.exception("Convert failed")
        raise HTTPException(500, f"Convert failed: {repr(e)}")

    headers = {"Content-Disposition": 'attachment; filename="pages.zip"'}
    return StreamingResponse(zip_buf, media_type="application/zip", headers=headers)
