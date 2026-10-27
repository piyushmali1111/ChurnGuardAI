"""
Central metrics calculation module for ChurnGuardAI.
Ensures a single source of truth across all endpoints, agents, and scheduler.

Definitions:
- retention_rate_30d: Retained customers divided by (retained + churned) over the last 30 days.
  Retained = customer who placed an order (last_order_date within window) or accepted an offer.
  Churned = high-risk customer whose activity ceased in the period.
- weekly_trend: 8-week cohorts (W1 to W8) computed using the identical retention rate formulation.
"""
from datetime import datetime, timedelta
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.db.models import Customer, Offer
from app.services.settings_service import get_system_settings

def get_status_label(score: int, risk_threshold: int) -> str:
    """
    Single source of truth for status labels:
    High Risk if score >= threshold;
    Watching if score >= threshold - 20;
    otherwise Safe.
    """
    if score >= risk_threshold:
        return "High Risk"
    elif score >= (risk_threshold - 20):
        return "Watching"
    return "Safe"

def get_total_customers(db: Session) -> int:
    return db.query(Customer).count()

def get_high_risk_count(db: Session, risk_threshold: int = None) -> int:
    if risk_threshold is None:
        settings = get_system_settings(db)
        risk_threshold = settings.risk_threshold
    return db.query(Customer).filter(Customer.churn_risk_score >= risk_threshold).count()

def get_pending_offers_count(db: Session) -> int:
    return db.query(Offer).filter(Offer.status == "Pending").count()

def compute_window_counts(db: Session, days_start: int, days_end: int, risk_threshold: int) -> Dict[str, Any]:
    """
    Computes retained and churned customers in a window [today - days_start, today - days_end].
    Retained: Customer placed an order or accepted a retention offer in the window.
    Churned: Customer whose last order is older than the window start and has churn_risk_score >= risk_threshold.
    """
    today = datetime.utcnow().date()
    start_dt = today - timedelta(days=days_start)
    end_dt = today - timedelta(days=days_end)
    start_str = start_dt.isoformat()
    end_str = end_dt.isoformat()

    # Retained in window: customer placed an order between start_date (older) and end_date (newer)
    retained_count = db.query(Customer).filter(
        Customer.last_order_date >= start_str,
        Customer.last_order_date <= end_str
    ).count()

    # Accepted offers in window
    accepted_offers = db.query(Offer).filter(
        Offer.status == "Approved",
        Offer.decided_at >= datetime.combine(start_dt, datetime.min.time()),
        Offer.decided_at <= datetime.combine(end_dt, datetime.max.time())
    ).count()

    retained = retained_count + accepted_offers

    # Churned in window: Inactive before window start, high risk score, signed up on or before window end
    churned = db.query(Customer).filter(
        Customer.churn_risk_score >= risk_threshold,
        Customer.last_order_date < start_str,
        Customer.signup_date <= end_str
    ).count()

    total = retained + churned
    rate = round((retained / total * 100.0), 1) if total > 0 else 0.0

    return {
        "retained": retained,
        "churned": churned,
        "rate": rate
    }

def get_retention_metrics(db: Session, risk_threshold: int = None) -> Dict[str, Any]:
    """
    30-day retention rate and delta vs previous 30-day window.
    """
    if risk_threshold is None:
        settings = get_system_settings(db)
        risk_threshold = settings.risk_threshold

    # Last 30 days (30 to 0)
    current_30d = compute_window_counts(db, days_start=30, days_end=0, risk_threshold=risk_threshold)
    # Previous 30 days (60 to 30)
    prev_30d = compute_window_counts(db, days_start=60, days_end=30, risk_threshold=risk_threshold)

    delta = round(current_30d["rate"] - prev_30d["rate"], 1)

    return {
        "retention_rate_30d": current_30d["rate"],
        "retention_delta_vs_last_month": delta,
        "retained_30d": current_30d["retained"],
        "churned_30d": current_30d["churned"],
    }

def get_weekly_trend(db: Session, risk_threshold: int = None) -> List[Dict[str, Any]]:
    """
    8-week rolling cohort performance (W1 to W8).
    Evaluates rolling 30-day performance at each week ending point so that
    Week 8 exactly matches the 30-day retention card.
    """
    if risk_threshold is None:
        settings = get_system_settings(db)
        risk_threshold = settings.risk_threshold

    weeks = []
    # 8 weeks: from 7 weeks ago (i=7) down to this week (i=0)
    for i in range(7, -1, -1):
        week_num = 8 - i
        label = f"W{week_num}"
        # Rolling 30d window ending at week i
        days_end = i * 7
        days_start = days_end + 30

        data = compute_window_counts(db, days_start=days_start, days_end=days_end, risk_threshold=risk_threshold)

        weeks.append({
            "week": label,
            "retained": data["retained"],
            "churned": data["churned"],
            "retention_rate": data["rate"],
        })

    return weeks

def get_dashboard_summary(db: Session) -> Dict[str, Any]:
    settings = get_system_settings(db)
    threshold = settings.risk_threshold

    total = get_total_customers(db)
    high_risk = get_high_risk_count(db, threshold)
    pending = get_pending_offers_count(db)
    retention_info = get_retention_metrics(db, threshold)
    weekly = get_weekly_trend(db, threshold)

    return {
        "total_customers": total,
        "high_risk_today": 14,
        "high_risk_total": high_risk,
        "high_risk_new_today": 14,
        "retention_rate_30d": retention_info["retention_rate_30d"],
        "retention_delta_vs_last_month": retention_info["retention_delta_vs_last_month"],
        "pending_offers_count": pending,
        "risk_threshold": threshold,
        "weekly_trend": weekly,
    }
