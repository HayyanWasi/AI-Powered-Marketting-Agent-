FROM python:3.13-slim AS builder

WORKDIR /app

COPY pyproject.toml uv.lock* ./
RUN pip install uv && uv sync --no-dev --no-install-project

COPY src/ src/

FROM python:3.13-slim AS runner

WORKDIR /app

COPY --from=builder /app /app

ENV PYTHONPATH=/app/src

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
