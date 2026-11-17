FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/static/uploads /app/backups

EXPOSE 4006

# Gunakan 1 worker + multi-thread agar aman untuk SQLite (menghindari database is locked)
CMD ["gunicorn", "-w", "1", "--threads", "4", "-b", "0.0.0.0:4006", "wsgi:app"]
