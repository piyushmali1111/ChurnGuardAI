import os
import logging
import joblib
import pandas as pd
import numpy as np
from typing import Dict, Any, Union

from app.ml.features import FEATURE_COLS

logger = logging.getLogger(__name__)

MODEL_PATH = os.path.join(os.path.dirname(__file__), "../../models/churn_model.pkl")

_model = None


def get_model():
    global _model
    if _model is None:
        if os.path.exists(MODEL_PATH):
            try:
                _model = joblib.load(MODEL_PATH)
            except Exception as e:
                logger.error(f"Failed to load model from {MODEL_PATH}: {e}")
                if os.environ.get("ALLOW_HEURISTIC_FALLBACK") == "1":
                    return None
                raise RuntimeError(f"Could not load churn model from {MODEL_PATH}: {e}")
        else:
            if os.environ.get("ALLOW_HEURISTIC_FALLBACK") == "1":
                return None
            raise FileNotFoundError(f"Model file not found at {MODEL_PATH}. Run train_churn_model.py first.")
    return _model


def score_to_status(score: float, threshold: int = 60) -> str:
    """
    Categorizes churn risk score into Safe, Watching, or High Risk.
    High Risk at or above the threshold.
    Watching from threshold - 20 (e.g. 40 to 59).
    Otherwise Safe (< 40).
    """
    if score >= threshold:
        return "High Risk"
    elif score >= (threshold - 20):
        return "Watching"
    return "Safe"


def predict_churn_risk(customer_data: Dict[str, Any]) -> float:
    """
    Accepts customer features dict with keys from FEATURE_COLS:
    DaysSinceLastOrder, OrderCount, TotalSpent, ComplaintCount,
    SatisfactionScore, TenureMonths, ReturnRate, DiscountUsageRate.

    Returns a float churn risk score rounded to 1 decimal place (1.0 to 99.0).
    """
    model = get_model()

    if model is None:
        if os.environ.get("ALLOW_HEURISTIC_FALLBACK") == "1":
            logger.error("Using HEURISTIC fallback for customer churn prediction! Model artifact unavailable.")
            days = customer_data.get("DaysSinceLastOrder", 30)
            complaints = customer_data.get("ComplaintCount", 0)
            sat = customer_data.get("SatisfactionScore", 3.5)
            raw = 20.0 + 0.5 * days + 12.0 * complaints - 10.0 * (sat - 3.0)
            clamped = max(1.0, min(99.0, raw))
            return round(clamped, 1)
        raise RuntimeError("Churn model is not available and heuristic fallback is disabled.")

    row = {col: customer_data.get(col, 0.0) for col in FEATURE_COLS}
    df = pd.DataFrame([row])[FEATURE_COLS]

    if hasattr(model, "predict_proba"):
        proba = float(model.predict_proba(df)[0][1])
    else:
        proba = float(model.predict(df)[0])

    raw_score = proba * 100.0

    if raw_score < 1.0:
        logger.warning(f"Churn score {raw_score:.2f} clamped to 1.0 safety floor.")
        score = 1.0
    elif raw_score > 99.0:
        logger.warning(f"Churn score {raw_score:.2f} clamped to 99.0 safety ceiling.")
        score = 99.0
    else:
        score = raw_score

    return round(score, 1)


def predict_churn_risk_batch(df: pd.DataFrame) -> np.ndarray:
    """
    Scores multiple customers in one vectorized call (for proactive scan).
    Accepts DataFrame with FEATURE_COLS and returns numpy array of floats rounded to 1 decimal.
    """
    model = get_model()
    if model is None:
        if os.environ.get("ALLOW_HEURISTIC_FALLBACK") == "1":
            logger.error("Batch heuristic fallback used.")
            return np.array([predict_churn_risk(row) for row in df.to_dict(orient="records")])
        raise RuntimeError("Churn model is not available and heuristic fallback is disabled.")

    X = df[FEATURE_COLS]
    if hasattr(model, "predict_proba"):
        probas = model.predict_proba(X)[:, 1]
    else:
        probas = model.predict(X)

    raw_scores = probas * 100.0
    under_floor = raw_scores < 1.0
    over_ceiling = raw_scores > 99.0
    if np.any(under_floor):
        logger.warning(f"{np.sum(under_floor)} scores clamped to 1.0 in batch prediction.")
    if np.any(over_ceiling):
        logger.warning(f"{np.sum(over_ceiling)} scores clamped to 99.0 in batch prediction.")

    clamped = np.clip(raw_scores, 1.0, 99.0)
    return np.round(clamped, 1)
