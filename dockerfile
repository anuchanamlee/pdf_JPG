# ใช้ base image ตัวเล็ก
FROM python:3.11-slim

# ตั้งค่าทั่วไปให้ Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# ติดตั้ง system packages ที่จำเป็น
# - build-essential: กันกรณีต้องคอมไพล์ lib บางตัว
# - poppler-utils: เผื่ออนาคตจะใช้ pdfinfo/pdftoppm (ตอนนี้โค้ดนี้ยังไม่ใช้ก็ได้)
# - libglib2.0-0, libjpeg-dev, zlib1g-dev: เผื่อ Pillow / PyMuPDF ต้องใช้
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    poppler-utils \
    libglib2.0-0 \
    libjpeg-dev \
    zlib1g-dev \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# ตั้ง working dir
WORKDIR /app

# ติดตั้ง dependencies จาก requirements.txt
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ก๊อปโค้ดทั้งหมดเข้า container
# (ถ้าไฟล์หลักชื่อ main.py แบบในโค้ด ก็โอเคเลย)
COPY . .

# เปิดพอร์ต 8000 (เดี๋ยวเวลา run ค่อย map ข้างนอกเอง)
EXPOSE 8000

# รัน FastAPI ด้วย uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
