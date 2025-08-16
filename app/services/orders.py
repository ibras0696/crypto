"""Service layer for order operations: audit, reserve management, idempotent completion.

This centralizes side-effect logic so routers stay thin.
"""
from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from ..models import AuditLog, Order, Currency


async def log_action(db: AsyncSession, user_id: int | None, action: str, data: str | None = None):
	db.add(AuditLog(user_id=user_id, action=action, details=data))
	await db.commit()


async def ensure_reserve_sufficient(db: AsyncSession, currency_id: int, amount: float):
	cur = await db.get(Currency, currency_id)
	if not cur:
		raise ValueError("Currency missing")
	if float(cur.reserve) < float(amount):
		raise ValueError("Insufficient reserve")
	return cur


async def deduct_reserve_once(db: AsyncSession, order: Order):
	"""Idempotently deduct reserve for completed order.
	Checks if a prior completion audit exists to avoid double deduction.
	"""
	exists = await db.execute(select(AuditLog).where(AuditLog.action=="order.complete", AuditLog.details==f"order_id={order.id}"))
	if exists.scalars().first():
		return False
	cur = await db.get(Currency, order.to_currency)
	if cur and float(cur.reserve) >= float(order.amount_to):
		cur.reserve = float(cur.reserve) - float(order.amount_to)
		db.add(AuditLog(user_id=order.user_id, action="order.complete", details=f"order_id={order.id}"))
		await db.commit()
		return True
	return False
