"""Auth router: register and login endpoints."""
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..core.database import get_session
from ..models import User
from ..schemas.auth import UserCreate, UserRead, TokenResponse, KYCSubmit, KYCStatusUpdate
from ..core import security
from ..core import deps
from ..services.orders import log_action

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_session)):
    """Create a user if email not taken."""
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(email=payload.email, hashed_password=security.hash_password(payload.password))
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
async def login(payload: UserCreate, db: AsyncSession = Depends(get_session)):
    """Login returning JWT token (re-using UserCreate for simplicity)."""
    res = await db.execute(select(User).where(User.email == payload.email))
    user = res.scalar_one_or_none()
    if not user or not security.verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = security.create_access_token(str(user.id), user.role)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserRead)
async def me(user: User = Depends(deps.current_user)):
    """Return current authenticated user profile (includes KYC data if loaded)."""
    return user


@router.post("/kyc/submit", response_model=UserRead)
async def submit_kyc(payload: KYCSubmit, db: AsyncSession = Depends(get_session), user: User = Depends(deps.current_user)):
    from ..models.user import KYCData
    if user.kyc_status in ("pending","verified"):
        return user
    # upsert kyc data
    existing = await db.get(KYCData, getattr(user.kyc, 'id', 0)) if user.kyc else None
    if existing:
        existing.full_name = payload.full_name
        existing.document_id = payload.document_id
    else:
        db.add(KYCData(user_id=user.id, full_name=payload.full_name, document_id=payload.document_id))
    user.kyc_status = "pending"
    await db.commit()
    await db.refresh(user)
    masked = payload.document_id[:2] + "***" if len(payload.document_id) > 2 else "***"
    await log_action(db, user.id, "kyc.submit", f"doc={masked}")
    return user


@router.post("/kyc/{user_id}/status", response_model=UserRead)
async def set_kyc_status(user_id: int, payload: KYCStatusUpdate, db: AsyncSession = Depends(get_session), _: User = Depends(deps.require_roles("admin","operator"))):
    target = await db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if payload.status not in {"pending","verified","rejected"}:
        raise HTTPException(status_code=400, detail="Bad status")
    target.kyc_status = payload.status
    await db.commit()
    await db.refresh(target)
    await log_action(db, target.id, "kyc.status", f"status={payload.status}")
    return target


@router.post("/promote/{user_id}/{role}", response_model=UserRead)
async def promote(user_id: int, role: str, db: AsyncSession = Depends(get_session), _: User = Depends(deps.require_roles("admin",))):
    if role not in {"user","operator","admin"}:
        raise HTTPException(status_code=400, detail="Bad role")
    target = await db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    target.role = role
    await db.commit()
    await db.refresh(target)
    await log_action(db, target.id, "user.promote", f"role={role}")
    return target
