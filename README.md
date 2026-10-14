# PDF → JPG API

A small FastAPI service that renders every page (or a page range) of a PDF to JPEG
and returns them as one ZIP. Built to be called from automation tools such as n8n
before OCR or AI steps.

[ภาษาไทย](README.th.md)

## Why it exists

Converting PDFs is easy until someone uploads a 300-page scan at 600 DPI and the
container runs out of memory. This service caps the work per request instead of
trusting the input.

## Design decisions

| Risk | What the code does |
|---|---|
| Huge upload | Rejects PDFs over `MAX_MB` (50 MB) with HTTP 413 |
| Not really a PDF | Checks the `%PDF` header before opening |
| Huge page render | `safe_pixmap()` clamps DPI (72–600), width/height (2500×3500 px) and total pixels (~12 MP per page) |
| Huge ZIP in RAM | `SpooledTemporaryFile` spills to disk past 64 MB |
| Memory creep on long PDFs | Frees each page and runs `gc.collect()` every 5 pages |
| Password-protected PDF | Detected and returned as HTTP 400 |
| Bad input vs. server error | `ValueError` / corrupt PDF → 400 with a reason; anything else → 500 and a logged stack trace |

## Run

```bash
docker build -t pdf-jpg-api .
docker run -d -p 8000:8000 pdf-jpg-api
```

Or locally with Python 3.11+:

```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

Interactive docs: http://localhost:8000/docs

## API

`POST /convert/pdf-to-jpg` — `multipart/form-data` with field `file`. Returns `application/zip`
containing `page_001.jpg`, `page_002.jpg`, …

| Query param | Default | Range | Meaning |
|---|---|---|---|
| `dpi` | 250 | 72–600 | Render resolution (further capped by the pixel limits) |
| `quality` | 90 | 50–100 | JPEG quality |
| `grayscale` | false | | Render in grayscale for smaller files |
| `page_start` / `page_end` | first / last | ≥ 1 | 1-based page range |

```bash
curl -X POST "http://localhost:8000/convert/pdf-to-jpg?page_start=1&page_end=5&grayscale=true" \
  -F "file=@sample.pdf;type=application/pdf" \
  --output pages.zip
```

## Use from n8n

HTTP Request node → `POST http://<host>:8000/convert/pdf-to-jpg`, body type
*Form-Data*, binary field `file`, response format *File*.

## Stack

Python · FastAPI · PyMuPDF · Pillow · Docker

## License

MIT
