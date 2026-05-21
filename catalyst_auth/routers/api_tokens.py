"""API token routes — create, list, revoke."""
from __future__ import annotations
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth import generate_api_token
from database import get_db
from dependencies import get_current_user, require_admin
from models import User, ApiToken
from schemas import ApiTokenOut, ApiTokenCreated, MessageResponse

router = APIRouter(prefix="/tokens", tags=["api-tokens"])


@router.post("", response_model=ApiTokenCreated)
def create_token(
    expires_days: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    raw, hashed = generate_api_token()
    expires_at = (datetime.utcnow() + timedelta(days=expires_days)) if expires_days else None
    tok = ApiToken(user_id=current_user.id, token_hash=hashed, expires_at=expires_at)
    db.add(tok)
    db.commit()
    db.refresh(tok)
    return ApiTokenCreated(
        id=tok.id, user_id=tok.user_id,
        created_at=tok.created_at, expires_at=tok.expires_at,
        revoked=tok.revoked, raw_token=raw,
    )


@router.get("/me", response_model=List[ApiTokenOut])
def my_tokens(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(ApiToken)
        .filter(ApiToken.user_id == current_user.id, ApiToken.revoked.is_(False))
        .all()
    )


@router.delete("/{token_id}", response_model=MessageResponse)
def revoke_token(
    token_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tok = db.get(ApiToken, token_id)
    if not tok or str(tok.user_id) != str(current_user.id):
        raise HTTPException(404, "Token not found")
    tok.revoked = True
    db.commit()
    return MessageResponse(message="Token revoked")


# Admin: revoke any token
@router.delete("/admin/{token_id}", response_model=MessageResponse)
def admin_revoke_token(
    token_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    tok = db.get(ApiToken, token_id)
    if not tok:
        raise HTTPException(404, "Token not found")
    tok.revoked = True
    db.commit()
    return MessageResponse(message="Token revoked")
