FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Build + runtime libs needed while freezing the app.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libglib2.0-0 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

# Build a single executable entrypoint from main.py
RUN uv run pip install --no-cache-dir pyinstaller && \
    uv run pyinstaller --clean --onefile --name label-verification \
      --add-data "web/index.html:web" \
      main.py


FROM debian:bookworm-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Minimal shared libs required by OCR/image stack at runtime.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    libglib2.0-0 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/dist/label-verification /app/label-verification

EXPOSE 8001

CMD ["/app/label-verification"]
