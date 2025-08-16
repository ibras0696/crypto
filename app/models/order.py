"""Order model representing exchange request."""
from __future__ import annotations
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, DateTime, String, Numeric
from datetime import datetime
from ..core.database import Base

ORDER_STATUS = (
    "new",
    "pending_payment",
    "paid",
    "processing",
    "completed",
    "canceled",
)


class Order(Base):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    from_currency: Mapped[int] = mapped_column(ForeignKey("currencies.id"))
    to_currency: Mapped[int] = mapped_column(ForeignKey("currencies.id"))
    amount_from: Mapped[float] = mapped_column(Numeric(18, 8))
    amount_to: Mapped[float] = mapped_column(Numeric(18, 8))
    wallet_address: Mapped[str | None] = mapped_column(String(120), nullable=True)
    payout_details: Mapped[str | None] = mapped_column(String(255), nullable=True)
    rate: Mapped[float] = mapped_column(Numeric(18, 8))
    status: Mapped[str] = mapped_column(String(30), default="new")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="orders", lazy="selectin")
    from_currency_obj: Mapped["Currency"] = relationship(
        foreign_keys=[from_currency], back_populates="orders_from", lazy="selectin"
    )
    to_currency_obj: Mapped["Currency"] = relationship(
        foreign_keys=[to_currency], back_populates="orders_to", lazy="selectin"
    )
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="order", lazy="selectin")
