import os
import random
import pandas as pd
import numpy as np

def generate_data():
    os.makedirs("data", exist_ok=True)
    csv_path = "data/ecommerce_churn.csv"

    if os.path.exists(csv_path):
        print(f"[+] Dataset already exists at {csv_path}")
        return

    print("[*] Generating 5,000 synthetic e-commerce customer churn dataset...")
    np.random.seed(42)
    random.seed(42)

    n_samples = 5000

    days_since_last_order = np.random.exponential(scale=25, size=n_samples).astype(int)
    order_count = np.random.poisson(lam=8, size=n_samples) + 1
    total_spent = (order_count * np.random.uniform(45, 180, size=n_samples)).round(2)
    complaint_count = np.random.binomial(n=5, p=0.15, size=n_samples)
    satisfaction_score = np.clip(np.random.normal(loc=3.8 - (complaint_count * 0.4), scale=0.8), 1.0, 5.0).round(1)

    # Churn logic probability based on features
    churn_logit = (
        -2.5 
        + 0.045 * days_since_last_order 
        + 0.65 * complaint_count 
        - 0.55 * (satisfaction_score - 3.0) 
        - 0.08 * order_count
    )
    churn_prob = 1 / (1 + np.exp(-churn_logit))
    churn_label = (np.random.rand(n_samples) < churn_prob).astype(int)

    df = pd.DataFrame({
        "CustomerID": [f"CUST-{1000 + i}" for i in range(n_samples)],
        "DaysSinceLastOrder": days_since_last_order,
        "OrderCount": order_count,
        "TotalSpent": total_spent,
        "ComplaintCount": complaint_count,
        "SatisfactionScore": satisfaction_score,
        "Churn": churn_label
    })

    df.to_csv(csv_path, index=False)
    print(f"[+] Successfully generated {n_samples} rows to {csv_path}. Churn Rate: {df['Churn'].mean()*100:.1f}%")

if __name__ == "__main__":
    generate_data()
