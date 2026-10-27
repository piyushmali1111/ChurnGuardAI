import os
import argparse
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split

def generate_synthetic_data(n_samples: int = 4850, force: bool = False, check: bool = False, churn_rate_target: float = 0.23):
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(data_dir, exist_ok=True)
    csv_path = os.path.join(data_dir, "ecommerce_churn.csv")

    if os.path.exists(csv_path) and not force:
        print(f"[+] Dataset already exists at {csv_path}. (Use --force to regenerate)")
        if check:
            run_check(csv_path)
        return csv_path

    print(f"[*] Generating {n_samples} synthetic e-commerce customer records with 8 features and relative dates...")
    np.random.seed(42)

    today = datetime.now().date()

    # Base random distributions
    days = np.random.exponential(scale=28, size=n_samples).astype(int)
    days = np.clip(days, 1, 365)

    orders = np.random.poisson(lam=7, size=n_samples) + 1
    spent = np.round(orders * np.random.uniform(40, 160, size=n_samples), 2)
    complaints = np.random.binomial(n=4, p=0.15, size=n_samples)
    sat = np.clip(np.random.normal(loc=3.9 - 0.35 * complaints, scale=0.75), 1.0, 5.0).round(1)

    tenure_prior = np.random.exponential(scale=180, size=n_samples).astype(int) + 15
    tenure_days = days + tenure_prior
    tenure_months = np.round(tenure_days / 30.4, 1)

    return_rate = np.clip(np.random.beta(a=2, b=15, size=n_samples) + 0.05 * complaints, 0.0, 0.8).round(3)
    discount_usage = np.clip(np.random.beta(a=2, b=4, size=n_samples), 0.0, 1.0).round(2)

    # Inject realistic features for the 6 named demo customers at indices 0-5
    # Row 0: Lucas Vance (High Risk, order 24 days ago, 4 complaints, low satisfaction)
    days[0] = 24
    orders[0] = 2
    spent[0] = 210.0
    complaints[0] = 4
    sat[0] = 1.0
    tenure_days[0] = 310
    tenure_months[0] = round(310 / 30.4, 1)
    return_rate[0] = 0.40
    discount_usage[0] = 0.60

    # Row 1: Elena Rostova (High Risk, order 26 days ago, delayed delivery story, 3 complaints)
    days[1] = 26
    orders[1] = 3
    spent[1] = 320.0
    complaints[1] = 3
    sat[1] = 1.5
    tenure_days[1] = 260
    tenure_months[1] = round(260 / 30.4, 1)
    return_rate[1] = 0.28
    discount_usage[1] = 0.45

    # Row 2: Sophia Chen (High Risk, 65 days inactive, low satisfaction)
    days[2] = 65
    orders[2] = 4
    spent[2] = 350.0
    complaints[2] = 2
    sat[2] = 2.3
    tenure_days[2] = 550
    tenure_months[2] = round(550 / 30.4, 1)
    return_rate[2] = 0.15
    discount_usage[2] = 0.30

    # Row 3: Devon Miller (Watching band 40-59, moderate recency & satisfaction)
    days[3] = 35
    orders[3] = 6
    spent[3] = 600.0
    complaints[3] = 1
    sat[3] = 3.2
    tenure_days[3] = 365
    tenure_months[3] = round(365 / 30.4, 1)
    return_rate[3] = 0.10
    discount_usage[3] = 0.25

    # Row 4: Marcus Sterling (Safe band, frequent buyer, 0 complaints, high satisfaction)
    days[4] = 12
    orders[4] = 8
    spent[4] = 950.0
    complaints[4] = 0
    sat[4] = 4.1
    tenure_days[4] = 600
    tenure_months[4] = round(600 / 30.4, 1)
    return_rate[4] = 0.05
    discount_usage[4] = 0.15

    # Row 5: Amara Thorne (Safe band, high value, 0 complaints, exceptional satisfaction)
    days[5] = 6
    orders[5] = 10
    spent[5] = 1450.0
    complaints[5] = 0
    sat[5] = 4.8
    tenure_days[5] = 730
    tenure_months[5] = round(730 / 30.4, 1)
    return_rate[5] = 0.03
    discount_usage[5] = 0.10

    # Churn probability logit
    z = (
        -1.95
        + 0.035 * days
        - 0.040 * orders
        - 0.0002 * (spent - 800)
        + 0.55 * complaints
        - 0.45 * (sat - 3.0)
        - 0.010 * tenure_months
        + 1.30 * return_rate
        + 0.35 * discount_usage
    )
    noise = np.random.logistic(loc=0, scale=0.75, size=n_samples)
    p = 1.0 / (1.0 + np.exp(-(z + noise)))
    churn = (p > 0.5).astype(int)

    # Ensure ground truth churn label matches risk profiles for demo customers
    churn[0] = 1  # Lucas
    churn[1] = 1  # Elena
    churn[2] = 1  # Sophia
    churn[3] = 0  # Devon
    churn[4] = 0  # Marcus
    churn[5] = 0  # Amara

    last_order_dates = [(today - timedelta(days=int(d))).isoformat() for d in days]
    signup_dates = [(today - timedelta(days=int(td))).isoformat() for td in tenure_days]
    customer_ids = [f"CUST-{1000 + i}" for i in range(n_samples)]

    df = pd.DataFrame({
        "CustomerID": customer_ids,
        "SignupDate": signup_dates,
        "LastOrderDate": last_order_dates,
        "DaysSinceLastOrder": days,
        "OrderCount": orders,
        "TotalSpent": spent,
        "ComplaintCount": complaints,
        "SatisfactionScore": sat,
        "TenureMonths": tenure_months,
        "ReturnRate": return_rate,
        "DiscountUsageRate": discount_usage,
        "Churn": churn,
    })

    df.to_csv(csv_path, index=False)
    actual_churn_rate = df["Churn"].mean()
    print(f"[+] Successfully saved {n_samples} records to {csv_path}. Real Churn Rate: {actual_churn_rate * 100:.2f}%")

    if check:
        run_check(csv_path)

    return csv_path

def run_check(csv_path: str):
    df = pd.read_csv(csv_path)
    feature_cols = [
        "DaysSinceLastOrder", "OrderCount", "TotalSpent", "ComplaintCount",
        "SatisfactionScore", "TenureMonths", "ReturnRate", "DiscountUsageRate"
    ]
    X = df[feature_cols]
    y = df["Churn"]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    lr = LogisticRegression(max_iter=1000)
    lr.fit(X_train, y_train)
    probs = lr.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, probs)
    print(f"[CHECK] Logistic Regression AUC: {auc:.4f}")
    assert 0.78 <= auc <= 0.88, f"AUC {auc:.4f} is outside required range [0.78, 0.88]"
    print("[CHECK] PASSED: Logistic Regression AUC is between 0.78 and 0.88.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic customer churn data")
    parser.add_argument("--force", action="store_true", help="Force regeneration of data even if file exists")
    parser.add_argument("--check", action="store_true", help="Run logistic regression AUC check")
    parser.add_argument("--n-samples", type=int, default=4850, help="Number of customer samples to generate")
    parser.add_argument("--churn-rate", type=float, default=0.23, help="Target churn rate")

    args = parser.parse_args()
    generate_synthetic_data(n_samples=args.n_samples, force=args.force, check=args.check, churn_rate_target=args.churn_rate)
