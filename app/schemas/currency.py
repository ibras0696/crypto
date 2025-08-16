"""Currency schemas."""
from __future__ import annotations
from pydantic import BaseModel, Field


class CurrencyRead(BaseModel):
    id: int
    code: str
    name: str
    reserve: float

    model_config = {"from_attributes": True}


class CurrencyUpdateReserve(BaseModel):
    reserve: float = Field(ge=0)


class CurrencyCreate(BaseModel):
    code: str
    name: str
    reserve: float = Field(ge=0, default=0)
