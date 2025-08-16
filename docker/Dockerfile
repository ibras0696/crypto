# Multi-stage Dockerfile for production build
FROM python:3.12-slim AS build
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && pip wheel --no-cache-dir --no-deps -r requirements.txt -w /wheels

# Stage for running tests (uses wheels to speed up)
FROM python:3.12-slim AS test
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY --from=build /wheels /wheels
RUN pip install --no-cache-dir /wheels/*
COPY . .
# Use SQLite for tests (override if needed) and disable rate limit for speed
ENV DATABASE_URL=sqlite+aiosqlite:///./test.db RATE_LIMIT_ENABLED=false
RUN pytest -q || (echo "Tests failed" && exit 1)

FROM python:3.12-slim AS final
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY --from=build /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && useradd -u 1001 appuser && mkdir -p /app && chown -R appuser /app
COPY . .
USER appuser
EXPOSE 8000
# Gunicorn with uvicorn workers
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 CMD python -c "import asyncio,sys,httpx;async def c():\n import os;u='http://127.0.0.1:8000/health';\n async with httpx.AsyncClient(timeout=5) as cli: r=await cli.get(u);\n sys.exit(0 if r.status_code==200 else 1)\n;asyncio.run(c())" || exit 1
CMD ["gunicorn", "crypto_exchange.app.main:app", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000", "--workers", "2", "--threads", "2", "--timeout", "60"]
