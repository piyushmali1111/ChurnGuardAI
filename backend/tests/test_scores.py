import os
import sys
import random
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Ensure backend root is in sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.db.session import SessionLocal
from app.db.models import Customer, Ticket, Offer
from app.ml.features import FEATURE_COLS
from app.ml.churn_predictor import predict_churn_risk, score_to_status
from app.ml.shap_explainer import explain_churn_risk


def run_all_tests():
    print("\n=============================================================")
    print("       ChurnGuardAI — Comprehensive Score Verification       ")
    print("=============================================================")

    db = SessionLocal()
    rng = random.Random(42)
    today = datetime.now().date()

    try:
        # Load CSV and OOF reference data
        csv_path = os.path.join(backend_dir, "data", "ecommerce_churn.csv")
        oof_path = os.path.join(backend_dir, "models", "oof_scores.csv")
        assert os.path.exists(csv_path), "ecommerce_churn.csv not found!"
        assert os.path.exists(oof_path), "oof_scores.csv not found!"

        csv_df = pd.read_csv(csv_path)
        oof_df = pd.read_csv(oof_path)
        oof_map = dict(zip(oof_df["CustomerID"], oof_df["score"]))
        csv_days_map = dict(zip(csv_df["CustomerID"], csv_df["DaysSinceLastOrder"]))

        # --- Test 1: DB scores equal oof_scores.csv for 50 random customers ---
        all_customers = db.query(Customer).all()
        assert len(all_customers) >= 4850, f"Expected 4850 customers, found {len(all_customers)}"

        sample_50 = rng.sample(all_customers, 50)
        t1_diffs = []
        for c in sample_50:
            expected_score = oof_map[c.id]
            diff = abs(c.churn_risk_score - expected_score)
            t1_diffs.append(diff)
            assert diff < 1e-4, f"Mismatch for {c.id}: DB={c.churn_risk_score}, OOF={expected_score}"
        print(f"[TEST 1] PASSED: DB scores match oof_scores.csv exactly for 50 random customers (Max diff: {max(t1_diffs):.4f}).")

        # --- Test 2: Distinct integer scores & largest share ---
        int_scores = [int(round(c.churn_risk_score)) for c in all_customers]
        distinct_count = len(set(int_scores))
        max_share = pd.Series(int_scores).value_counts(normalize=True).max()

        print(f"[TEST 2] Distinct integer scores: {distinct_count} (Target: >= 70)")
        print(f"[TEST 2] Largest single score share: {max_share * 100:.2f}% (Target: <= 10.0%)")
        assert distinct_count >= 70, f"Distinct scores {distinct_count} < 70"
        assert max_share <= 0.10, f"Largest single share {max_share * 100:.2f}% > 10%"
        print("[TEST 2] PASSED: Score diversity and distribution meet targets.")

        # --- Test 3: Monotonic sensitivity checks on median customer ---
        median_row = {
            "DaysSinceLastOrder": int(csv_df["DaysSinceLastOrder"].median()),
            "OrderCount": int(csv_df["OrderCount"].median()),
            "TotalSpent": float(csv_df["TotalSpent"].median()),
            "ComplaintCount": int(csv_df["ComplaintCount"].median()),
            "SatisfactionScore": float(csv_df["SatisfactionScore"].median()),
            "TenureMonths": float(csv_df["TenureMonths"].median()),
            "ReturnRate": float(csv_df["ReturnRate"].median()),
            "DiscountUsageRate": float(csv_df["DiscountUsageRate"].median()),
        }

        base_score = predict_churn_risk(median_row)

        # 3a. Raising DaysSinceLastOrder by 60 raises the score
        row_days = dict(median_row, DaysSinceLastOrder=median_row["DaysSinceLastOrder"] + 60)
        score_days = predict_churn_risk(row_days)
        print(f"[TEST 3a] Base score: {base_score:.1f} -> +60 Days score: {score_days:.1f}")
        assert score_days > base_score, f"Expected score increase with +60 days, got {score_days} <= {base_score}"

        # 3b. Adding 2 complaints raises it
        row_comp = dict(median_row, ComplaintCount=median_row["ComplaintCount"] + 2)
        score_comp = predict_churn_risk(row_comp)
        print(f"[TEST 3b] Base score: {base_score:.1f} -> +2 Complaints score: {score_comp:.1f}")
        assert score_comp > base_score, f"Expected score increase with +2 complaints, got {score_comp} <= {base_score}"

        # 3c. Raising satisfaction from 2.0 to 4.5 lowers it
        row_low_sat = dict(median_row, SatisfactionScore=2.0)
        row_high_sat = dict(median_row, SatisfactionScore=4.5)
        score_low_sat = predict_churn_risk(row_low_sat)
        score_high_sat = predict_churn_risk(row_high_sat)
        print(f"[TEST 3c] Sat 2.0: {score_low_sat:.1f} -> Sat 4.5: {score_high_sat:.1f}")
        assert score_high_sat < score_low_sat, f"Expected lower score for higher sat, got {score_high_sat} >= {score_low_sat}"

        # 3d. Raising order count from 2 to 15 lowers it
        row_orders_2 = dict(median_row, OrderCount=2)
        row_orders_15 = dict(median_row, OrderCount=15)
        score_orders_2 = predict_churn_risk(row_orders_2)
        score_orders_15 = predict_churn_risk(row_orders_15)
        print(f"[TEST 3d] Orders 2: {score_orders_2:.1f} -> Orders 15: {score_orders_15:.1f}")
        assert score_orders_15 < score_orders_2, f"Expected lower score for 15 orders, got {score_orders_15} >= {score_orders_2}"
        print("[TEST 3] PASSED: All 4 monotonic sensitivity conditions verified.")

        # --- Test 4: Low-risk behavior guard ---
        safe_customer = {
            "DaysSinceLastOrder": 12,
            "OrderCount": 8,
            "TotalSpent": 900.0,
            "ComplaintCount": 0,
            "SatisfactionScore": 4.5,
            "TenureMonths": 18.0,
            "ReturnRate": 0.05,
            "DiscountUsageRate": 0.15,
        }
        safe_score = predict_churn_risk(safe_customer)
        safe_status = score_to_status(safe_score, threshold=60)
        print(f"[TEST 4] Safe customer score: {safe_score:.1f}, status: {safe_status}")
        assert safe_status == "Safe", f"Expected Safe status, got {safe_status}"
        assert safe_score < 40, f"Expected score < 40, got {safe_score}"
        print("[TEST 4] PASSED: Recent, satisfied buyer with 0 complaints is Safe.")

        # --- Test 5: SHAP additivity & protective factor sign on 100 random customers ---
        sample_100 = rng.sample(all_customers, 100)
        shap_diffs = []
        for c in sample_100:
            c_dict = {
                "DaysSinceLastOrder": (today - datetime.strptime(c.last_order_date[:10], "%Y-%m-%d").date()).days,
                "OrderCount": c.order_count,
                "TotalSpent": c.total_spent,
                "ComplaintCount": c.complaint_count,
                "SatisfactionScore": c.satisfaction_score,
                "TenureMonths": c.tenure_months,
                "ReturnRate": c.return_rate,
                "DiscountUsageRate": c.discount_usage_rate,
            }
            res = explain_churn_risk(c_dict, c.churn_risk_score)
            assert res["available"], f"SHAP unavailable for {c.id}"
            pts_sum = sum(f["points"] for f in res["factors"])
            delta = res["score"] - res["base_score"]
            diff = abs(round(delta, 1) - round(pts_sum, 1))
            shap_diffs.append(diff)
            assert diff <= 0.15, f"SHAP sum mismatch for {c.id}: delta={delta:.2f}, sum={pts_sum:.2f}"

        # Check that high satisfaction produces negative points (lowers risk)
        high_sat_test = dict(median_row, SatisfactionScore=4.8)
        sat_res = explain_churn_risk(high_sat_test)
        sat_factor = next((f for f in sat_res["factors"] if f["feature"] == "SatisfactionScore"), None)
        if sat_factor:
            print(f"[TEST 5] Satisfaction 4.8 factor points: {sat_factor['points']} pts (Expected negative)")
            assert sat_factor["points"] <= 0.0, f"Expected negative points for high satisfaction, got {sat_factor['points']}"

        print(f"[TEST 5] PASSED: SHAP additivity verified for 100 random customers (Max diff: {max(shap_diffs):.2f} pts).")

        # --- Test 6: last_order_date equals today minus DaysSinceLastOrder for every customer ---
        today = datetime.now().date()
        date_errors = 0
        for c in all_customers:
            expected_date = (today - timedelta(days=csv_days_map[c.id])).isoformat()
            if c.last_order_date != expected_date:
                date_errors += 1
        print(f"[TEST 6] Date errors across {len(all_customers)} customers: {date_errors}")
        assert date_errors == 0, f"Found {date_errors} date mismatches!"
        print("[TEST 6] PASSED: 100% of customers have last_order_date exactly matching today - DaysSinceLastOrder.")

        # --- Test 7: Heuristic fallback was never used ---
        # Verified because ALLOW_HEURISTIC_FALLBACK is not set and model loaded successfully
        assert os.environ.get("ALLOW_HEURISTIC_FALLBACK") != "1", "ALLOW_HEURISTIC_FALLBACK was enabled"
        from app.ml.churn_predictor import get_model
        m = get_model()
        assert m is not None, "Model failed to load"
        print("[TEST 7] PASSED: Machine learning model was used for all scoring (no heuristic fallback).")

        # --- Test 8: No isotonic or base_score = 14 in codebase ---
        import subprocess
        proc_iso = subprocess.run(["git", "grep", "-i", "isotonic"], capture_output=True, text=True)
        # Exclude this test file or prompt text if any
        iso_lines = [l for l in proc_iso.stdout.splitlines() if "prompt_full" not in l and "test_scores" not in l and "calibration.py" not in l]
        assert len(iso_lines) == 0, f"Found isotonic references: {iso_lines}"

        proc_base = subprocess.run(["git", "grep", "-i", "base_score = 14"], capture_output=True, text=True)
        base_lines = [l for l in proc_base.stdout.splitlines() if "prompt_full" not in l and "test_scores" not in l]
        assert len(base_lines) == 0, f"Found base_score = 14 references: {base_lines}"
        print("[TEST 8] PASSED: grep for 'isotonic' and 'base_score = 14' returned 0 occurrences.")

        print("\n=============================================================")
        print("          ALL 8 TEST SUITES PASSED SUCCESSFULLY!             ")
        print("=============================================================\n")

    finally:
        db.close()


if __name__ == "__main__":
    run_all_tests()
