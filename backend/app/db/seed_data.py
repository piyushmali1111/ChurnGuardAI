import os
import sys
import random
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from faker import Faker

# Ensure backend root is in sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.db.session import SessionLocal, engine
from app.db.models import Base, Customer, Ticket, Offer, SystemSetting, Outcome
from app.ml.sentiment_model import analyze_sentiment
from app.ml.churn_predictor import score_to_status
from app.config import settings as app_settings

ANGRY_TEMPLATES = [
    ("Item arrived crushed. Box had zero padding. Want immediate store credit or refund.", "damaged"),
    ("My order arrived completely damaged and missing items! This is unacceptable and I want a refund!", "damaged"),
    ("Still waiting for my delayed order. Two weeks late and courier says nothing. Terrible service and unacceptable!", "delayed"),
    ("Package was torn open and items are missing. This is unacceptable and terrible service.", "missing"),
    ("Horrible product quality, arrived completely broken and unusable. I am furious and want my money back.", "damaged"),
    ("Received completely wrong size and color. Totally disappointed and unacceptable.", "wrong"),
    ("I stopped ordering after my last delivery problem, nobody followed up or cared.", "inactivity"),
    ("Third time my delivery is late this month. Completely unacceptable customer service.", "delayed"),
]

NEUTRAL_TEMPLATES = [
    ("Check the delivery status of order #8841.", "status"),
    ("Hi, can I change the delivery address for my order?", "address"),
    ("Can you assist with a size exchange for order #7712?", "exchange"),
    ("Inquiring about product warranty details for my recent purchase.", "inquiry"),
    ("Would like instructions for processing a standard return.", "return"),
    ("Checking if standard ground shipping is available to my postal code.", "shipping"),
    ("Requesting an invoice copy for my recent order.", "invoice"),
    ("How do I update my notification preferences?", "account"),
]

HAPPY_TEMPLATES = [
    ("Thanks so much, the package arrived early and everything looks great!", "praise"),
    ("Outstanding customer support and great product quality. Thank you so much!", "praise"),
    ("Really appreciate the wonderful assistance from your team. Best shopping experience!", "praise"),
    ("Loved the fast shipping and excellent packaging. Great job!", "praise"),
    ("Exceptional experience shopping here. The item is fantastic and support was very helpful!", "praise"),
]

EMAIL_DOMAINS = (
    ["gmail.com"] * 50
    + ["outlook.com"] * 10
    + ["hotmail.com"] * 5
    + ["yahoo.com"] * 12
    + ["icloud.com"] * 8
    + ["proton.me"] * 3
    + ["novaretail.co", "acmeworks.io", "strataflow.net", "zenithcorp.org", "vanguardtech.io", "apexretail.org"] * 2
)


def generate_email(first_name: str, last_name: str, rng: random.Random) -> str:
    clean_first = "".join(c for c in first_name.lower() if c.isalnum())
    clean_last = "".join(c for c in last_name.lower() if c.isalnum())
    domain = rng.choice(EMAIL_DOMAINS)
    pattern = rng.choice(["dot", "number", "flast", "underscore"])

    if pattern == "dot":
        return f"{clean_first}.{clean_last}@{domain}"
    elif pattern == "number":
        num = rng.randint(10, 99)
        return f"{clean_first}{clean_last}{num}@{domain}"
    elif pattern == "flast":
        f_init = clean_first[:1] if clean_first else "c"
        return f"{f_init}{clean_last}@{domain}"
    else:
        return f"{clean_first}_{clean_last}@{domain}"


