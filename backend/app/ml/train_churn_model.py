import os
import sys
import json
import joblib
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sklearn.model_selection import train_test_split, StratifiedKFold
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    average_precision_score,
    brier_score_loss,
)
from sklearn.calibration import calibration_curve
from imblearn.over_sampling import SMOTE
from xgboost import XGBClassifier

# Ensure backend root is in sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.ml.features import FEATURE_COLS, MONOTONE
from app.ml.calibration import PlattCalibratedModel
from app.config import settings as app_settings


def fit_calibrated(X_tr, y_tr, random_state: int = 42) -> PlattCalibratedModel:
    """
    Fits XGBoost with monotonic constraints and Platt calibration:
    - Inner 75/25 split (giving 60% inner train / 20% inner val of original data)
    - SMOTE on inner train
    - XGBoost early stopping on inner validation
    - Platt calibration on inner validation (real class ratio)
    """
    X_in_tr, X_in_val, y_in_tr, y_in_val = train_test_split(
        X_tr, y_tr, test_size=0.25, random_state=random_state, stratify=y_tr
    )

    smote = SMOTE(random_state=random_state)
    X_res, y_res = smote.fit_resample(X_in_tr, y_in_tr)

    xgb = XGBClassifier(
        max_depth=3,
        learning_rate=0.05,
        n_estimators=600,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=5,
        reg_lambda=5,
        monotone_constraints=MONOTONE,
        early_stopping_rounds=30,
        random_state=random_state,
        eval_metric="logloss",
    )
    xgb.fit(X_res, y_res, eval_set=[(X_in_val, y_in_val)], verbose=False)
    return PlattCalibratedModel(xgb, X_in_val, y_in_val)


