"""Currencies management router (admin/operator create/update reserves, list public)."""
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..core.database import get_session
from ..core import deps
from ..models import Currency
from ..schemas.currency import CurrencyRead, CurrencyUpdateReserve, CurrencyCreate

router = APIRouter(prefix="/currencies", tags=["currencies"])


@router.get("", response_model=list[CurrencyRead])
async def list_currencies(db: AsyncSession = Depends(get_session)):
    res = await db.execute(select(Currency))
    return list(res.scalars())


@router.post("", response_model=CurrencyRead, dependencies=[Depends(deps.require_roles("admin","operator"))])
async def create_currency(payload: CurrencyCreate, db: AsyncSession = Depends(get_session)):
    exists = await db.execute(select(Currency).where(Currency.code == payload.code))
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Code exists")
    cur = Currency(code=payload.code.upper(), name=payload.name, reserve=payload.reserve)
    db.add(cur)
    await db.commit()
    await db.refresh(cur)
    return cur


@router.patch("/{currency_id}", response_model=CurrencyRead, dependencies=[Depends(deps.require_roles("admin","operator"))])
async def update_reserve(currency_id: int, payload: CurrencyUpdateReserve, db: AsyncSession = Depends(get_session)):
    cur = await db.get(Currency, currency_id)
    if not cur:
        raise HTTPException(status_code=404, detail="Not found")
    cur.reserve = payload.reserve
    await db.commit()
    await db.refresh(cur)
    return cur
