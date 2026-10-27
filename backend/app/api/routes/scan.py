import uuid
import asyncio
from datetime import datetime, timedelta
import pandas as pd
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import Customer, Offer
from app.api.schemas import ScanRunResponse
from app.ml.features import FEATURE_COLS
from app.ml.churn_predictor import predict_churn_risk_batch, score_to_status
from app.ml.shap_explainer import explain_churn_risk
from app.agents.orchestrator import run_agent_pipeline
from app.services.settings_service import get_system_settings
from app.services.metrics import get_total_customers, get_high_risk_count
from app.websocket.agent_activity import broadcaster

router = APIRouter()


def compute_days_inactive(last_order_str: str) -> int:
    try:
        today = datetime.utcnow().date()
        order_date = datetime.strptime(last_order_str[:10], "%Y-%m-%d").date()
        return max(0, (today - order_date).days)
    except Exception:
        return 30


@router.post("/run", response_model=ScanRunResponse)
def run_proactive_scan(db: Session = Depends(get_db)):
    settings_obj = get_system_settings(db)
    threshold = settings_obj.risk_threshold
    max_discount = settings_obj.max_discount_percent

    customers = db.query(Customer).all()
    if not customers:
        return ScanRunResponse(scanned_customers=0, high_risk_flagged=0, offers_drafted=0)

    # 1. Batch vector scoring across all customers using FEATURE_COLS
    records = []
    days_inactive_list = []
    for c in customers:
        d_inact = compute_days_inactive(c.last_order_date)
        days_inactive_list.append(d_inact)
        records.append({
            "DaysSinceLastOrder": d_inact,
            "OrderCount": c.order_count,
            "TotalSpent": c.total_spent,
            "ComplaintCount": c.complaint_count,
            "SatisfactionScore": c.satisfaction_score,
            "TenureMonths": getattr(c, "tenure_months", 12.0) or 12.0,
            "ReturnRate": getattr(c, "return_rate", 0.10) or 0.10,
            "DiscountUsageRate": getattr(c, "discount_usage_rate", 0.20) or 0.20,
        })

    df = pd.DataFrame(records)[FEATURE_COLS]
    try:
        new_scores = predict_churn_risk_batch(df)
    except Exception as e:
        new_scores = [c.churn_risk_score for c in customers]

    now_utc = datetime.utcnow()
    newly_flagged_count = 0
    high_risk_customers = []

    for c, new_score, d_inact in zip(customers, new_scores, days_inactive_list):
        was_high_risk = (c.churn_risk_score >= threshold)
        is_high_risk = (new_score >= threshold)

        if is_high_risk and not was_high_risk:
            newly_flagged_count += 1

        c.churn_risk_score = round(float(new_score), 1)
        c.baseline_score = int(round(new_score))
        c.fused_score = round(float(new_score), 1)
        c.churn_status = score_to_status(new_score, threshold)
        c.scored_at = now_utc

        if is_high_risk:
            high_risk_customers.append((c, d_inact))

    # 2. Offer drafting rules (Step 9):
    # - Draft offers only for top 25 per run ranked by fused_score * total_spent
    # - Skip customers who already have a Pending offer
    # - Skip customers who got an offer in the last 30 days
    thirty_days_ago = now_utc - timedelta(days=30)
    pending_ids = set(r[0] for r in db.query(Offer.customer_id).filter(Offer.status == "Pending").all())
    recent_offer_ids = set(r[0] for r in db.query(Offer.customer_id).filter(Offer.created_at >= thirty_days_ago).all())

    eligible_candidates = [
        (c, d_inact) for c, d_inact in high_risk_customers
        if c.id not in pending_ids and c.id not in recent_offer_ids
    ]

    # Rank by fused_score * lifetime spend descending
    eligible_candidates.sort(key=lambda item: (item[0].fused_score or item[0].churn_risk_score) * item[0].total_spent, reverse=True)
    top_candidates = eligible_candidates[:25]

    new_offers_count = 0
    for cust, days_inact in top_candidates:
        feat_dict = {
            "DaysSinceLastOrder": days_inact,
            "OrderCount": cust.order_count,
            "TotalSpent": cust.total_spent,
            "ComplaintCount": cust.complaint_count,
            "SatisfactionScore": cust.satisfaction_score,
            "TenureMonths": getattr(cust, "tenure_months", 12.0) or 12.0,
            "ReturnRate": getattr(cust, "return_rate", 0.10) or 0.10,
            "DiscountUsageRate": getattr(cust, "discount_usage_rate", 0.20) or 0.20,
        }
        shap_data = explain_churn_risk(feat_dict, cust.churn_risk_score)
        offer_id = f"OFFER-{uuid.uuid4().hex[:6].upper()}"

        result = run_agent_pipeline(
            customer_id=cust.id,
            customer_name=cust.name,
            churn_risk_score=cust.churn_risk_score,
            shap_factors=shap_data["factors"],
            total_spent=cust.total_spent,
            ticket_text=None,
            sentiment_urgency=None,
            ticket_id=None,
            offer_id=offer_id,
            recency_days=days_inact,
            order_count=cust.order_count,
            complaint_count=cust.complaint_count,
            satisfaction_score=cust.satisfaction_score,
            risk_threshold=threshold,
            max_discount_ceiling=max_discount,
        )

        if result.get("verified_offer"):
            offer_draft = result["verified_offer"]
            new_offer = Offer(
                id=offer_id,
                customer_id=cust.id,
                ticket_id=None,
                drafted_message=offer_draft.get("drafted_message", ""),
                discount_percent=offer_draft.get("discount_percent", 10),
                reasoning=offer_draft.get("reasoning", "Proactive scan flagged high churn risk."),
                baseline_score=cust.churn_risk_score,
                urgency_score=None,
                fused_score=cust.churn_risk_score,
                status="Pending",
                created_at=datetime.utcnow(),
            )
            db.add(new_offer)
            new_offers_count += 1

    db.commit()

    total_count = get_total_customers(db)
    flagged_count = get_high_risk_count(db, threshold)

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(broadcaster.broadcast_event(
                agent="Scheduler",
                message=f"Proactive scan completed: {total_count:,} customers scored, {flagged_count} flagged.",
                type_label="info",
                chip="Proactive Scan"
            ))
    except Exception:
        pass

    return ScanRunResponse(
        scanned_customers=total_count,
        high_risk_flagged=flagged_count,
        new_offers_count=new_offers_count,
        scan_timestamp=datetime.utcnow().isoformat()
    )
