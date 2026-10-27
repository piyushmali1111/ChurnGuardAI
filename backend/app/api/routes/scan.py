import uuid
import asyncio
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import Customer, Offer
from app.api.schemas import ScanRunResponse
from app.ml.churn_predictor import predict_churn_risk
from app.ml.shap_explainer import explain_churn_risk
from app.agents.orchestrator import run_agent_pipeline
from app.services.settings_service import get_system_settings
from app.services.metrics import get_status_label, get_total_customers, get_high_risk_count
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
    new_offers_count = 0

    for cust in customers:
        days_inact = compute_days_inactive(cust.last_order_date)
        feature_dict = {
            "DaysSinceLastOrder": days_inact,
            "OrderCount": cust.order_count,
            "TotalSpent": cust.total_spent,
            "ComplaintCount": cust.complaint_count,
            "SatisfactionScore": cust.satisfaction_score,
        }
        try:
            new_score = predict_churn_risk(feature_dict)
        except Exception:
            new_score = cust.churn_risk_score

        cust.churn_risk_score = new_score
        cust.baseline_score = new_score
        # For proactive scan with no ticket, fused_score equals baseline_score
        cust.fused_score = new_score
        cust.churn_status = get_status_label(new_score, threshold)

        # Only create offer if no pending offer already exists for this customer
        existing = db.query(Offer).filter(
            Offer.customer_id == cust.id,
            Offer.status == "Pending"
        ).first()

        if new_score >= threshold and not existing:
            shap_data = explain_churn_risk(feature_dict, new_score)
            offer_id = f"OFFER-{uuid.uuid4().hex[:6].upper()}"

            result = run_agent_pipeline(
                customer_id=cust.id,
                customer_name=cust.name,
                churn_risk_score=new_score,
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
                    baseline_score=new_score,
                    urgency_score=None,
                    fused_score=new_score,
                    status="Pending",
                    created_at=datetime.utcnow(),
                )
                db.add(new_offer)
                new_offers_count += 1

    db.commit()

    total_count = get_total_customers(db)
    flagged_count = get_high_risk_count(db, threshold)

    # Section 9 requirement:
    # "The batch scan event must not say the Risk-Fusion Agent completed it.
    # Use the label 'Scheduler' with text 'Proactive scan completed: 4,850 customers scored, 14 flagged.'"
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

    return {
        "new_offers_count": new_offers_count,
        "scan_timestamp": datetime.utcnow().isoformat(),
    }
