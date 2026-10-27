import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
import random
from datetime import datetime, timedelta
from app.db.session import SessionLocal, engine
from app.db.models import Base, Customer, Ticket, Offer, SystemSetting
from app.ml.sentiment_model import analyze_sentiment
from app.ml.churn_predictor import predict_churn_risk
from app.services.metrics import get_status_label
from app.config import settings as app_settings

ANGRY_TEMPLATES = [
    ("Item arrived crushed and broken. Box had zero padding. Want immediate refund now!", "damaged"),
    ("My order has not arrived after two weeks. Extremely disappointed and furious with this terrible service.", "delayed"),
    ("Worst customer experience ever. Completely wrong item sent and unacceptable delay. Refund now!", "wrong"),
    ("Package was torn open and items are missing. This is unacceptable and terrible service.", "missing"),
    ("Horrible product quality, arrived completely damaged and unusable. I am furious and want my money back.", "damaged"),
    ("Order arrived broken into pieces. Awful packaging and useless support. Extremely angry!", "damaged"),
    ("Still waiting for my delayed order. Two weeks late and courier says nothing. Terrible!", "delayed"),
    ("Received completely wrong size and color. Totally disappointed and unacceptable.", "wrong"),
]

NEUTRAL_TEMPLATES = [
    ("Check the delivery status of order #8841.", "status"),
    ("I need to update the delivery address for order #4912.", "address"),
    ("Can you assist with a size exchange for order #7712?", "exchange"),
    ("Inquiring about product warranty details for my recent purchase.", "inquiry"),
    ("Would like instructions for processing a standard return.", "return"),
    ("Checking if standard ground shipping is available to my postal code.", "shipping"),
    ("Requesting an invoice copy for my recent order.", "invoice"),
    ("How do I update my notification preferences?", "account"),
]

