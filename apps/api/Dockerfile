FROM python:3.12-slim

# System deps for Playwright Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 \
    libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 \
    libcairo2 libasound2 libwayland-client0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml ./
COPY radar ./radar
COPY alembic.ini ./
COPY alembic ./alembic
RUN pip install --no-cache-dir .
RUN playwright install chromium

# Run migrations then start server
CMD alembic upgrade head && uvicorn radar.main:app --host 0.0.0.0 --port "${PORT:-8000}"
