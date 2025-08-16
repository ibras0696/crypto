"""Orders router: create and retrieve orders, admin status change."""
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..core.database import get_session
from ..models import Order, Currency, User
from ..schemas.order import OrderCreate, OrderRead, OrderStatusUpdate, VALID_STATUSES, TransactionCreate, TransactionRead
from ..core import deps
from ..core.deps import get_rate
from ..core.config import settings
from datetime import datetime, timedelta
from sqlalchemy import func
from ..services.orders import log_action, ensure_reserve_sufficient, deduct_reserve_once
import secrets

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("/analytics/summary")
async def orders_summary(days: int = 7, db: AsyncSession = Depends(get_session), _: User = Depends(deps.require_roles("admin","operator"))):
    """Return aggregated stats: total counts per status and daily volume for last N days."""
    days = max(1, min(days, 30))
    from datetime import datetime, timedelta
    since = datetime.utcnow() - timedelta(days=days)
    # counts per status
    from sqlalchemy import func
    status_rows = (await db.execute(select(Order.status, func.count(), func.coalesce(func.sum(Order.amount_to),0)).where(Order.created_at>=since).group_by(Order.status))).all()
    status_stats = {s: {"count": int(c), "volume": float(v)} for s,c,v in status_rows}
    # daily buckets
    # Fetch raw rows and bucket client-side (portable)
    rows = (await db.execute(select(Order.created_at, Order.amount_to).where(Order.created_at>=since))).all()
    buckets: dict[str,float] = {}
    for created_at, amt in rows:
        day_key = created_at.strftime('%Y-%m-%d')
        buckets[day_key] = buckets.get(day_key, 0.0) + float(amt)
    # ensure all days present
    for i in range(days):
        d = (since + timedelta(days=i)).strftime('%Y-%m-%d')
        buckets.setdefault(d, 0.0)
    daily = [{"date": k, "volume": buckets[k]} for k in sorted(buckets.keys())]
    return {"status": status_stats, "daily": daily}


@router.post("", response_model=OrderRead)
async def create_order(payload: OrderCreate, db: AsyncSession = Depends(get_session), user: User = Depends(deps.current_user)):
    """Create order using dynamic rate (Binance cache) if possible.

    amount_to = payload.amount_to or amount_from * rate
    """
    from_cur = await db.get(Currency, payload.from_currency)
    to_cur = await db.get(Currency, payload.to_currency)
    if not from_cur or not to_cur:
        raise HTTPException(status_code=404, detail="Currency not found")
    # attempt dynamic rate
    dynamic_rate = None
    symbol = f"{from_cur.code}{to_cur.code}".upper()
    try:
        dynamic_rate = await get_rate(symbol)
    except Exception:
        dynamic_rate = None
    rate = float(dynamic_rate) if dynamic_rate else 100.0  # fallback demo rate
    amount_to = payload.amount_to or payload.amount_from * rate
    # KYC limits for unverified users
    if user.kyc_status != "verified":
        if amount_to > settings.UNVERIFIED_ORDER_MAX:
            raise HTTPException(status_code=400, detail="Order limit exceeded (KYC required)")
        # daily volume check (sum of today's orders amount_to)
        start_day = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        q = select(func.coalesce(func.sum(Order.amount_to), 0)).where(
            Order.user_id == user.id, Order.created_at >= start_day
        )
        total_today = (await db.execute(q)).scalar()
        if float(total_today) + float(amount_to) > settings.UNVERIFIED_DAILY_VOLUME_MAX:
            raise HTTPException(status_code=400, detail="Daily volume limit exceeded (KYC required)")
    try:
        await ensure_reserve_sufficient(db, to_cur.id, amount_to)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    wallet_address = "demo_" + secrets.token_hex(8)
    # initial status flow: new -> pending_payment immediately (awaiting user transfer)
    order = Order(
        user_id=user.id,
        from_currency=from_cur.id,
        to_currency=to_cur.id,
        amount_from=payload.amount_from,
        amount_to=amount_to,
        rate=rate,
        wallet_address=wallet_address,
        payout_details=payload.payout_details,
        status="pending_payment",
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)
    await log_action(db, user.id, "order.create", f"order_id={order.id}")
    return order


