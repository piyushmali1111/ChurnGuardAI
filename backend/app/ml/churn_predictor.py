import os
import joblib
import pandas as pd

MODEL_PATH = os.path.join(os.path.dirname(__file__), "../../models/churn_model.pkl")

_model = None

def get_model():
    global _model
    if _model is None:
        if os.path.exists(MODEL_PATH):
            _model = joblib.load(MODEL_PATH)
        else:
            raise FileNotFoundError(f"Model file not found at {MODEL_PATH}. Run train_churn_model.py first.")
    return _model

def predict_churn_risk(customer_data: dict) -> int:
    """
    Accepts customer features dict with keys:
    DaysSinceLastOrder, OrderCount, TotalSpent, ComplaintCount, SatisfactionScore
    Returns an integer churn risk score clamped between 2 and 98.
    """
    try:
        model = get_model()
    except Exception:
        # Fallback heuristic calculation if model artifact is missing
        days = customer_data.get("DaysSinceLastOrder", 30)
        complaints = customer_data.get("ComplaintCount", 0)
        sat = customer_data.get("SatisfactionScore", 3.5)
        raw = int(round(20 + 0.5 * days + 12 * complaints - 10 * (sat - 3.0)))
        return max(2, min(98, raw))

    feature_cols = [
        "DaysSinceLastOrder",
        "OrderCount",
        "TotalSpent",
        "ComplaintCount",
        "SatisfactionScore",
    ]

    df = pd.DataFrame([customer_data])[feature_cols]

    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(df)[0][1]
    else:
        proba = float(model.predict(df)[0])

    risk_score = int(round(proba * 100))
    # Section 3 & Check 6: Clamp displayed scores to the range 2-98
    return max(2, min(98, risk_score))
