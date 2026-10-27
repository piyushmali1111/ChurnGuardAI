from sqlalchemy.orm import Session
from app.db.models import SystemSetting
from app.config import settings as default_settings

def get_system_settings(db: Session) -> SystemSetting:
    setting = db.query(SystemSetting).filter(SystemSetting.id == 1).first()
    if not setting:
        setting = SystemSetting(
            id=1,
            risk_threshold=default_settings.RISK_THRESHOLD,
            max_discount_percent=default_settings.MAX_DISCOUNT_PERCENT,
            scan_frequency=default_settings.PROACTIVE_SCAN_INTERVAL,
        )
        db.add(setting)
        db.commit()
        db.refresh(setting)
    return setting

def update_system_settings(
    db: Session,
    risk_threshold: int = None,
    max_discount_percent: int = None,
    scan_frequency: str = None
) -> SystemSetting:
    setting = get_system_settings(db)
    if risk_threshold is not None:
        setting.risk_threshold = risk_threshold
    if max_discount_percent is not None:
        setting.max_discount_percent = max_discount_percent
    if scan_frequency is not None:
        setting.scan_frequency = scan_frequency
    db.commit()
    db.refresh(setting)
    return setting
