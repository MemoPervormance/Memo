"""Announcement routes — public read + admin CRUD."""
from __future__ import annotations
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_user, require_admin
from models import Announcement, User
from schemas import AnnouncementOut, AnnouncementCreateRequest, MessageResponse

router = APIRouter(prefix="/announcements", tags=["announcements"])


# Public: active announcements
@router.get("", response_model=List[AnnouncementOut])
def list_announcements(db: Session = Depends(get_db)):
    return (
        db.query(Announcement)
        .filter(Announcement.is_active.is_(True))
        .order_by(Announcement.created_at.desc())
        .all()
    )


@router.get("/{ann_id}", response_model=AnnouncementOut)
def get_announcement(ann_id: str, db: Session = Depends(get_db)):
    ann = db.get(Announcement, ann_id)
    if not ann or not ann.is_active:
        raise HTTPException(404, "Announcement not found")
    return ann


# Admin: create
@router.post("", response_model=AnnouncementOut)
def create_announcement(
    body: AnnouncementCreateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    ann = Announcement(
        title=body.title,
        content=body.content,
        is_active=body.is_active,
        created_by=admin.id,
    )
    db.add(ann)
    db.commit()
    db.refresh(ann)
    return ann


# Admin: update
@router.patch("/{ann_id}", response_model=AnnouncementOut)
def update_announcement(
    ann_id: str,
    body: AnnouncementCreateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    ann = db.get(Announcement, ann_id)
    if not ann:
        raise HTTPException(404, "Announcement not found")
    ann.title     = body.title
    ann.content   = body.content
    ann.is_active = body.is_active
    db.commit()
    db.refresh(ann)
    return ann


# Admin: delete
@router.delete("/{ann_id}", response_model=MessageResponse)
def delete_announcement(
    ann_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    ann = db.get(Announcement, ann_id)
    if not ann:
        raise HTTPException(404, "Announcement not found")
    db.delete(ann)
    db.commit()
    return MessageResponse(message="Announcement deleted")
