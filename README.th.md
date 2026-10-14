
# PDF to JPG API (FastAPI + PyMuPDF)

API สำหรับแปลงไฟล์ **PDF → JPG** แบบหลายหน้าในครั้งเดียว  
ใช้ **FastAPI + PyMuPDF + Pillow** พร้อมระบบจำกัดขนาดภาพและไฟล์ เพื่อกัน RAM แตกและไฟล์ใหญ่เกินจำเป็น

---

## ✨ Features

- แปลง PDF ทุกหน้าเป็นรูป **JPG** แล้วรวมเป็นไฟล์ **ZIP** ให้ดาวน์โหลด
- รองรับ:
  - กำหนด **DPI** เอง (มี limit ป้องกันยิงค่าเกิน)
  - กำหนด **คุณภาพรูป (quality)** ของ JPEG
  - เลือกแปลงบางหน้า: `page_start`, `page_end`
  - แปลงเป็น **ขาวดำ (grayscale)** เพื่อลดขนาดไฟล์
- ปลอดภัยขึ้น:
  - เช็กขนาด PDF ไม่เกิน `MAX_MB` (ค่าเริ่มต้น 50MB)
  - เช็ก header ต้องเริ่มด้วย `%PDF`
  - ตรวจจับ PDF ที่ตั้งรหัสผ่าน
  - จำกัด resolution สูงสุดต่อหน้า (ตาม `MAX_WIDTH_PX`, `MAX_HEIGHT_PX`, `MAX_PIXELS`)
  - ใช้ `SpooledTemporaryFile` ให้ ZIP ใหญ่ ๆ spill ลงดิสก์แทนการอยู่ใน RAM ทั้งก้อน
- มี log ผ่าน `logging` (ชื่อ logger: `pdf2jpg`)

---

## 📂 โครงสร้างโปรเจกต์ (โดยสรุป)

```text
pdf_JPG/
├─ main.py             # โค้ด FastAPI + PDF→JPG logic (ตัวอย่างใน README นี้)
├─ requirements.txt    # dependencies
├─ Dockerfile          # ใช้ build image รัน API
└─ README.md
หมายเหตุ: ไฟล์หลักใน Dockerfile ใช้คำสั่ง uvicorn main:app ...
ชื่อไฟล์ Python หลักจึงควรเป็น main.py และตัวแปร FastAPI ต้องชื่อ app
```
## 🔧 Requirements
- ถ้ารันแบบไม่ใช้ Docker:

- Python 3.11+

- แนะนำให้ใช้ virtual environment (venv)

- ระบบมี pip สำหรับติดตั้งแพ็กเกจ

- Dependencies หลัก (ใน requirements.txt):

- fastapi

- uvicorn[standard]

- pymupdf หรือ PyMuPDF

- Pillow

- starlette

## 🚀 การติดตั้ง & รัน (แบบปกติ / ไม่ใช้ Docker)
### 1) Clone โปรเจกต์
```bash
git clone https://github.com/anuchanamlee/pdf_JPG.git
```
```bash
cd pdf_JPG
```
### 2) สร้างและเปิดใช้งาน virtualenv (แนะนำ)
#### Windows (PowerShell):


```bash
python -m venv venv
```
หรือ 
```bash
py -m venv venv
```
```bash
.\venv\Scripts\activate
```

