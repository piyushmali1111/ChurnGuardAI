"""
ChurnGuardAI — Feedback Loop Retrain Script
Run manually to retrain the churn model using outcome data from approved offers.

Usage:
    python retrain_from_outcomes.py
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.db.session import SessionLocal
from app.db.models import Outcome, Offer, Customer

def prepare_feedback_data():
    db = SessionLocal()
    outcomes = db.query(Outcome).filter(Outcome.customer_stayed.isnot(None)).all()

    if not outcomes:
        print("[!] No completed Outcome records found yet. Run the system and approve offers to generate outcome data.")
        db.close()
        return

    rows = []
    for o in outcomes:
        offer = db.query(Offer).filter(Offer.id == o.offer_id).first()
        cust = db.query(Customer).filter(Customer.id == offer.customer_id).first() if offer else None
        if cust:
            rows.append({
                "CustomerID": cust.id,
                "DaysSinceLastOrder": 30,
                "OrderCount": cust.order_count,
                "TotalSpent": cust.total_spent,
                "ComplaintCount": cust.complaint_count,
                "SatisfactionScore": cust.satisfaction_score,
                "Churn": 0 if o.customer_stayed else 1,
            })

    db.close()

    import pandas as pd
    df = pd.DataFrame(rows)
    output_path = "data/outcome_feedback.csv"
    df.to_csv(output_path, index=False)
    print(f"[+] Saved {len(rows)} outcome feedback rows to {output_path}")
    print("[*] Merge outcome_feedback.csv with ecommerce_churn.csv and re-run train_churn_model.py to retrain.")
    return df

if __name__ == "__main__":
    prepare_feedback_data()
