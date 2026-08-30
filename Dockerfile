FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY sql ./sql

RUN pip install --no-cache-dir .

ENV SCHEMA_PATH=/app/sql/schema.sql
ENV EVOLUTE_CREDENTIALS=/data/credentials.json

CMD ["python", "-m", "evaconnect.poller"]
