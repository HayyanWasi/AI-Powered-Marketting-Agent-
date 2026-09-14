FROM python:3.13-slim

WORKDIR /app

COPY pyproject.toml uv.lock* ./
RUN apt-get update && apt-get install -y imagemagick ffmpeg && rm -rf /var/lib/apt/lists/*
RUN pip install uv && uv sync --no-dev

COPY src/ src/

ENV PYTHONPATH=/app/src

EXPOSE 8000

CMD ["sh", "-c", "uv run uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
