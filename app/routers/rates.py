"""Rates and pairs router with dynamic Binance-backed rates cached in Redis."""
from __future__ import annotations
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from ..core.database import get_session
from sqlalchemy import select
from ..models import Currency
from ..core.deps import get_rate

router = APIRouter(prefix="/public", tags=["public"])  # /public/rates, /public/pairs


@router.get("/rates")
async def get_rates(
    symbols: list[str] | None = Query(None, description="Specific symbols like BTCUSDT,ETHUSDT"),
    db: AsyncSession = Depends(get_session),
):
    """Return validated rates (with Redis+Binance + fallback).

    If no symbols provided: build CODE<quote> (quote from ALLOWED_RATE_QUOTES) using first allowed quote present in DB (e.g. USDT).
    Invalid symbols return value None rather than failing entire response.
    """
    if symbols is None:
        res = await db.execute(select(Currency.code))
        codes = [c for (c,) in res.all()]
        if "USDT" not in codes:
            return {}
        symbols = [f"{c}USDT" for c in codes if c != "USDT"]
    rates = {}
    for sym in symbols:
        try:
            rate = await get_rate(sym)
            rates[sym] = rate
        except Exception:
            rates[sym] = None
    return rates


@router.get("/pairs")
async def get_pairs(db: AsyncSession = Depends(get_session)):
    res = await db.execute(select(Currency))
    codes = [c.code for c in res.scalars().all()]
    return {"pairs": [f"{a}-{b}" for a in codes for b in codes if a != b]}
