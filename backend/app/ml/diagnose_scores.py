import os
import sys
import random
import re
from collections import Counter
from datetime import datetime, timedelta

# Ensure backend path is in sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.db.session import SessionLocal
from app.db.models import Customer
import app.ml.churn_predictor as cp

def run_diagnostics():
    print("=" * 60)
    print("STEP 0 DIAGNOSTICS: Churn Score Diagnosis")
    print("=" * 60)

    db = SessionLocal()
    customers = db.query(Customer).all()
    print(f"\n[1] Total customers in DB: {len(customers)}")

    # 1. Number of distinct churn_risk_score values in DB & 10 most frequent values with counts
    scores = [c.churn_risk_score for c in customers]
    score_counts = Counter(scores)
    print(f"Number of distinct churn_risk_score values in DB: {len(score_counts)}")
    print("10 most frequent churn_risk_score values with counts:")
    for score, count in score_counts.most_common(10):
        pct = (count / len(customers)) * 100
        print(f"  Score {score:2d}: {count:5d} customers ({pct:5.2f}%)")

    # 2. Find exact function and line that writes churn_risk_score and last_order_date in seed_data.py
    seed_file = os.path.join(backend_dir, "app", "db", "seed_data.py")
    print(f"\n[2] Lines writing churn_risk_score and last_order_date in {seed_file}:")
    with open(seed_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
        for idx, line in enumerate(lines, 1):
            if "churn_risk_score=" in line or "last_order_date=" in line:
                print(f"  Line {idx:3d}: {line.strip()}")

    # 3. Take 20 random customers: compare DB score and predict_churn_risk(features)
    print("\n[3] Comparing 20 random customers (DB score vs predict_churn_risk):")
    # Instrument heuristic fallback counter
    original_predict = cp.predict_churn_risk
    heuristic_hits = [0]
    model_hits = [0]

    def instrumented_predict(customer_data):
        try:
            model = cp.get_model()
            model_hits[0] += 1
        except Exception:
            heuristic_hits[0] += 1
        return original_predict(customer_data)

    cp.predict_churn_risk = instrumented_predict

    today = datetime.utcnow().date()
    sample_customers = random.sample(customers, min(20, len(customers)))
    diff_count = 0
    for c in sample_customers:
        # compute days since last order from last_order_date
        ord_date = datetime.fromisoformat(c.last_order_date).date()
        days_since = (today - ord_date).days
        feat = {
            "DaysSinceLastOrder": days_since,
            "OrderCount": c.order_count,
            "TotalSpent": c.total_spent,
            "ComplaintCount": c.complaint_count,
            "SatisfactionScore": c.satisfaction_score,
        }
        recomputed_score = cp.predict_churn_risk(feat)
        diff = recomputed_score - c.churn_risk_score
        if diff != 0:
            diff_count += 1
        print(f"  Cust {c.id} ({c.name:20s}): DB score={c.churn_risk_score:2d}, Recomputed={recomputed_score:2d}, Diff={diff:+3d}, DaysSince={days_since:3d}, Sat={c.satisfaction_score:.1f}, Orders={c.order_count:2d}")

    print(f"Differences in sample of 20: {diff_count}/20")

    # 4. Grep seed_data.py, routes, services for score or status set from constant, bucket, label, random.choice
    print("\n[4] Scanning seed_data.py, routes, services for constants, buckets, labels, random.choice setting scores/status:")
    search_dirs = [
        os.path.join(backend_dir, "app", "db"),
        os.path.join(backend_dir, "app", "api", "routes"),
        os.path.join(backend_dir, "app", "services"),
    ]
    patterns = [
        r"churn_risk_score\s*=\s*",
        r"score\s*=\s*random\.",
        r"churn_status\s*=\s*",
        r"random\.choice",
    ]
    for s_dir in search_dirs:
        for root, _, files in os.walk(s_dir):
            for file in files:
                if file.endswith(".py"):
                    f_path = os.path.join(root, file)
                    rel_path = os.path.relpath(f_path, backend_dir)
                    with open(f_path, "r", encoding="utf-8") as pf:
                        for l_idx, pline in enumerate(pf, 1):
                            for pat in patterns:
                                if re.search(pat, pline) and not pline.strip().startswith("#"):
                                    print(f"  {rel_path}:{l_idx}: {pline.strip()}")

    # 5. Count how many calls to predict_churn_risk hit the heuristic fallback
    print(f"\n[5] Fallback check during 20 calls:")
    print(f"  Model calls: {model_hits[0]}, Heuristic fallback hits: {heuristic_hits[0]}")
    # Also test with full dataset from CSV if available
    csv_path = os.path.join(backend_dir, "data", "ecommerce_churn.csv")
    if os.path.exists(csv_path):
        import pandas as pd
        csv_df = pd.read_csv(csv_path)
        print(f"\n[6] Checking CSV {csv_path} ({len(csv_df)} rows):")
        print(f"  Columns: {list(csv_df.columns)}")
        # Check if CSV has last_order_date
        has_dates = "LastOrderDate" in csv_df.columns or "last_order_date" in csv_df.columns
        print(f"  Does CSV currently contain date columns? {has_dates}")
    else:
        print(f"\n[6] CSV {csv_path} does not exist yet.")

    db.close()
    print("\n" + "=" * 60)
    print("DIAGNOSTICS COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    run_diagnostics()
