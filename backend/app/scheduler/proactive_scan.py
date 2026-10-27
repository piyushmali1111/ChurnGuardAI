import uuid
import asyncio
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from app.db.session import SessionLocal
from app.db.models import Customer, Offer
from app.ml.churn_predictor import predict_churn_risk
from app.ml.shap_explainer import explain_churn_risk
from app.agents.orchestrator import run_agent_pipeline
from app.services.settings_service import get_system_settings
from app.services.metrics import get_status_label, get_total_customers, get_high_risk_count
from app.websocket.agent_activity import broadcaster

_scheduler = None

def compute_days_inactive(last_order_str: str) -> int:
    try:
        today = datetime.utcnow().date()
        order_date = datetime.strptime(last_order_str[:10], "%Y-%m-%d").date()
        return max(0, (today - order_date).days)
    except Exception:
        return 30

def run_proactive_scan_job():
    print(f"[SCAN] Proactive batch scan started at {datetime.utcnow().isoformat()}")
    db = SessionLocal()
    new_offers = 0

    try:
        settings_obj = get_system_settings(db)
        threshold = settings_obj.risk_threshold
        max_discount = settings_obj.max_discount_percent

        customers = db.query(Customer).all()
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
                cust.churn_risk_score = new_score
                cust.baseline_score = new_score
                cust.fused_score = new_score
                cust.churn_status = get_status_label(new_score, threshold)
            except Exception:
                pass

            existing = db.query(Offer).filter(
                Offer.customer_id == cust.id,
                Offer.status == "Pending"
            ).first()

            if cust.churn_risk_score >= threshold and not existing:
                shap_data = explain_churn_risk(feature_dict, cust.churn_risk_score)
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
                    od = result["verified_offer"]
                    db.add(Offer(
                        id=offer_id,
                        customer_id=cust.id,
                        ticket_id=None,
                        drafted_message=od.get("drafted_message", ""),
                        discount_percent=od.get("discount_percent", 10),
                        reasoning=od.get("reasoning", "Proactive scan flagged high churn risk."),
                        baseline_score=cust.churn_risk_score,
                        urgency_score=None,
                        fused_score=cust.churn_risk_score,
                        status="Pending",
                        created_at=datetime.utcnow(),
                    ))
                    new_offers += 1

        db.commit()

        total_count = get_total_customers(db)
        flagged_count = get_high_risk_count(db, threshold)
        print(f"[SCAN] Completed - {new_offers} new offers created.")

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

    except Exception as e:
        print(f"[SCAN ERROR] {e}")
    finally:
        db.close()

def start_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        return

    db = SessionLocal()
    try:
        settings_obj = get_system_settings(db)
        interval = settings_obj.scan_frequency
    finally:
        db.close()

    _scheduler = BackgroundScheduler()

    if interval == "weekly":
        _scheduler.add_job(run_proactive_scan_job, "cron", day_of_week="sun", hour=2)
        print("[SCHEDULER] Proactive scan scheduled: Weekly on Sunday at 02:00 UTC")
    else:
        _scheduler.add_job(run_proactive_scan_job, "cron", hour=3)
        print("[SCHEDULER] Proactive scan scheduled: Daily at 03:00 UTC")

    _scheduler.start()

def stop_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown()
