"""FastAPI application entrypoint: mounts routes, creates tables on startup.
This is a simplified MVP version.
"""
from __future__ import annotations
from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
from .core.config import settings
from fastapi.middleware.cors import CORSMiddleware
from .core.database import engine, Base, get_session
from .routers import auth, orders, rates, currencies
from sqlalchemy.ext.asyncio import AsyncSession
import logging, time
from collections import defaultdict, deque
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("crypto")

app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG)
if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
app.include_router(auth.router)
app.include_router(orders.router)
app.include_router(rates.router)
app.include_router(currencies.router)

BASE_DIR = Path(__file__).resolve().parent  # .../app
templates_dir = BASE_DIR / "templates"
static_dir = BASE_DIR / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=str(templates_dir))

# --- Rate Limiter (simple in-memory, suitable only for single-process dev) ---
_rate_buckets: dict[str, deque] = defaultdict(deque)
_metrics = {
    "requests_total": 0,
    "requests_inflight": 0,
    "requests_by_path": defaultdict(int),
    "latency_ms_sum": 0.0,
}

@app.middleware("http")
async def rate_limit(request: Request, call_next):
    if not settings.RATE_LIMIT_ENABLED:
        return await call_next(request)
    # Skip static & health
    if request.url.path.startswith("/static") or request.url.path == "/health":
        return await call_next(request)
    ident = request.client.host  # could add token-based key
    now = time.time()
    window = 60
    limit = settings.RATE_LIMIT_PER_MINUTE
    dq = _rate_buckets[ident]
    while dq and now - dq[0] > window:
        dq.popleft()
    if len(dq) >= limit:
        return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
    dq.append(now)
    start = time.time()
    _metrics["requests_total"] += 1
    _metrics["requests_inflight"] += 1
    try:
        response = await call_next(request)
        return response
    finally:
        elapsed = (time.time() - start) * 1000
        _metrics["latency_ms_sum"] += elapsed
        _metrics["requests_by_path"][request.url.path] += 1
        _metrics["requests_inflight"] -= 1

# --- Global error handler (hide internals) ---
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/metrics")
async def metrics():
    if not settings.METRICS_ENABLED:
        return JSONResponse(status_code=404, content={"detail": "disabled"})
    return {
        "requests_total": _metrics["requests_total"],
        "requests_inflight": _metrics["requests_inflight"],
        "latency_ms_avg": (_metrics["latency_ms_sum"] / _metrics["requests_total"]) if _metrics["requests_total"] else 0,
        "requests_by_path": dict(_metrics["requests_by_path"]),
    }


@app.on_event("startup")
async def startup():
    logger.info("Startup - assume Alembic migrations applied externally")
    # Optional: seed basic currencies if empty (dev convenience)
    from sqlalchemy import select
    from .models.currency import Currency
    from .core.database import SessionLocal
    async with SessionLocal() as session:  # direct session (not dependency generator)
        res = await session.execute(select(Currency.id))
        if not res.first():
            logger.info("Seeding default currencies (BTC, USDT, ETH)")
            session.add_all([
                Currency(code="BTC", name="Bitcoin", reserve=10),
                Currency(code="USDT", name="Tether", reserve=100000),
                Currency(code="ETH", name="Ethereum", reserve=500),
            ])
            await session.commit()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    # Pass settings for frontend limits (UNVERIFIED_ORDER_MAX etc.)
    return templates.TemplateResponse("index.html", {"request": request, "settings": settings})


@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})


@app.get("/health")
async def health(db: AsyncSession = Depends(get_session)):
    # quick DB check
    try:
        await db.execute("SELECT 1")
        db_status = "up"
    except Exception:
        db_status = "down"
    # redis ping (optional)
    from .core.deps import get_redis
    try:
        r = await get_redis()
        await r.ping()
        redis_status = "up"
    except Exception:
        redis_status = "down"
    return {"status": "ok" if db_status=="up" and redis_status=="up" else "degraded", "db": db_status, "redis": redis_status}
