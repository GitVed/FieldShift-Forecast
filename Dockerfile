FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend backend
COPY data/seed data/seed
# Daily IMERG and POWER evidence (Predict and season replay) and projection metadata.
COPY data/source data/source
COPY data/metadata data/metadata
COPY frontend frontend
CMD ["sh", "-c", "python -m backend.seed && exec uvicorn backend.app:app --host 0.0.0.0 --port 8000"]
