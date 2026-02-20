FROM python:3.11-slim-bookworm AS builder

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
RUN uv pip install --python .venv/bin/python pyinstaller && \
    .venv/bin/python -c "import uvicorn, fastapi; print('freeze env ok')" && \
    .venv/bin/python -m PyInstaller --clean --onefile --name label-verification \
      --hidden-import uvicorn \
      --hidden-import uvicorn.logging \
      --hidden-import uvicorn.loops.auto \
      --hidden-import uvicorn.protocols.http.auto \
      --hidden-import uvicorn.protocols.websockets.auto \
      --collect-all uvicorn \
      --collect-all fastapi \
      --collect-all starlette \
      --collect-all anyio \
      --collect-all pydantic \
      --collect-all pydantic_core \
      --add-data "web/index.html:web" \
      --add-data "logic/required_text.yaml:logic" \
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
