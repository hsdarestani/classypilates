FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py .
COPY feedback_app.py .
COPY class_language.py .
COPY studio_management.py .
COPY ui_polish.py .
COPY password_reset.py .
COPY runtime_app.py .
COPY import_mindbody_schedule.py .
COPY mindbody_api.py .
COPY mindbody_sync.py .
COPY data ./data
RUN mkdir -p /data/uploads
EXPOSE 8000
CMD ["uvicorn","runtime_app:app","--host","0.0.0.0","--port","8000","--proxy-headers"]
