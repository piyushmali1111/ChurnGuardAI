import uuid
from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import Customer, Ticket, Offer
from app.api.schemas import TicketResponse, TicketCreateRequest
from app.ml.sentiment_model import analyze_sentiment
from app.ml.shap_explainer import explain_churn_risk
from app.agents.orchestrator import run_agent_pipeline
from app.services.settings_service import get_system_settings

router = APIRouter()

def compute_days_inactive(last_order_str: str) -> int:
    try:
        today = datetime.utcnow().date()
        order_date = datetime.strptime(last_order_str[:10], "%Y-%m-%d").date()
        return max(0, (today - order_date).days)
    except Exception:
        return 30

@router.get("", response_model=List[TicketResponse])
def list_tickets(limit: int = 100, db: Session = Depends(get_db)):
    results = (
        db.query(Ticket, Customer.name)
        .outerjoin(Customer, Ticket.customer_id == Customer.id)
        .order_by(Ticket.created_at.desc())
        .limit(limit)
        .all()
    )
    res = []
    for t, cust_name in results:
        res.append({
            "id": t.id,
            "customer_id": t.customer_id,
            "customer_name": cust_name,
            "message": t.message,
            "sentiment_label": t.sentiment_label,
            "sentiment_score": t.sentiment_score,
            "urgency_score": t.urgency_score or t.sentiment_score,
            "baseline_score": t.baseline_score,
            "fused_score": t.fused_score,
            "agent_reply": t.agent_reply,
            "created_at": t.created_at.isoformat(),
        })
    return res

@router.post("", response_model=dict)
def create_ticket(payload: TicketCreateRequest, db: Session = Depends(get_db)):
    cust = db.query(Customer).filter(Customer.id == payload.customer_id).first()
    if not cust:
        raise HTTPException(status_code=404, detail="Customer not found")

    settings_obj = get_system_settings(db)
    threshold = settings_obj.risk_threshold
    max_discount = settings_obj.max_discount_percent

    # 1. Analyze ticket sentiment according to Section 5
    sentiment = analyze_sentiment(payload.message)
    urgency_val = sentiment["sentiment_score"]

    ticket_id = f"TCK-{uuid.uuid4().hex[:5].upper()}"
    offer_id = f"OFFER-{uuid.uuid4().hex[:6].upper()}"

    # 2. Build customer features
    days_inact = compute_days_inactive(cust.last_order_date)
    feature_dict = {
        "DaysSinceLastOrder": days_inact,
        "OrderCount": cust.order_count,
        "TotalSpent": cust.total_spent,
        "ComplaintCount": cust.complaint_count + 1,
        "SatisfactionScore": cust.satisfaction_score,
    }
    baseline_score = cust.baseline_score or cust.churn_risk_score
    shap_data = explain_churn_risk(feature_dict, baseline_score)

    # 3. Run multi-agent pipeline
    result = run_agent_pipeline(
        customer_id=cust.id,
        customer_name=cust.name,
        churn_risk_score=baseline_score,
        shap_factors=shap_data["factors"],
        total_spent=cust.total_spent,
        ticket_text=payload.message,
        sentiment_urgency=urgency_val,
        ticket_id=ticket_id,
        offer_id=offer_id,
        recency_days=days_inact,
        order_count=cust.order_count,
        complaint_count=cust.complaint_count + 1,
        satisfaction_score=cust.satisfaction_score,
        risk_threshold=threshold,
        max_discount_ceiling=max_discount,
    )

    support_reply = result.get("support_reply") or f"Hi {cust.name}, we've flagged your case to our team and will follow up shortly with next steps."

    # 4. Save ticket
    ticket = Ticket(
        id=ticket_id,
        customer_id=cust.id,
        message=payload.message,
        sentiment_label=sentiment["sentiment_label"],
        sentiment_score=urgency_val,
        urgency_score=urgency_val,
        baseline_score=result["baseline_score"],
        fused_score=result["fused_score"],
        agent_reply=support_reply,
        created_at=datetime.utcnow(),
    )
    db.add(ticket)

    # Update customer record
    cust.complaint_count += 1
    cust.baseline_score = result["baseline_score"]
    cust.urgency_score = result["urgency_score"]
    cust.fused_score = result["fused_score"]
    db.commit()

    # 5. Save pending offer if created by agent pipeline
    created_offer = None
    if result.get("verified_offer"):
        offer_draft = result["verified_offer"]
        new_offer = Offer(
            id=offer_id,
            customer_id=cust.id,
            ticket_id=ticket_id,
            drafted_message=offer_draft.get("drafted_message", ""),
            discount_percent=offer_draft.get("discount_percent", 15),
            reasoning=offer_draft.get("reasoning", "Ticket-triggered retention offer."),
            baseline_score=result["baseline_score"],
            urgency_score=result["urgency_score"],
            fused_score=result["fused_score"],
            status="Pending",
            created_at=datetime.utcnow(),
        )
        db.add(new_offer)
        db.commit()
        db.refresh(new_offer)
        created_offer = {
            "id": new_offer.id,
            "customer_id": new_offer.customer_id,
            "customer_name": cust.name,
            "ticket_id": new_offer.ticket_id,
            "drafted_message": new_offer.drafted_message,
            "discount_percent": new_offer.discount_percent,
            "reasoning": new_offer.reasoning,
            "baseline_score": new_offer.baseline_score,
            "urgency_score": new_offer.urgency_score,
            "fused_score": new_offer.fused_score,
            "status": new_offer.status,
            "created_at": new_offer.created_at.isoformat(),
        }

    return {
        "ticket": {
            "id": ticket.id,
            "customer_id": ticket.customer_id,
            "customer_name": cust.name,
            "message": ticket.message,
            "sentiment_label": ticket.sentiment_label,
            "sentiment_score": ticket.sentiment_score,
            "urgency_score": ticket.urgency_score,
            "baseline_score": ticket.baseline_score,
            "fused_score": ticket.fused_score,
            "agent_reply": ticket.agent_reply,
            "created_at": ticket.created_at.isoformat(),
        },
        "agent_reply": support_reply,
        "offer": created_offer,
    }
