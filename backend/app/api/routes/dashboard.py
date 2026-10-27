from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.schemas import DashboardSummaryResponse
from app.services.metrics import get_dashboard_summary as compute_summary

router = APIRouter()

@router.get("/summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary(db: Session = Depends(get_db)):
    return compute_summary(db)
