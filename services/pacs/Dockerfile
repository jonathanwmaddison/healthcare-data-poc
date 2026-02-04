FROM python:3.11-slim

WORKDIR /app

COPY shared/requirements.txt .
RUN pip install --no-cache-dir minio python-multipart -r requirements.txt

COPY shared/ ./shared/
COPY services/pacs/app/ ./app/

ENV PYTHONPATH=/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