def train_and_evaluate():
    print("=========================================================")
    print("      ChurnGuardAI — Calibrated Churn Model Training     ")
    print("=========================================================")

    data_dir = os.path.join(backend_dir, "data")
    models_dir = os.path.join(backend_dir, "models")
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(models_dir, exist_ok=True)

    csv_path = os.path.join(data_dir, "ecommerce_churn.csv")
    if not os.path.exists(csv_path):
        from generate_synthetic_data import generate_synthetic_data
        generate_synthetic_data(force=True, check=True)

    df = pd.read_csv(csv_path)
    print(f"[+] Loaded {len(df)} rows from {csv_path}")

    X = df[FEATURE_COLS]
    y = df["Churn"]
    real_churn_rate = float(y.mean())
    print(f"[*] Overall churn rate: {real_churn_rate * 100:.2f}%")

    # 1. Stratified 60% train / 20% validation / 20% test split
    X_train_val, X_test, y_train_val, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )
    X_train, X_val, y_train, y_val = train_test_split(
        X_train_val, y_train_val, test_size=0.25, random_state=42, stratify=y_train_val
    )

    print(f"[*] Split sizes: Train={len(X_train)} (60%), Val={len(X_val)} (20%), Test={len(X_test)} (20%)")

    # 2. SMOTE on training split only
    smote = SMOTE(random_state=42)
    X_train_res, y_train_res = smote.fit_resample(X_train, y_train)

    # 3. Fit candidate models & calibrate on validation set
    threshold_prob = app_settings.RISK_THRESHOLD / 100.0  # e.g. 0.60

    # Model 1: Logistic Regression
    lr = LogisticRegression(max_iter=1000, random_state=42)
    lr.fit(X_train_res, y_train_res)
    calib_lr = PlattCalibratedModel(lr, X_val, y_val)

    # Model 2: Random Forest
    rf = RandomForestClassifier(max_depth=8, min_samples_leaf=20, n_estimators=100, random_state=42)
    rf.fit(X_train_res, y_train_res)
    calib_rf = PlattCalibratedModel(rf, X_val, y_val)

    # Model 3: XGBoost (fitted on train, early stopped & calibrated on val)
    xgb = XGBClassifier(
        max_depth=3,
        learning_rate=0.05,
        n_estimators=600,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=5,
        reg_lambda=5,
        monotone_constraints=MONOTONE,
        early_stopping_rounds=30,
        random_state=42,
        eval_metric="logloss",
    )
    xgb.fit(X_train_res, y_train_res, eval_set=[(X_val, y_val)], verbose=False)
    calib_xgb = PlattCalibratedModel(xgb, X_val, y_val)

    candidates = {
        "Logistic Regression": calib_lr,
        "Random Forest": calib_rf,
        "XGBoost": calib_xgb,
    }

    metrics_report = {}
    print("\n--- Model Evaluation Comparison (Test Set @ threshold = {:.2f}) ---".format(threshold_prob))
    print(f"{'Model':<22} {'Val AUC':<9} {'Test AUC':<9} {'PR-AUC':<8} {'Brier':<8} {'Acc':<7} {'Prec':<7} {'Rec':<7} {'F1':<7}")

    for name, model in candidates.items():
        val_probs = model.predict_proba(X_val)[:, 1]
        val_auc = roc_auc_score(y_val, val_probs)

        test_probs = model.predict_proba(X_test)[:, 1]
        test_auc = roc_auc_score(y_test, test_probs)
        pr_auc = average_precision_score(y_test, test_probs)
        brier = brier_score_loss(y_test, test_probs)

        y_pred = (test_probs >= threshold_prob).astype(int)
        acc = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred, zero_division=0)
        rec = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)

        metrics_report[name] = {
            "Val_ROC_AUC": round(float(val_auc), 4),
            "Test_ROC_AUC": round(float(test_auc), 4),
            "PR_AUC": round(float(pr_auc), 4),
            "Brier_Score": round(float(brier), 4),
            "Accuracy": round(float(acc), 4),
            "Precision": round(float(prec), 4),
            "Recall": round(float(rec), 4),
            "F1_Score": round(float(f1), 4),
            "Mean_Calibrated_Score": round(float(test_probs.mean() * 100), 2),
        }

        print(f"{name:<22} {val_auc:<9.4f} {test_auc:<9.4f} {pr_auc:<8.4f} {brier:<8.4f} {acc:<7.4f} {prec:<7.4f} {rec:<7.4f} {f1:<7.4f}")

    # Production model is XGBoost (paper's model)
    prod_model = calib_xgb
    xgb_test_probs = prod_model.predict_proba(X_test)[:, 1]
    xgb_test_auc = roc_auc_score(y_test, xgb_test_probs)
    xgb_mean_score = xgb_test_probs.mean() * 100.0
    test_churn_rate = y_test.mean() * 100.0
    score_diff = abs(xgb_mean_score - test_churn_rate)

    print(f"\n[+] Production Model: XGBoost (Calibrated)")
    print(f"    - Test ROC-AUC: {xgb_test_auc:.4f}")
    print(f"    - Test Mean Calibrated Score: {xgb_mean_score:.2f}% vs Real Churn Rate: {test_churn_rate:.2f}% (Diff: {score_diff:.2f} pts)")

    # 6. Save model artifact
    model_path = os.path.join(models_dir, "churn_model.pkl")
    joblib.dump(prod_model, model_path)
    print(f"[+] Saved calibrated XGBoost model to {model_path}")

    # Save metrics.json
    metrics_path = os.path.join(models_dir, "metrics.json")
    with open(metrics_path, "w") as f:
        json.dump(metrics_report, f, indent=2)
    print(f"[+] Saved metrics comparison table to {metrics_path}")

    # Save calibration diagram
    calib_plot_path = os.path.join(models_dir, "calibration.png")
    prob_true, prob_pred = calibration_curve(y_test, xgb_test_probs, n_bins=10)
    plt.figure(figsize=(7, 6))
    plt.plot(prob_pred, prob_true, marker="o", linewidth=2, label="Calibrated XGBoost")
    plt.plot([0, 1], [0, 1], linestyle="--", color="gray", label="Perfect Calibration")
    plt.xlabel("Mean Predicted Probability")
    plt.ylabel("Fraction of Positives")
    plt.title("Reliability Diagram (Test Set)")
    plt.legend()
    plt.tight_layout()
    plt.savefig(calib_plot_path)
    plt.close()
    print(f"[+] Saved reliability diagram to {calib_plot_path}")

    # Save shap_background.csv (200 real training rows)
    shap_bg_path = os.path.join(models_dir, "shap_background.csv")
    shap_bg = X_train.sample(n=200, random_state=42)
    shap_bg.to_csv(shap_bg_path, index=False)
    print(f"[+] Saved 200 real training rows for SHAP background to {shap_bg_path}")

    # 8. Out-of-fold scores using 5-fold cross-fitting
    print("[*] Generating 5-fold out-of-fold scores for all seeded customers...")
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    oof_probs = np.zeros(len(df))

    for fold, (train_idx, val_idx) in enumerate(skf.split(X, y)):
        fold_model = fit_calibrated(X.iloc[train_idx], y.iloc[train_idx], random_state=42 + fold)
        oof_probs[val_idx] = fold_model.predict_proba(X.iloc[val_idx])[:, 1]

    oof_scores = np.round(oof_probs * 100.0, 1)
    oof_scores = np.clip(oof_scores, 1.0, 99.0)

    oof_path = os.path.join(models_dir, "oof_scores.csv")
    oof_df = pd.DataFrame({
        "CustomerID": df["CustomerID"],
        "score": oof_scores
    })
    oof_df.to_csv(oof_path, index=False)
    print(f"[+] Saved out-of-fold scores for {len(oof_df)} customers to {oof_path}")

    # 9. Acceptance checks
    print("\n==================== Acceptance Criteria ====================")
    auc_ok = 0.78 <= xgb_test_auc <= 0.90
    mean_ok = score_diff <= 3.0
    print(f"1. XGBoost Test AUC in [0.78, 0.90]: {xgb_test_auc:.4f} -> {'PASS' if auc_ok else 'FAIL'}")
    print(f"2. Mean Score vs Real Churn <= 3.0 pts: {score_diff:.2f} pts -> {'PASS' if mean_ok else 'FAIL'}")
    print("=============================================================\n")

    assert auc_ok, f"XGBoost Test AUC {xgb_test_auc:.4f} not in [0.78, 0.90]"
    assert mean_ok, f"Score difference {score_diff:.2f} points exceeds 3.0"


if __name__ == "__main__":
    train_and_evaluate()
