"""Order and related schemas."""
from __future__ import annotations
from pydantic import BaseModel, Field
from datetime import datetime


VALID_STATUSES = {"new","pending_payment","paid","processing","completed","canceled"}


class OrderCreate(BaseModel):
    from_currency: int
    to_currency: int
    amount_from: float = Field(gt=0)
    payout_details: str | None = None


class OrderStatusUpdate(BaseModel):
    status: str

    def validate_status(self):
        if self.status not in VALID_STATUSES:
            raise ValueError("Invalid status")
        return self


class OrderRead(BaseModel):
    id: int
    user_id: int
    from_currency: int
    to_currency: int
    amount_from: float
    amount_to: float
    rate: float
    status: str
    wallet_address: str | None
    payout_details: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TransactionRead(BaseModel):
    id: int
    order_id: int
    tx_hash: str | None
    amount: float
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TransactionCreate(BaseModel):
    tx_hash: str | None = None
    amount: float