HAPPY_TEMPLATES = [
    ("Thank you so much for the quick help! The replacement arrived perfectly and I love it.", "praise"),
    ("Outstanding customer support and great product quality. Thank you so much!", "praise"),
    ("Really appreciate the wonderful assistance from your team. Best shopping experience!", "praise"),
    ("Loved the fast shipping and excellent packaging. Great job!", "praise"),
    ("Exceptional experience shopping here. The item is fantastic and support was very helpful!", "praise"),
]

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

    print("[*] Seeding database with 4,850 customers and consistent tickets/offers...")
    # Initialize settings table
    setting = db.query(SystemSetting).filter(SystemSetting.id == 1).first()
    if not setting:
        setting = SystemSetting(
            id=1,
            risk_threshold=60,
            max_discount_percent=25,
            scan_frequency="daily",
        )
        db.add(setting)
        db.commit()

    threshold = setting.risk_threshold
    today = datetime.utcnow().date()

    # Define Named Demo Customers
    # Relative dates ensuring:
    # - Lucas: damaged item ticket 5 days ago; last order 10 days ago (5 days before ticket <= 14 days)
    # - Elena: delayed delivery ticket 6 days ago; last order 16 days ago (10 days before ticket within 7-21 days)
    demo_specs = [
        {
            "id": "CUST-4491",
            "name": "Lucas Vance",
            "email": "lucas.v@vancemedia.co",
            "signup_days": 420,
            "order_days": 10,
            "order_count": 8,
            "total_spent": 1250.0,
            "complaint_count": 4,
            "satisfaction_score": 1.8,
            "tickets": [
                {
                    "msg": "Item arrived crushed and broken. Box had zero padding. Want immediate refund now!",
                    "days_ago": 5, # 5 days ago (order was 10 days ago -> 5 days after order <= 14 days)
                    "category": "damaged",
                    "reply": "Hi Lucas, we deeply apologize for the damaged item! We have flagged your ticket for urgent inspection, and our team is reviewing this and will confirm next steps shortly."
                },
                {
                    "msg": "Billing discrepancy: was charged twice on subscription renewal invoice last month. Please reverse.",
                    "days_ago": 45,
                    "category": "billing",
                    "reply": "Hi Lucas, we apologize for the billing issue and have escalated this to finance for review."
                },
                {
                    "msg": "Customer portal search filters keep freezing whenever I view order history archives.",
                    "days_ago": 90,
                    "category": "technical",
                    "reply": "Hi Lucas, our engineering team has deployed an update to fix the search filter performance."
                },
                {
                    "msg": "Please remove promotional paper mailers from my physical mailing address.",
                    "days_ago": 130,
                    "category": "account",
                    "reply": "Hi Lucas, your physical mailer preferences have been updated in your profile."
                },
            ]
        },
        {
            "id": "CUST-8021",
            "name": "Elena Rostova",
            "email": "elena.r@luxdesign.co",
            "signup_days": 380,
            "order_days": 16,
            "order_count": 12,
            "total_spent": 1840.50,
            "complaint_count": 3,
            "satisfaction_score": 2.0,
            "tickets": [
                {
                    "msg": "My order has not arrived after two weeks. Extremely disappointed and furious with this terrible service.",
                    "days_ago": 6, # order was 16 days ago -> 10 days after order (within 7-21 days)
                    "category": "delayed",
                    "reply": "Dear Elena, we sincerely apologize for the shipping delay. We have contacted our courier team to trace your package, and our team is reviewing this and will confirm next steps shortly."
                },
                {
                    "msg": "Account portal session timed out during promotional checkout and discount wasn't recorded.",
                    "days_ago": 70,
                    "category": "account",
                    "reply": "Dear Elena, we have refreshed your portal session and verified your account profile."
                },
                {
                    "msg": "Inquiring about custom monogramming options and catalog samples.",
                    "days_ago": 110,
                    "category": "inquiry",
                    "reply": "Dear Elena, our custom production line had a temporary delay. We have expedited completion."
                },
            ]
        },
        {
            "id": "CUST-5510",
            "name": "Sophia Chen",
            "email": "sophia.chen@studio-art.com",
            "signup_days": 210,
            "order_days": 35,
            "order_count": 5,
            "total_spent": 890.0,
            "complaint_count": 2,
            "satisfaction_score": 2.4,
            "tickets": [
                {
                    "msg": "Horrible product quality, arrived completely damaged and unusable. I am furious and want my money back.",
                    "days_ago": 30, # order was 35 days ago -> 5 days after order <= 14 days
                    "category": "damaged",
                    "reply": "Hi Sophia, we deeply apologize for the quality issue. We have logged your request for review."
                },
                {
                    "msg": "Check the delivery status of order #8841.",
                    "days_ago": 95,
                    "category": "status",
                    "reply": "Hi Sophia, your order has been tracked and is currently en route."
                },
            ]
        },
        {
            "id": "CUST-3312",
            "name": "Devon Miller",
            "email": "devon.m@techops.net",
            "signup_days": 280,
            "order_days": 24,
            "order_count": 9,
            "total_spent": 1250.0,
            "complaint_count": 1,
            "satisfaction_score": 3.4,
            "tickets": [
                {
                    "msg": "I need to update the delivery address for order #4912.",
                    "days_ago": 20,
                    "category": "address",
                    "reply": "Hi Devon, your delivery address has been verified and updated."
                }
            ]
        },
        {
            "id": "CUST-9142",
            "name": "Marcus Sterling",
            "email": "m.sterling@apexventures.io",
            "signup_days": 500,
            "order_days": 18,
            "order_count": 24,
            "total_spent": 3420.0,
            "complaint_count": 0,
            "satisfaction_score": 4.5,
            "tickets": []
        },
        {
            "id": "CUST-1049",
            "name": "Amara Thorne",
            "email": "amara@thorne-designs.org",
            "signup_days": 600,
            "order_days": 8,
            "order_count": 38,
            "total_spent": 5120.0,
            "complaint_count": 0,
            "satisfaction_score": 4.9,
            "tickets": []
        },
    ]

    named_customers = []
    all_tickets = []
    named_offers = []

    for spec in demo_specs:
        last_ord_str = (today - timedelta(days=spec["order_days"])).isoformat()
        signup_str = (today - timedelta(days=spec["signup_days"])).isoformat()

        feat = {
            "DaysSinceLastOrder": spec["order_days"],
            "OrderCount": spec["order_count"],
            "TotalSpent": spec["total_spent"],
            "ComplaintCount": spec["complaint_count"],
            "SatisfactionScore": spec["satisfaction_score"],
        }
        score = predict_churn_risk(feat)
        score = max(2, min(98, score))
        status = get_status_label(score, threshold)

        cust = Customer(
            id=spec["id"],
            name=spec["name"],
            email=spec["email"],
            signup_date=signup_str,
            last_order_date=last_ord_str,
            order_count=spec["order_count"],
            total_spent=spec["total_spent"],
            complaint_count=spec["complaint_count"],
            satisfaction_score=spec["satisfaction_score"],
            churn_risk_score=score,
            baseline_score=score,
            urgency_score=None,
            fused_score=score,
            churn_status=status,
        )
        named_customers.append(cust)

        # Generate tickets
        for t_spec in spec["tickets"]:
            t_dt = datetime.utcnow() - timedelta(days=t_spec["days_ago"])
            s_res = analyze_sentiment(t_spec["msg"])
            tck = Ticket(
                id=f"TCK-{len(all_tickets)+101}",
                customer_id=spec["id"],
                message=t_spec["msg"],
                sentiment_label=s_res["sentiment_label"],
                sentiment_score=s_res["sentiment_score"],
                urgency_score=s_res["urgency_score"],
                baseline_score=score,
                fused_score=round(0.7 * score + 0.3 * s_res["urgency_score"]),
                agent_reply=t_spec["reply"],
                created_at=t_dt,
            )
            all_tickets.append(tck)
            # Update customer latest urgency/fused if most recent ticket
            if t_spec["days_ago"] <= 10:
                cust.urgency_score = s_res["urgency_score"]
                cust.fused_score = round(0.7 * score + 0.3 * s_res["urgency_score"])

    db.add_all(named_customers)
    db.commit()

    # Initial Offers for high-risk named customers
    # Lucas: ticket TCK-101
    tck_lucas = all_tickets[0]
    lucas_cust = named_customers[0]
    lucas_fused = round(0.7 * lucas_cust.churn_risk_score + 0.3 * tck_lucas.urgency_score)
    named_offers.append(
        Offer(
            id="OFFER-105",
            customer_id=lucas_cust.id,
            ticket_id=tck_lucas.id,
            drafted_message="Hi Lucas, we appreciate your loyalty with us! Please accept an exclusive 20% courtesy discount on your next order with code GUARD20-LUCAS.",
            discount_percent=20,
            reasoning="Satisfaction 1.8/5.0, 4 complaints, angry ticket regarding damaged package",
            baseline_score=lucas_cust.churn_risk_score,
            urgency_score=tck_lucas.urgency_score,
            fused_score=lucas_fused,
            status="Pending",
            created_at=datetime.utcnow() - timedelta(days=5),
        )
    )

    # Elena: ticket TCK-105
    tck_elena = all_tickets[4]
    elena_cust = named_customers[1]
    elena_fused = round(0.7 * elena_cust.churn_risk_score + 0.3 * tck_elena.urgency_score)
    named_offers.append(
        Offer(
            id="OFFER-101",
            customer_id=elena_cust.id,
            ticket_id=tck_elena.id,
            drafted_message="Hi Elena, we value your business! Please accept an exclusive 20% discount on your next order with code GUARD20-ELENA.",
            discount_percent=20,
            reasoning="Satisfaction 2.0/5.0, 3 complaints, angry ticket regarding delayed shipment",
            baseline_score=elena_cust.churn_risk_score,
            urgency_score=tck_elena.urgency_score,
            fused_score=elena_fused,
            status="Pending",
            created_at=datetime.utcnow() - timedelta(days=6),
        )
    )

    # Sophia: proactive offer (no ticket)
    sophia_cust = named_customers[2]
    named_offers.append(
        Offer(
            id="OFFER-103",
            customer_id=sophia_cust.id,
            ticket_id=None,
            drafted_message="Hi Sophia, we value your partnership! Please accept an exclusive 15% discount on your next order with code GUARD15-SOPHIA.",
            discount_percent=15,
            reasoning="Days since last order 35 days, satisfaction rating 2.4/5.0, proactive retention scan",
            baseline_score=sophia_cust.churn_risk_score,
            urgency_score=None,
            fused_score=sophia_cust.churn_risk_score,
            status="Pending",
            created_at=datetime.utcnow() - timedelta(days=3),
        )
    )

    # Proactive VIP offer for Marcus
    marcus_cust = named_customers[4]
    named_offers.append(
        Offer(
            id="OFFER-102",
            customer_id=marcus_cust.id,
            ticket_id=None,
            drafted_message="Hi Marcus, thank you for being a valued customer! Here is an exclusive 15% VIP discount code (GUARD15-MARCUS) on your next order.",
            discount_percent=15,
            reasoning="Lifetime spend $3,420.00, proactive VIP appreciation retention offer",
            baseline_score=marcus_cust.churn_risk_score,
            urgency_score=None,
            fused_score=marcus_cust.churn_risk_score,
            status="Pending",
            created_at=datetime.utcnow() - timedelta(days=4),
        )
    )

    # Now generate the remaining 4,844 customers to reach exactly 4,850 customers
    random.seed(42)
    n_remaining = 4850 - len(named_customers)
    extra_customers = []

    # Pre-select ~40 customers who will receive complaints to reach ~50 total tickets
    # target ticket mix: 35% angry (~18), 40% neutral (~20), 25% happy (~12)
    # We already have 10 tickets from demo customers (7 angry, 3 neutral).
    # Remaining tickets to generate: ~11 angry, ~17 neutral, ~12 happy (~40 tickets).
    remaining_ticket_specs = []
    for _ in range(11):
        tmpl, cat = random.choice(ANGRY_TEMPLATES)
        remaining_ticket_specs.append((tmpl, cat, "Angry"))
    for _ in range(17):
        tmpl, cat = random.choice(NEUTRAL_TEMPLATES)
        remaining_ticket_specs.append((tmpl, cat, "Neutral"))
    for _ in range(12):
        tmpl, cat = random.choice(HAPPY_TEMPLATES)
        remaining_ticket_specs.append((tmpl, cat, "Happy"))
    random.shuffle(remaining_ticket_specs)

    # Assign tickets to distinct customers so each customer with complaints gets exactly 1 ticket
    ticket_assigned_idx = 0

    FIRST_NAMES = ["Liam", "Noah", "Oliver", "James", "Elijah", "Mateo", "Theodore", "Henry", "Lucas", "William",
                   "Olivia", "Emma", "Charlotte", "Amelia", "Sophia", "Mia", "Isabella", "Ava", "Evelyn", "Luna"]
    LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
                  "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin"]

    existing_ids = {spec["id"] for spec in demo_specs}
    current_id_counter = 1000

    while len(extra_customers) < n_remaining:
        cust_id = f"CUST-{current_id_counter}"
        current_id_counter += 1
        if cust_id in existing_ids:
            continue

        i = len(extra_customers)
        name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
        email = f"{name.lower().replace(' ', '.')}{i}@example.com"
        signup_days = random.randint(30, 720)

        # Decide if this customer has a ticket assigned
        if ticket_assigned_idx < len(remaining_ticket_specs):
            msg, cat, s_type = remaining_ticket_specs[ticket_assigned_idx]
            ticket_assigned_idx += 1
            has_ticket = True
            c_count = 1
        else:
            has_ticket = False
            c_count = 0

        if has_ticket:
            msg_lower = msg.lower()
            if any(w in msg_lower for w in ["damaged", "crushed", "missing", "wrong"]):
                # Check 7 requirement: last_order_date within 14 days before ticket!
                tck_days_ago = random.randint(2, 20)
                # order was 3 to 12 days before the ticket
                order_days = tck_days_ago + random.randint(3, 12)
            elif any(w in msg_lower for w in ["delayed", "late", "arrived after"]):
                tck_days_ago = random.randint(2, 20)
                order_days = tck_days_ago + random.randint(7, 18)
            else:
                tck_days_ago = random.randint(2, 40)
                order_days = tck_days_ago + random.randint(1, 20)
        else:
            order_days = int(random.expovariate(1 / 28.0)) + 1
            if order_days > signup_days:
                order_days = random.randint(1, min(signup_days, 60))

        order_count = int(random.expovariate(1 / 8.0)) + 1
        total_spent = round(order_count * random.uniform(40.0, 160.0), 2)
        sat_base = 4.2 - (c_count * 0.8)
        satisfaction = round(max(1.0, min(5.0, random.normalvariate(sat_base, 0.6))), 1)

        feat = {
            "DaysSinceLastOrder": order_days,
            "OrderCount": order_count,
            "TotalSpent": total_spent,
            "ComplaintCount": c_count,
            "SatisfactionScore": satisfaction,
        }
        score = predict_churn_risk(feat)
        score = max(2, min(98, score))
        status = get_status_label(score, threshold)

        last_ord_str = (today - timedelta(days=order_days)).isoformat()
        signup_str = (today - timedelta(days=signup_days)).isoformat()

        c_obj = Customer(
            id=cust_id,
            name=name,
            email=email,
            signup_date=signup_str,
            last_order_date=last_ord_str,
            order_count=order_count,
            total_spent=total_spent,
            complaint_count=c_count,
            satisfaction_score=satisfaction,
            churn_risk_score=score,
            baseline_score=score,
            urgency_score=None,
            fused_score=score,
            churn_status=status,
        )
        extra_customers.append(c_obj)

        if has_ticket:
            t_dt = datetime.utcnow() - timedelta(days=tck_days_ago)
            s_res = analyze_sentiment(msg)
            t_obj = Ticket(
                id=f"TCK-{len(all_tickets)+101}",
                customer_id=cust_id,
                message=msg,
                sentiment_label=s_res["sentiment_label"],
                sentiment_score=s_res["sentiment_score"],
                urgency_score=s_res["urgency_score"],
                baseline_score=score,
                fused_score=round(0.7 * score + 0.3 * s_res["urgency_score"]),
                agent_reply=f"Hi {name}, we have logged your inquiry and our operations team is reviewing next steps.",
                created_at=t_dt,
            )
            all_tickets.append(t_obj)
            c_obj.urgency_score = s_res["urgency_score"]
            c_obj.fused_score = round(0.7 * score + 0.3 * s_res["urgency_score"])

    # Batch add all customers
    db.add_all(extra_customers)
    db.commit()

    # Batch add all tickets
    db.add_all(all_tickets)
    db.commit()

    # Batch add all initial offers
    db.add_all(named_offers)
    db.commit()

    total_c = db.query(Customer).count()
    total_t = db.query(Ticket).count()
    total_o = db.query(Offer).count()
    print(f"[+] Successfully seeded: {total_c} customers, {total_t} tickets, {total_o} offers.")
    db.close()

if __name__ == "__main__":
    reseed_flag = "--reseed" in sys.argv
    seed_db(reseed=reseed_flag)
