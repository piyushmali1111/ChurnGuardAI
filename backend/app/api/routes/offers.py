from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import Offer, Customer
from app.api.schemas import OfferResponse, OfferPatchRequest

router = APIRouter()

def _serialize_offer(o: Offer, customer_name: str = None) -> dict:
    return {
        "id": o.id,
        "customer_id": o.customer_id,
        "customer_name": customer_name,
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

@router.get("/pending", response_model=List[OfferResponse])
def get_pending_offers(db: Session = Depends(get_db)):
    offers = db.query(Offer).filter(Offer.status == "Pending").order_by(Offer.created_at.desc()).all()
    res = []
    for o in offers:
        cust = db.query(Customer).filter(Customer.id == o.customer_id).first()
        res.append(_serialize_offer(o, cust.name if cust else None))
    return res

@router.post("/{offer_id}/approve", response_model=OfferResponse)
def approve_offer(offer_id: str, db: Session = Depends(get_db)):
    offer = db.query(Offer).filter(Offer.id == offer_id).first()
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    offer.status = "Approved"
    offer.decided_at = datetime.utcnow()
    db.commit()
    db.refresh(offer)
    cust = db.query(Customer).filter(Customer.id == offer.customer_id).first()
    return _serialize_offer(offer, cust.name if cust else None)

@router.post("/{offer_id}/reject", response_model=OfferResponse)
def reject_offer(offer_id: str, db: Session = Depends(get_db)):
    offer = db.query(Offer).filter(Offer.id == offer_id).first()
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    offer.status = "Rejected"
    offer.decided_at = datetime.utcnow()
    db.commit()
    db.refresh(offer)
    cust = db.query(Customer).filter(Customer.id == offer.customer_id).first()
    return _serialize_offer(offer, cust.name if cust else None)

@router.patch("/{offer_id}", response_model=OfferResponse)
def patch_offer(offer_id: str, payload: OfferPatchRequest, db: Session = Depends(get_db)):
    offer = db.query(Offer).filter(Offer.id == offer_id).first()
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    if payload.drafted_message is not None:
        offer.drafted_message = payload.drafted_message
    if payload.discount_percent is not None:
        offer.discount_percent = payload.discount_percent
    offer.status = "Edited"
    db.commit()
    db.refresh(offer)
    cust = db.query(Customer).filter(Customer.id == offer.customer_id).first()
    return _serialize_offer(offer, cust.name if cust else None)