@router.post("/{order_id}/transactions", response_model=TransactionRead)
async def create_transaction(order_id: int, payload: TransactionCreate, db: AsyncSession = Depends(get_session), user: User = Depends(deps.current_user)):
    order = await db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.user_id != user.id and user.role not in ("admin","operator"):
        raise HTTPException(status_code=403, detail="Forbidden")
    # create transaction
    from ..models.transaction import Transaction  # local import to avoid circular
    tx = Transaction(order_id=order.id, tx_hash=payload.tx_hash, amount=payload.amount, status="pending")
    db.add(tx)
    # simple rule: if amount >= amount_from mark order as paid
    if float(payload.amount) >= float(order.amount_from):
        if order.status == "pending_payment":
            order.status = "paid"
        elif order.status == "processing":
            changed = await deduct_reserve_once(db, order)
            if changed:
                order.status = "completed"
    await db.commit()
    await db.refresh(tx)
    await log_action(db, user.id, "tx.create", f"order_id={order.id};tx_id={tx.id}")
    return tx


@router.get("/{order_id}/transactions", response_model=list[TransactionRead])
async def list_transactions(order_id: int, db: AsyncSession = Depends(get_session), user: User = Depends(deps.current_user)):
    order = await db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.user_id != user.id and user.role not in ("admin","operator"):
        raise HTTPException(status_code=403, detail="Forbidden")
    return order.transactions


@router.get("", response_model=list[OrderRead])
async def list_orders(
    status: str | None = None,
    user_id: int | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(deps.require_roles("admin","operator")),
):
    """List orders with optional filters (admin/operator)."""
    stmt = select(Order)
    if status:
        stmt = stmt.where(Order.status == status)
    if user_id:
        stmt = stmt.where(Order.user_id == user_id)
    stmt = stmt.order_by(Order.id.desc()).limit(min(limit, 200))
    res = await db.execute(stmt)
    return list(res.scalars())


@router.get("/{order_id}", response_model=OrderRead)
async def get_order(order_id: int, db: AsyncSession = Depends(get_session), user: User = Depends(deps.current_user)):
    """Return order if owner or admin/operator."""
    order = await db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Not found")
    if order.user_id != user.id and user.role not in ("admin", "operator"):
        raise HTTPException(status_code=403, detail="Forbidden")
    return order


@router.get("/my/list", response_model=list[OrderRead])
async def my_orders(limit: int = 50, db: AsyncSession = Depends(get_session), user: User = Depends(deps.current_user)):
    """Return recent orders for current user (self-service view)."""
    stmt = select(Order).where(Order.user_id == user.id).order_by(Order.id.desc()).limit(min(limit, 200))
    res = await db.execute(stmt)
    return list(res.scalars())


@router.post("/{order_id}/status", response_model=OrderRead)
async def update_status(order_id: int, payload: OrderStatusUpdate, db: AsyncSession = Depends(get_session), user: User = Depends(deps.require_roles("admin","operator"))):
    """Change order status (admin/operator only) with validation and reserve update."""
    if payload.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")
    order = await db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Not found")
    # Simple state machine rule example
    allowed_forward = {
        "new": {"pending_payment","canceled"},
        "pending_payment": {"paid","canceled"},
        "paid": {"processing","canceled"},
        "processing": {"completed","canceled"},
        "completed": set(),
        "canceled": set(),
    }
    if payload.status not in allowed_forward.get(order.status, set()):
        raise HTTPException(status_code=400, detail=f"Transition {order.status}->{payload.status} not allowed")
    prev = order.status
    order.status = payload.status
    if payload.status == "completed":
        await deduct_reserve_once(db, order)
    await db.commit()
    await db.refresh(order)
    await log_action(db, user.id, "order.status", f"order_id={order.id};status={order.status}")
    return order
