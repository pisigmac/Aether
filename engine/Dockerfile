FROM python:3.12-slim

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml /app/pyproject.toml
COPY aether /app/aether
RUN pip install --no-cache-dir -e .

ENV AETHER_DATA_DIR=/data
EXPOSE 8000
CMD ["uvicorn", "aether.api:app", "--host", "0.0.0.0", "--port", "8000"]
