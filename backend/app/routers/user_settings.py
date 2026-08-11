"""User settings router.

Single-row settings table for UI preferences and AI analysis behaviour.
If no row exists the GET endpoint creates one with defaults; PATCH updates it.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import UserSettings
from app.schemas import UserSettingsOut, UserSettingsUpdate

router = APIRouter(prefix="/api", tags=["user-settings"])

_SETTINGS_ROW_ID = 1


def _get_or_create(db: Session) -> UserSettings:
    row = db.get(UserSettings, _SETTINGS_ROW_ID)
    if row is None:
        row = UserSettings(id=_SETTINGS_ROW_ID)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


@router.get("/user-settings", response_model=UserSettingsOut)
def get_settings(db: Session = Depends(get_db)):
    return _get_or_create(db)


@router.patch("/user-settings", response_model=UserSettingsOut)
def update_settings(payload: UserSettingsUpdate, db: Session = Depends(get_db)):
    row = _get_or_create(db)
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row
