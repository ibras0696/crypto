"""Common dependency utilities: current user, role checks, Redis client, rate cache.

Includes helper to fetch and cache ticker prices from Binance public API.
"""
from __future__ import annotations
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from .database import get_session
from ..models import User
from .security import decode_token
from .config import settings
import httpx
import json
import re
import redis.asyncio as redis

security_scheme = HTTPBearer()

async def get_redis() -> redis.Redis:
    return redis.from_url(settings.REDIS_URL, decode_responses=True)

async def get_rate(pair: str, r: redis.Redis = Depends(get_redis)) -> float:
    """Get rate with validation & resilient fallback.

    Flow:
      1. Validate symbol (A-Z only) and allowed quote.
      2. Try short-term cache rate:<pair>.
      3. On miss: call Binance, update current and last_good.<pair>.
      4. If Binance fails: fallback to last_good:<pair> else 502.
    """
    symbol = pair.upper()
    if not re.fullmatch(r"[A-Z0-9]{5,15}", symbol):
        raise HTTPException(status_code=400, detail="Bad symbol")
    if not any(symbol.endswith(q) for q in settings.ALLOWED_RATE_QUOTES):
        raise HTTPException(status_code=400, detail="Quote not allowed")
    cur_key = f"rate:{symbol}"
    cached = await r.get(cur_key)
    if cached:
        try:
            return float(json.loads(cached)["price"])
        except Exception:
            pass
    base_url = settings.BINANCE_PUBLIC_URL
    url = f"{base_url}/api/v3/ticker/price?symbol={symbol}"
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            price = float(data.get("price"))
            payload = json.dumps({"price": price})
            await r.set(cur_key, payload, ex=settings.RATE_CACHE_TTL)
            await r.set(f"last_good:{symbol}", payload)
            return price
    except Exception:
        fallback = await r.get(f"last_good:{symbol}")
        if fallback:
            try:
                return float(json.loads(fallback)["price"])
            except Exception:
                pass
        raise HTTPException(status_code=502, detail="Rate provider error (no fallback)")

async def current_user(creds: HTTPAuthorizationCredentials = Depends(security_scheme), db: AsyncSession = Depends(get_session)) -> User:
    token_data = decode_token(creds.credentials)
    if not token_data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    res = await db.execute(select(User).where(User.id == int(token_data.sub)))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def require_roles(*roles: str):
    async def checker(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient role")
        return user
    return checker
