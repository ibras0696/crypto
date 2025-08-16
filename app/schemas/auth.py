"""Auth and user related Pydantic schemas."""
from __future__ import annotations
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime


class UserRead(BaseModel):
    id: int
    email: EmailStr
    role: str
    kyc_status: str
    created_at: datetime
    kyc: 'KYCRead | None' = None

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=100)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class KYCSubmit(BaseModel):
    full_name: str
    document_id: str


class KYCStatusUpdate(BaseModel):
    status: str  # pending|verified|rejected


class KYCRead(BaseModel):
    full_name: str
    document_id: str

UserRead.model_rebuild()