### 3) ติดตั้ง dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```
### 4) รัน FastAPI ด้วย Uvicorn
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```
เสร็จแล้วจะสามารถเปิด docs ได้ที่:

- Swagger UI  : http://localhost:8000/docs

- ReDoc       : http://localhost:8000/redoc

## 🐳 การใช้งานผ่าน Docker
### 1) Build Docker image
```bash
docker build -t pdf-jpg-api .
```
###  2) รัน container
```bash
docker run -d --name pdf-jpg-api -p 8000:8000 pdf-jpg-api
```
ตอนนี้ API จะพร้อมใช้งานที่: http://localhost:8000/docs

Endpoint หลัก: POST http://localhost:8000/convert/pdf-to-jpg

## 📡 Endpoint
```
POST /convert/pdf-to-jpg
```
แปลงไฟล์ PDF เป็นรูป JPG ทั้งหมด (หรือบางหน้า) แล้วส่งกลับเป็น ZIP

Request

- ```Content-Type: multipart/form-data ```

- ```file: ไฟล์ PDF ```

## Query Parameters

| ชื่อ        | ชนิด          | ค่า default | ช่วงที่รับได้ | อธิบาย                                                        |
|------------|---------------|------------:|---------------|----------------------------------------------------------------|
| `dpi`      | `int`         | `250`       | `72–600`      | DPI สำหรับ render หน้ากระดาษ                                  |
| `quality`  | `int`         | `90`        | `50–100`      | คุณภาพ JPEG (ภายในฟังก์ชันจะ clamp 60–95 อีกที)              |
| `grayscale`| `bool`        | `false`     | `true/false`  | ถ้า `true` จะ render เป็นภาพขาวดำ (ลดขนาดไฟล์)                |
| `page_start` | `int \| None` | `None`    | `≥ 1`         | หน้าเริ่ม (1-based) ถ้าไม่ส่ง = หน้า 1                        |
| `page_end`   | `int \| None` | `None`    | `≥ 1`         | หน้าสิ้นสุด (1-based) ถ้าไม่ส่ง = หน้าสุดท้าย                |


### ข้อจำกัดเพิ่มเติมในโค้ด

- ขนาดไฟล์ PDF สูงสุด: MAX_MB MB (ค่าเริ่มต้น 50MB)

- ต้องเป็น PDF จริง (เช็กด้วย pdf_bytes.startswith(b"%PDF"))

- ถ้า PDF ถูกเข้ารหัสด้วยรหัสผ่านและ unlock ไม่ได้ → จะ error

- ถ้าระบุ page_start / page_end ผิด (เช่น > จำนวนหน้า, ติดลบ ฯลฯ) → HTTP 400

Response

- สถานะ: 200 OK

- Header: Content-Disposition: attachment; filename="pages.zip"

- Body: ไฟล์ ZIP ที่ภายในประกอบด้วย:
  - page_001.jpg
  - page_002.jpg
- MIME type: application/zip

## 🧪 ตัวอย่างการเรียกใช้งาน (cURL)
### 1) แปลงทั้งไฟล์
```bash
curl -X POST "http://localhost:8000/convert/pdf-to-jpg" \
  -H "accept: application/zip" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@sample.pdf;type=application/pdf" \
  --output pages.zip
```
### 2) แปลงเฉพาะบางหน้า + ตั้ง DPI และ quality
```bash
curl -X POST "http://localhost:8000/convert/pdf-to-jpg?dpi=250&quality=90&page_start=1&page_end=5" \
  -H "accept: application/zip" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@sample.pdf;type=application/pdf" \
  --output pages_1_5.zip
```
### 3) แปลงเป็นขาวดำ เพื่อลดขนาดไฟล์
```bash
curl -X POST "http://localhost:8000/convert/pdf-to-jpg?grayscale=true" \
  -H "accept: application/zip" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@sample.pdf;type=application/pdf" \
  --output pages_gray.zip
```
## 🧠 การออกแบบด้านประสิทธิภาพ & ความปลอดภัย (สรุปจากโค้ด)
- ใช้ ```bash safe_pixmap(...)``` เพื่อคุมไม่ให้ภาพใหญ่เกิน:

  - จำกัด DPI (`bash DEFAULT_DPI `, `MAX_DPI`)

  - จำกัดขนาดภาพสูงสุด: `MAX_WIDTH_PX`, `MAX_HEIGHT_PX`

  - จำกัดจำนวนพิกเซลต่อหน้า: `MAX_PIXELS` (เช่น ~12MP)

- ใช้ SpooledTemporaryFile สำหรับ ZIP:

  - ถ้า ZIP ยังเล็ก → อยู่บน RAM

  - ถ้าเกิน `SPOOL_MAX_MB` → spill ลงดิสก์อัตโนมัติ

- เคลียร์ memory ต่อหน้า:

  - `del img, pix, page`

  - เรียก `gc.collect()` ทุก ๆ 5 หน้า

- Handling error:

  - `ValueError` → HTTP 400 (บอกสาเหตุชัด)

  - `fitz.FileDataError` → PDF เสีย / อ่านไม่ได้ → HTTP 400

  - อื่น ๆ → HTTP 500 พร้อม log ผ่าน `logger.exception("Convert failed")`

## 🔗 ใช้งานร่วมกับระบบอื่น (เช่น n8n, Automation Tools)
API นี้เหมาะสำหรับใช้งานร่วมกับ:

- n8n / Node-RED / Zapier ผ่าน HTTP Request node

- Backend อื่น ๆ ที่ต้องการแปลง PDF ก่อนส่งไป OCR หรือ AI ภายนอก

ตัวอย่างการใช้ใน n8n (แนวคิด):

- Node: HTTP Request

  - Method: POST

  - URL: `http://your-host:8000/convert/pdf-to-jpg`

  - Content Type: `multipart/form-data`

  - Body:

    - Binary property: `file` (รับจาก node ก่อนหน้า เช่น Google Drive → Binary)

  - Response: File (ZIP) → สามารถแตกไฟล์ต่อ หรือส่งต่อให้ OCR/AI

