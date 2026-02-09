FROM python:3.10-slim

# منع بايثون من إنشاء ملفات مؤقتة وتأمين خروج الطباعة مباشرة للـ Logs
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# تحديث أسماء المكتبات لتناسب نسخة Debian الحديثة (Trixie)
RUN apt-get update --fix-missing && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# تثبيت المكتبات البرمجية
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# نسخ ملفات المشروع
COPY . .

# أمر التشغيل
CMD ["python", "app.py"]
