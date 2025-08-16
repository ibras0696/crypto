"""Currency model holds reserve and code meta."""
from __future__ import annotations
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Numeric
from ..core.database import Base


class Currency(Base):
    __tablename__ = "currencies"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(15), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    reserve: Mapped[float] = mapped_column(Numeric(18, 8), default=0)

    orders_from: Mapped[list["Order"]] = relationship(
        back_populates="from_currency_obj", foreign_keys="Order.from_currency"
    )
    orders_to: Mapped[list["Order"]] = relationship(
        back_populates="to_currency_obj", foreign_keys="Order.to_currency"
    )
