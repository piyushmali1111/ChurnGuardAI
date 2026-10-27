import os
import joblib
import pandas as pd
import numpy as np
import shap
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from imblearn.over_sampling import SMOTE
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from generate_synthetic_data import generate_data

def train_and_evaluate():
    print("=========================================================")
    print("         ChurnGuardAI — Churn Model Training & EDA           ")
    print("=========================================================")

    data_dir = "data"
    models_dir = "models"
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(models_dir, exist_ok=True)

    csv_path = os.path.join(data_dir, "ecommerce_churn.csv")
    if not os.path.exists(csv_path):
        generate_data()

    df = pd.read_csv(csv_path)
    print(f"[+] Loaded {len(df)} rows from {csv_path}")

    feature_cols = [
        "DaysSinceLastOrder",
        "OrderCount",
        "TotalSpent",
        "ComplaintCount",
        "SatisfactionScore",
    ]
    target_col = "Churn"

    X = df[feature_cols]
    y = df[target_col]

    print(f"[*] Class imbalance: {y.value_counts(normalize=True).to_dict()}")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Apply SMOTE on training set only
    print("[*] Applying SMOTE on training set...")
    smote = SMOTE(random_state=42)
    X_train_res, y_train_res = smote.fit_resample(X_train, y_train)

    models = {
        "Logistic Regression": LogisticRegression(max_iter=1000, random_state=42),
        "Random Forest": RandomForestClassifier(n_estimators=100, random_state=42),
        "XGBoost": XGBClassifier(n_estimators=100, max_depth=4, learning_rate=0.05, random_state=42, eval_metric="logloss"),
    }

    results = []

    for name, model in models.items():
        model.fit(X_train_res, y_train_res)
        y_pred = model.predict(X_test)
        y_proba = model.predict_proba(X_test)[:, 1]

        acc = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred, zero_division=0)
        rec = recall_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred)
        auc = roc_auc_score(y_test, y_proba)

        results.append({
            "Model": name,
            "Accuracy": acc,
            "Precision": prec,
            "Recall": rec,
            "F1-Score": f1,
            "ROC-AUC": auc,
            "instance": model,
        })

    results_df = pd.DataFrame(results)
    print("\n--- Model Evaluation Comparison ---")
    print(results_df[["Model", "Accuracy", "Precision", "Recall", "F1-Score", "ROC-AUC"]].to_string(index=False))

    # Select best model by ROC-AUC
    best = results_df.sort_values(by="ROC-AUC", ascending=False).iloc[0]
    best_name = best["Model"]
    best_model = best["instance"]

    print(f"\n[+] Winning Model Selected: {best_name} (ROC-AUC: {best['ROC-AUC']:.4f})")

    model_path = os.path.join(models_dir, "churn_model.pkl")
    joblib.dump(best_model, model_path)
    print(f"[+] Saved model artifact to {model_path}")

    # Fit & save SHAP Explainer
    print("[*] Fitting SHAP Explainer on winning model...")
    explainer = shap.Explainer(best_model, X_train_res)
    explainer_path = os.path.join(models_dir, "shap_explainer.pkl")
    joblib.dump(explainer, explainer_path)
    print(f"[+] Saved SHAP explainer artifact to {explainer_path}")
    print("=========================================================\n")

if __name__ == "__main__":
    train_and_evaluate()
