FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate && python manage.py seed_data && celery -A project worker --loglevel=info & gunicorn project.wsgi:application --bind 0.0.0.0:8000"]
