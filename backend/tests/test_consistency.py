"""
Consistency and Acceptance Checklist for ChurnGuardAI (Section 12)
Validates all 12 acceptance criteria defined in the specification.
"""

import os
import sys
import math
from datetime import datetime
import unittest

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.db.models import Customer, Ticket, Offer, SystemSetting
from app.ml.sentiment_model import get_analyzer

client = TestClient(app)

class TestChurnGuardAIConsistency(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()

    def tearDown(self):
        self.db.close()

    def test_01_no_retainiq_matches(self):
        """1. grep -ri retainiq . returns 0 matches across all source code."""
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
        skip_dirs = {"node_modules", ".next", ".git", "__pycache__", ".venv"}
        skip_files = {"test_consistency.py"}
        matches = []
        target = "retain" + "iq"

        for root, dirs, files in os.walk(root_dir):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for file in files:
                if file in skip_files or file.endswith((".db", ".pyc", ".png", ".jpg", ".ico", ".log")):
                    continue
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        for line_no, line in enumerate(f, 1):
                            if target in line.lower():
                                matches.append(f"{filepath}:{line_no}: {line.strip()}")
                except Exception:
                    pass

        self.assertEqual(len(matches), 0, f"Found references in: {matches}")

    def test_02_get_settings_defaults(self):
        """2. GET /api/settings returns threshold=60, max_discount=25, scan_frequency=daily, fusion_alpha=0.7."""
        res = client.get("/api/settings")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("risk_threshold"), 60)
        self.assertEqual(data.get("max_discount_percent"), 25)
        self.assertEqual(data.get("scan_frequency"), "daily")
        self.assertAlmostEqual(data.get("fusion_alpha"), 0.7, places=2)

    def test_03_settings_update_dynamic_counts(self):
        """3. Updating threshold to 65 via PUT /api/settings immediately changes high_risk_count and status labels."""
        try:
            # Update threshold to 65
            put_res = client.put("/api/settings", json={"risk_threshold": 65})
            self.assertEqual(put_res.status_code, 200)

            # Check dashboard summary reflects threshold 65
            sum_res = client.get("/api/dashboard/summary")
            self.assertEqual(sum_res.status_code, 200)
            data = sum_res.json()
            self.assertEqual(data.get("risk_threshold"), 65)

            # Check customers filter by High Risk (>= 65)
            cust_res = client.get("/api/customers?risk_level=High Risk&page_size=100")
            self.assertEqual(cust_res.status_code, 200)
            items = cust_res.json()["items"]
            for c in items:
                self.assertGreaterEqual(c["churn_risk_score"], 65)
                self.assertEqual(c["churn_status"], "High Risk")
        finally:
            # Restore to 60
            client.put("/api/settings", json={"risk_threshold": 60})

    def test_04_total_customers_and_pagination(self):
        """4. Total customers in DB is 4,850; GET /api/customers?page=1&page_size=25 returns items of length 25 and total=4850."""
        count = self.db.query(Customer).count()
        self.assertEqual(count, 4850)

        res = client.get("/api/customers?page=1&page_size=25")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("total"), 4850)
        self.assertEqual(len(data.get("items", [])), 25)
        self.assertEqual(data.get("page"), 1)
        self.assertEqual(data.get("page_size"), 25)

    def test_05_calibrated_churn_scores(self):
        """5. All displayed churn scores in DB are between 1 and 99 (prompt v2)."""
        customers = self.db.query(Customer).all()
        invalid_scores = [c.id for c in customers if c.churn_risk_score < 1.0 or c.churn_risk_score > 99.0]
        self.assertEqual(len(invalid_scores), 0, f"Found invalid scores for: {invalid_scores}")

    def test_06_complaint_count_matches_ticket_count(self):
        """6. For every customer in DB, complaint_count == len(tickets) (0 mismatches across all 4,850)."""
        customers = self.db.query(Customer).all()
        mismatches = []
        for c in customers:
            actual_tickets = self.db.query(Ticket).filter(Ticket.customer_id == c.id).count()
            if c.complaint_count != actual_tickets:
                mismatches.append((c.id, c.complaint_count, actual_tickets))
        self.assertEqual(len(mismatches), 0, f"Found ticket count mismatches: {mismatches[:5]}")

    def test_07_ticket_stories_match_order_dates(self):
        """7. For all tickets mentioning damaged/crushed/missing/wrong, the customer's last order is <= 14 days before the ticket date (0 failures)."""
        keywords = ["damaged", "crushed", "missing", "wrong"]
        tickets = self.db.query(Ticket).all()
        failures = []

        for t in tickets:
            if any(k in t.message.lower() for k in keywords):
                cust = self.db.query(Customer).filter(Customer.id == t.customer_id).first()
                t_date = t.created_at.date() if isinstance(t.created_at, datetime) else datetime.fromisoformat(t.created_at).date()
                c_date = datetime.fromisoformat(cust.last_order_date).date()
                diff_days = (t_date - c_date).days
                if not (0 <= diff_days <= 14):
                    failures.append((t.id, t.message, diff_days))

        self.assertEqual(len(failures), 0, f"Found {len(failures)} failures on Check 7: {failures}")

    def test_08_urgency_score_vader_formula(self):
        """8. For all tickets, urgency_score == floor((1 - compound) / 2 * 100) (0 mismatches across all tickets)."""
        sia = get_analyzer()
        tickets = self.db.query(Ticket).all()
        mismatches = []

        for t in tickets:
            score_dict = sia.polarity_scores(t.message)
            compound = score_dict["compound"]
            expected_urgency = max(0, min(100, math.floor((1.0 - compound) / 2.0 * 100.0)))
            if t.urgency_score != expected_urgency:
                mismatches.append((t.id, t.urgency_score, expected_urgency))

        self.assertEqual(len(mismatches), 0, f"Found urgency score mismatches: {mismatches}")

    def test_09_shap_bars_in_points_and_sum(self):
        """9. All SHAP bar contributions in the API are in points (no %), and abs(sum(points) - (score - base_score)) < 1.0."""
        demo_ids = ["CUST-1000", "CUST-1001", "CUST-1002", "CUST-1003"]
        for cid in demo_ids:
            res = client.get(f"/api/customers/{cid}")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            shap_factors = data.get("shap_factors", [])
            base_score = data.get("base_score")
            score = data.get("churn_risk_score")

            self.assertIsNotNone(base_score)
            self.assertIsNotNone(score)
            self.assertGreater(len(shap_factors), 0)

            total_pts = 0.0
            for f in shap_factors:
                self.assertIn("points", f)
                self.assertNotIn("%", str(f.get("label", "")))
                if f.get("feature") not in ["ReturnRate", "DiscountUsageRate"]:
                    self.assertNotIn("%", str(f.get("value", "")))
                total_pts += f["points"]

            expected_delta = score - base_score
            self.assertLess(abs(total_pts - expected_delta), 1.0)

    def test_10_support_agent_no_promises(self):
        """10. The word 're-shipping' or 'refund has been issued' appears nowhere in support agent replies for unapproved tickets."""
        tickets = self.db.query(Ticket).all()
        violations = []
        banned = ["re-shipping", "reshipping", "refund has been issued", "store credit has been issued"]

        for t in tickets:
            if t.agent_reply:
                rep_lower = t.agent_reply.lower()
                for b in banned:
                    if b in rep_lower:
                        violations.append((t.id, b, t.agent_reply))

        self.assertEqual(len(violations), 0, f"Found commitment violations in support agent replies: {violations}")

    def test_11_retention_agent_no_hallucinations(self):
        """11. No retention offer draft contains the words 'cart', 'checkout', 'promo code', or 'tracking'."""
        offers = self.db.query(Offer).all()
        violations = []
        banned = ["cart", "checkout", "promo code", "tracking"]

        for o in offers:
            msg_lower = o.drafted_message.lower()
            for b in banned:
                if b in msg_lower:
                    violations.append((o.id, b, o.drafted_message))

        self.assertEqual(len(violations), 0, f"Found hallucinated words in offer drafts: {violations}")

    def test_12_weekly_cohort_8_weeks_labelled(self):
        """12. Customer cohort retention chart renders 8 columns labelled W1 to W8."""
        res = client.get("/api/dashboard/summary")
        self.assertEqual(res.status_code, 200)
        weekly = res.json().get("weekly_trend", [])
        self.assertEqual(len(weekly), 8)
        weeks = [w["week"] for w in weekly]
        self.assertEqual(weeks, ["W1", "W2", "W3", "W4", "W5", "W6", "W7", "W8"])

if __name__ == "__main__":
    unittest.main()
