from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc, asc
from app.db.session import get_db
from app.db.models import Customer, Ticket, Offer
from app.api.schemas import CustomerSummaryResponse, CustomerDetailResponse, PaginatedCustomersResponse
from app.ml.shap_explainer import explain_churn_risk
from app.services.settings_service import get_system_settings
from app.services.metrics import get_status_label

router = APIRouter()

def compute_days_inactive(last_order_str: str) -> int:
    try:
        today = datetime.utcnow().date()
        order_date = datetime.strptime(last_order_str[:10], "%Y-%m-%d").date()
        return max(0, (today - order_date).days)
    except Exception:
        return 30

@router.get("", response_model=PaginatedCustomersResponse)
def list_customers(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    search: Optional[str] = Query(None),
    risk_level: Optional[str] = Query(None),
    sort: Optional[str] = Query("risk_desc"),
    db: Session = Depends(get_db)
):
    settings = get_system_settings(db)
    threshold = settings.risk_threshold

    query = db.query(Customer)

    # Server-side search
    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Customer.name.ilike(term),
                Customer.email.ilike(term),
                Customer.id.ilike(term)
            )
        )

    # Server-side risk level filter using dynamic threshold
    if risk_level and risk_level.strip():
        rl = risk_level.strip().lower()
        if rl in ["high", "high risk", "high_risk"]:
            query = query.filter(Customer.churn_risk_score >= threshold)
        elif rl in ["watching"]:
            query = query.filter(
                Customer.churn_risk_score >= (threshold - 20),
                Customer.churn_risk_score < threshold
            )
        elif rl in ["safe"]:
            query = query.filter(Customer.churn_risk_score < (threshold - 20))

    total = query.count()

    # Server-side sort
    if sort == "risk_asc":
        query = query.order_by(asc(Customer.churn_risk_score))
    elif sort == "spent_desc":
        query = query.order_by(desc(Customer.total_spent))
    elif sort == "spent_asc":
        query = query.order_by(asc(Customer.total_spent))
    elif sort == "date_desc":
        query = query.order_by(desc(Customer.last_order_date))
    elif sort == "date_asc":
        query = query.order_by(asc(Customer.last_order_date))
    else:  # default risk_desc: score desc, days since last order desc, total spent desc
        query = query.order_by(desc(Customer.churn_risk_score), asc(Customer.last_order_date), desc(Customer.total_spent))

    offset = (page - 1) * page_size
    customers = query.offset(offset).limit(page_size).all()

    items = []
    for c in customers:
        days_inact = compute_days_inactive(c.last_order_date)
        status = get_status_label(c.churn_risk_score, threshold)
        items.append(
            CustomerSummaryResponse(
                id=c.id,
                name=c.name,
                email=c.email,
                churn_risk_score=c.churn_risk_score,
                baseline_score=c.baseline_score or c.churn_risk_score,
                urgency_score=c.urgency_score,
                fused_score=c.fused_score,
                churn_status=status,
                last_order_date=c.last_order_date,
                days_inactive=days_inact,
                total_spent=c.total_spent,
                order_count=c.order_count,
            )
        )

    return PaginatedCustomersResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size
    )

@router.get("/{customer_id}", response_model=CustomerDetailResponse)
def get_customer(customer_id: str, db: Session = Depends(get_db)):
    cust = db.query(Customer).filter(Customer.id == customer_id).first()
    if not cust:
        raise HTTPException(status_code=404, detail="Customer not found")

    settings = get_system_settings(db)
    threshold = settings.risk_threshold
    status = get_status_label(cust.churn_risk_score, threshold)
    days_inact = compute_days_inactive(cust.last_order_date)

    feature_dict = {
        "DaysSinceLastOrder": days_inact,
        "OrderCount": cust.order_count,
        "TotalSpent": cust.total_spent,
        "ComplaintCount": cust.complaint_count,
        "SatisfactionScore": cust.satisfaction_score,
        "TenureMonths": getattr(cust, "tenure_months", 12.0) or 12.0,
        "ReturnRate": getattr(cust, "return_rate", 0.10) or 0.10,
        "DiscountUsageRate": getattr(cust, "discount_usage_rate", 0.20) or 0.20,
    }

    baseline_score = cust.baseline_score or cust.churn_risk_score
    shap_data = explain_churn_risk(feature_dict, baseline_score)

    tickets = db.query(Ticket).filter(Ticket.customer_id == customer_id).order_by(desc(Ticket.created_at)).all()
    ticket_history = [
        {
            "id": t.id,
            "customer_id": t.customer_id,
            "customer_name": cust.name,
            "message": t.message,
            "sentiment_label": t.sentiment_label,
            "sentiment_score": t.sentiment_score,
            "urgency_score": t.urgency_score or t.sentiment_score,
            "baseline_score": t.baseline_score,
            "fused_score": t.fused_score,
            "agent_reply": t.agent_reply,
            "created_at": t.created_at.isoformat(),
        }
        for t in tickets
    ]

    offers = db.query(Offer).filter(Offer.customer_id == customer_id).order_by(desc(Offer.created_at)).all()
    offer_history = [
        {
            "id": o.id,
            "customer_id": o.customer_id,
            "customer_name": cust.name,
            "ticket_id": o.ticket_id,
            "drafted_message": o.drafted_message,
            "discount_percent": o.discount_percent,
            "reasoning": o.reasoning,
            "baseline_score": o.baseline_score,
            "urgency_score": o.urgency_score,
            "fused_score": o.fused_score,
            "status": o.status,
            "created_at": o.created_at.isoformat(),
            "decided_at": o.decided_at.isoformat() if o.decided_at else None,
        }
        for o in offers
    ]

    # Latest fused score: from customer record or latest ticket/offer
    latest_fused = cust.fused_score
    latest_urgency = cust.urgency_score
    if latest_fused is None and offers and offers[0].fused_score is not None:
        latest_fused = offers[0].fused_score
        latest_urgency = offers[0].urgency_score
    elif latest_fused is None and tickets and tickets[0].fused_score is not None:
        latest_fused = tickets[0].fused_score
        latest_urgency = tickets[0].urgency_score

    return CustomerDetailResponse(
        id=cust.id,
        name=cust.name,
        email=cust.email,
        churn_risk_score=cust.churn_risk_score,
        baseline_score=baseline_score,
        urgency_score=latest_urgency,
        fused_score=latest_fused,
        churn_status=status,
        last_order_date=cust.last_order_date,
        days_inactive=days_inact,
        total_spent=cust.total_spent,
        order_count=cust.order_count,
        signup_date=cust.signup_date,
        complaint_count=cust.complaint_count,
        satisfaction_score=cust.satisfaction_score,
        base_score=shap_data["base_score"],
        shap_factors=shap_data["factors"],
        ticket_history=ticket_history,
        offers=offer_history,
    )
