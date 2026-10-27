from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.schemas import SettingsResponse, SettingsUpdateRequest
from app.services.settings_service import get_system_settings, update_system_settings
from app.config import settings as app_settings

router = APIRouter()

@router.get("", response_model=SettingsResponse)
def get_settings(db: Session = Depends(get_db)):
    curr = get_system_settings(db)
    return SettingsResponse(
        risk_threshold=curr.risk_threshold,
        max_discount_percent=curr.max_discount_percent,
        scan_frequency=curr.scan_frequency,
        fusion_alpha=app_settings.FUSION_ALPHA,
    )

@router.put("", response_model=SettingsResponse)
def update_settings(payload: SettingsUpdateRequest, db: Session = Depends(get_db)):
    curr = update_system_settings(
        db,
        risk_threshold=payload.risk_threshold,
        max_discount_percent=payload.max_discount_percent,
        scan_frequency=payload.scan_frequency,
    )
    return SettingsResponse(
        risk_threshold=curr.risk_threshold,
        max_discount_percent=curr.max_discount_percent,
        scan_frequency=curr.scan_frequency,
        fusion_alpha=app_settings.FUSION_ALPHA,
    )