def seed_db(reseed: bool = False):
    if reseed:
        print("[*] Reseed flag provided. Dropping all tables...")
        Base.metadata.drop_all(bind=engine)

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    if not reseed and db.query(Customer).count() >= 4850:
        print(f"[+] DB already contains seeded data ({db.query(Customer).count()} customers).")
        db.close()
        return

    print("[*] Loading CSV dataset and out-of-fold scores...")
    csv_path = os.path.join(backend_dir, "data", "ecommerce_churn.csv")
    oof_path = os.path.join(backend_dir, "models", "oof_scores.csv")

    if not os.path.exists(csv_path) or not os.path.exists(oof_path):
        from generate_synthetic_data import generate_synthetic_data
        from app.ml.train_churn_model import train_and_evaluate
        generate_synthetic_data(force=True, check=True)
        train_and_evaluate()

    df = pd.read_csv(csv_path)
    oof_df = pd.read_csv(oof_path)
    oof_map = dict(zip(oof_df["CustomerID"], oof_df["score"]))

    # 1. Initialize settings table
    setting = db.query(SystemSetting).filter(SystemSetting.id == 1).first()
    if not setting:
        setting = SystemSetting(
            id=1,
            risk_threshold=app_settings.RISK_THRESHOLD,
            max_discount_percent=app_settings.MAX_DISCOUNT_PERCENT,
            scan_frequency="daily",
        )
        db.add(setting)
        db.commit()

    threshold = setting.risk_threshold
    today = datetime.now().date()
    rng = random.Random(42)
    fake_us = Faker("en_US")
    fake_in = Faker("en_IN")
    fake_gb = Faker("en_GB")
    fakers = [fake_us, fake_in, fake_gb]

    named_demos = {
        "CUST-1000": {"name": "Lucas Vance", "email": "lucas.v@vancemedia.co"},
        "CUST-1001": {"name": "Elena Rostova", "email": "elena.r@luxdesign.co"},
        "CUST-1002": {"name": "Sophia Chen", "email": "sophia.chen@studio-art.com"},
        "CUST-1003": {"name": "Devon Miller", "email": "devon.m@techops.net"},
        "CUST-1004": {"name": "Marcus Sterling", "email": "m.sterling@apexventures.io"},
        "CUST-1005": {"name": "Amara Thorne", "email": "amara@thorne-designs.org"},
    }

    print(f"[*] Seeding {len(df)} customers directly from CSV with exact out-of-fold scores...")

    customers = []
    all_tickets = []
    offers = []

    for idx, row in df.iterrows():
        cust_id = row["CustomerID"]
        oof_score = float(oof_map.get(cust_id, 25.0))
        status = score_to_status(oof_score, threshold)

        if cust_id in named_demos:
            c_name = named_demos[cust_id]["name"]
            c_email = named_demos[cust_id]["email"]
        else:
            fkr = rng.choice(fakers)
            first = fkr.first_name()
            last = fkr.last_name()
            c_name = f"{first} {last}"
            c_email = generate_email(first, last, rng)

        signup_date_str = str(row["SignupDate"])
        last_order_date_str = str(row["LastOrderDate"])
        days_inactive = int(row["DaysSinceLastOrder"])
        last_order_d = today - timedelta(days=days_inactive)

        cust = Customer(
            id=cust_id,
            name=c_name,
            email=c_email,
            signup_date=signup_date_str,
            last_order_date=last_order_date_str,
            order_count=int(row["OrderCount"]),
            total_spent=float(row["TotalSpent"]),
            complaint_count=int(row["ComplaintCount"]),
            satisfaction_score=float(row["SatisfactionScore"]),
            tenure_months=float(row["TenureMonths"]),
            return_rate=float(row["ReturnRate"]),
            discount_usage_rate=float(row["DiscountUsageRate"]),
            churn_risk_score=round(oof_score, 1),
            baseline_score=int(round(oof_score)),
            urgency_score=None,
            fused_score=round(oof_score, 1),
            churn_status=status,
            model_version="v2-calibrated-xgb",
            scored_at=datetime.utcnow(),
        )
        customers.append(cust)

        # Generate lightweight historical tickets matching complaint_count
        comp_count = int(row["ComplaintCount"])
        if comp_count > 0:
            cust_tickets = []

            # Custom handling for Lucas Vance (4 tickets, order was 24 days ago)
            if cust_id == "CUST-1000":
                # Ticket 1 (active damaged item): 16 days ago (8 days after order -> within 3-14 days!)
                t1_dt = datetime.utcnow() - timedelta(days=16)
                t1_msg = "Item arrived crushed. Box had zero padding. Want immediate store credit or refund."
                s1 = analyze_sentiment(t1_msg)
                f1_score = round(0.7 * oof_score + 0.3 * s1["urgency_score"], 1)
                cust.urgency_score = s1["urgency_score"]
                cust.fused_score = f1_score

                cust_tickets.append(Ticket(
                    id=f"TCK-{cust_id}-1",
                    customer_id=cust_id,
                    message=t1_msg,
                    sentiment_label=s1["sentiment_label"],
                    sentiment_score=s1["urgency_score"],
                    urgency_score=s1["urgency_score"],
                    baseline_score=int(round(oof_score)),
                    fused_score=f1_score,
                    agent_reply="Hi Lucas, we deeply apologize for the damaged item! We have escalated this to our fulfillment leads and drafted a priority retention resolution.",
                    created_at=t1_dt,
                ))

                # Historical resolved tickets for Lucas (avoid physical damage keywords)
                hist_lucas = [
                    ("Billing discrepancy: double charge on renewal invoice. Please refund.", 45, "Hi Lucas, the duplicate charge has been reversed."),
                    ("Delivery delayed by 8 days without courier tracking updates.", 90, "Hi Lucas, your tracking has been refreshed and courier expedited."),
                    ("Customer portal search filters keep freezing whenever I view order history.", 130, "Hi Lucas, our engineering team has deployed an update to fix the search filter performance."),
                ]
                for h_i, (h_msg, h_days, h_reply) in enumerate(hist_lucas, start=2):
                    h_dt = datetime.utcnow() - timedelta(days=h_days)
                    h_s = analyze_sentiment(h_msg)
                    cust_tickets.append(Ticket(
                        id=f"TCK-{cust_id}-{h_i}",
                        customer_id=cust_id,
                        message=h_msg,
                        sentiment_label=h_s["sentiment_label"],
                        sentiment_score=h_s["urgency_score"],
                        urgency_score=h_s["urgency_score"],
                        baseline_score=int(round(oof_score)),
                        fused_score=round(0.7 * oof_score + 0.3 * h_s["urgency_score"], 1),
                        agent_reply=h_reply,
                        created_at=h_dt,
                    ))

            # Custom handling for Elena Rostova (3 tickets, order was 26 days ago)
            elif cust_id == "CUST-1001":
                # Ticket 1 (delayed delivery): 14 days ago (12 days after order -> within 7-21 days!)
                t1_dt = datetime.utcnow() - timedelta(days=14)
                t1_msg = "Still waiting for my delayed order. Two weeks late and courier says nothing. Terrible service and unacceptable!"
                s1 = analyze_sentiment(t1_msg)
                f1_score = round(0.7 * oof_score + 0.3 * s1["urgency_score"], 1)
                cust.urgency_score = s1["urgency_score"]
                cust.fused_score = f1_score

                cust_tickets.append(Ticket(
                    id=f"TCK-{cust_id}-1",
                    customer_id=cust_id,
                    message=t1_msg,
                    sentiment_label=s1["sentiment_label"],
                    sentiment_score=s1["urgency_score"],
                    urgency_score=s1["urgency_score"],
                    baseline_score=int(round(oof_score)),
                    fused_score=f1_score,
                    agent_reply="Dear Elena, we sincerely apologize for the delay. We have contacted the regional carrier depot and expedited dispatch.",
                    created_at=t1_dt,
                ))

                hist_elena = [
                    ("Account portal session timed out during promotional checkout.", 60, "Dear Elena, your session preferences have been restored."),
                    ("Inquiring about catalog samples and expedited shipping.", 110, "Dear Elena, samples have been sent to your primary address."),
                ]
                for h_i, (h_msg, h_days, h_reply) in enumerate(hist_elena, start=2):
                    h_dt = datetime.utcnow() - timedelta(days=h_days)
                    h_s = analyze_sentiment(h_msg)
                    cust_tickets.append(Ticket(
                        id=f"TCK-{cust_id}-{h_i}",
                        customer_id=cust_id,
                        message=h_msg,
                        sentiment_label=h_s["sentiment_label"],
                        sentiment_score=h_s["urgency_score"],
                        urgency_score=h_s["urgency_score"],
                        baseline_score=int(round(oof_score)),
                        fused_score=round(0.7 * oof_score + 0.3 * h_s["urgency_score"], 1),
                        agent_reply=h_reply,
                        created_at=h_dt,
                    ))

            # General customers with complaint_count > 0
            else:
                for t_idx in range(comp_count):
                    if t_idx == 0 and 3 <= days_inactive <= 30:
                        delta_after = rng.randint(3, min(14, max(3, days_inactive)))
                        t_order_date = last_order_d + timedelta(days=delta_after)
                        if t_order_date > today:
                            t_order_date = today
                        t_dt = datetime.combine(t_order_date, datetime.min.time()) + timedelta(hours=rng.randint(9, 18))
                        msg, cat = rng.choice([
                            ("Item arrived crushed. Box had zero padding. Want immediate store credit or refund.", "damaged"),
                            ("My order arrived completely damaged and missing items! This is unacceptable and I want a refund!", "damaged"),
                            ("Package was torn open and items are missing. This is unacceptable and terrible service.", "missing"),
                            ("Received completely wrong size and color. Totally disappointed and unacceptable.", "wrong"),
                        ])
                    elif days_inactive > 60:
                        dt_days = rng.randint(30, min(120, days_inactive))
                        t_dt = datetime.utcnow() - timedelta(days=dt_days)
                        msg, cat = ("I stopped ordering after my last delivery problem, nobody followed up or cared.", "inactivity")
                    else:
                        roll = rng.random()
                        if roll < 0.35:
                            msg, cat = rng.choice([
                                ("Still waiting for my delayed order. Two weeks late and courier says nothing. Terrible service and unacceptable!", "delayed"),
                                ("Third time my delivery is late this month. Completely unacceptable customer service.", "delayed"),
                                ("I stopped ordering after my last delivery problem, nobody followed up or cared.", "inactivity"),
                                ("Billing discrepancy on invoice renewal. Reverse the duplicate charge immediately.", "billing"),
                            ])
                        elif roll < 0.75:
                            msg, cat = rng.choice(NEUTRAL_TEMPLATES)
                        else:
                            msg, cat = rng.choice(HAPPY_TEMPLATES)
                        dt_days = rng.randint(10, 180)
                        t_dt = datetime.utcnow() - timedelta(days=dt_days)

                    # Strict check: if message contains physical damage keywords, t_dt must be within last_order_d to last_order_d + 14!
                    if any(k in msg.lower() for k in ["damaged", "crushed", "missing", "wrong"]):
                        delta_valid = rng.randint(3, min(14, max(3, days_inactive)))
                        valid_t_date = last_order_d + timedelta(days=delta_valid)
                        if valid_t_date > today:
                            valid_t_date = today
                        t_dt = datetime.combine(valid_t_date, datetime.min.time()) + timedelta(hours=14)
                    s_res = analyze_sentiment(msg)
                    t_fused = round(0.7 * oof_score + 0.3 * s_res["urgency_score"], 1)

                    if t_idx == 0:
                        cust.urgency_score = s_res["urgency_score"]
                        cust.fused_score = t_fused

                    cust_tickets.append(Ticket(
                        id=f"TCK-{cust_id}-{t_idx + 1}",
                        customer_id=cust_id,
                        message=msg,
                        sentiment_label=s_res["sentiment_label"],
                        sentiment_score=s_res["urgency_score"],
                        urgency_score=s_res["urgency_score"],
                        baseline_score=int(round(oof_score)),
                        fused_score=t_fused,
                        agent_reply=f"Resolved ticket for order inquiry ({cat})." if t_idx > 0 else "Our team has reviewed your complaint and initiated retention outreach.",
                        created_at=t_dt,
                    ))

            all_tickets.extend(cust_tickets)

    # 3. Create Pending Offers for approval inbox
    # Top 15 high-risk customers ranked by fused_score * total_spent
    print("[*] Generating pending retention offers for Approval Inbox...")
    high_risk_custs = [c for c in customers if c.churn_risk_score >= threshold]
    high_risk_custs.sort(key=lambda c: (c.fused_score or c.churn_risk_score) * c.total_spent, reverse=True)

    offer_candidates = high_risk_custs[:15]
    # Ensure Lucas and Elena are included in offer candidates
    lucas_cust = next((c for c in customers if c.id == "CUST-1000"), None)
    elena_cust = next((c for c in customers if c.id == "CUST-1001"), None)
    if lucas_cust and lucas_cust not in offer_candidates:
        offer_candidates.insert(0, lucas_cust)
    if elena_cust and elena_cust not in offer_candidates:
        offer_candidates.insert(1, elena_cust)

    for o_i, c in enumerate(offer_candidates[:14]):
        discount = min(app_settings.MAX_DISCOUNT_PERCENT, 20 if c.total_spent > 500 else 15)
        # Find primary ticket if exists
        p_ticket = next((t for t in all_tickets if t.customer_id == c.id), None)
        t_id = p_ticket.id if p_ticket else None

        if c.id == "CUST-1000":
            reasoning = f"Customer has low satisfaction ({c.satisfaction_score:.1f}/5.0), 4 past complaints, and a recent damaged item report. Fused risk {c.fused_score:.1f}. Recommending {discount}% discount on next order with expedited replacement."
            msg = f"Dear {c.name}, we are truly sorry for the damaged item you received. We have processed a replacement immediately, and here is a {discount}% discount coupon towards your next order: SAVE{discount}NOW."
        elif c.id == "CUST-1001":
            reasoning = f"High risk customer with 3 complaints, low satisfaction ({c.satisfaction_score:.1f}/5.0), and delayed delivery escalation. Recommending {discount}% discount retention voucher."
            msg = f"Dear {c.name}, we apologize for the unacceptable shipping delay. Your package has been tracked, and we are applying a {discount}% loyalty discount code: VIPRETAIN{discount} to your account."
        else:
            reasoning = f"High-risk customer (score {c.churn_risk_score:.1f}, {c.complaint_count} complaints, spend ${c.total_spent:,.2f}). Proactive Retention Agent drafted {discount}% discount."
            msg = f"Hi {c.name}, thank you for being a valued customer. Please enjoy {discount}% off your next purchase with code LOYAL{discount}."

        offers.append(Offer(
            id=f"OFF-{c.id}-{o_i + 1}",
            customer_id=c.id,
            ticket_id=t_id,
            drafted_message=msg,
            discount_percent=discount,
            reasoning=reasoning,
            baseline_score=c.baseline_score,
            urgency_score=c.urgency_score or 50,
            fused_score=c.fused_score,
            status="Pending",
            created_at=datetime.utcnow() - timedelta(hours=o_i * 2 + 1),
        ))

    print(f"[*] Bulk saving {len(customers)} customers, {len(all_tickets)} tickets, {len(offers)} offers...")
    db.bulk_save_objects(customers)
    db.commit()

    db.bulk_save_objects(all_tickets)
    db.commit()

    db.bulk_save_objects(offers)
    db.commit()

    db.close()
    print("[+] Database seeding completed successfully!")


if __name__ == "__main__":
    reseed_flag = "--reseed" in sys.argv
    seed_db(reseed=reseed_flag)
