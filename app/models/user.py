"""User model with basic role+kyc state."""
from __future__ import annotations
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, DateTime, ForeignKey
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:  # pragma: no cover
    from .order import Order
from datetime import datetime
from ..core.database import Base


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str]
    role: Mapped[str] = mapped_column(String(20), default="user")  # user|operator|admin
    kyc_status: Mapped[str] = mapped_column(String(20), default="unverified")  # unverified|pending|verified|rejected
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    orders: Mapped[list["Order"]] = relationship(back_populates="user", lazy="selectin")
    # Use direct forward ref (from __future__ annotations) without extra quotes around union part
    # Some SQLAlchemy versions mis-parse a stringified union containing quotes; use Optional forward ref style
    kyc: Mapped[Optional["KYCData"]] = relationship(back_populates="user", uselist=False, lazy="selectin")


class KYCData(Base):
    __tablename__ = "kyc_data"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    full_name: Mapped[str] = mapped_column(String(255))
    document_id: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped[User] = relationship(back_populates="kyc")
