import os
import logging
import shap
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional

from app.ml.features import FEATURE_COLS
from app.ml.churn_predictor import get_model

logger = logging.getLogger(__name__)

SHAP_BG_PATH = os.path.join(os.path.dirname(__file__), "../../models/shap_background.csv")

_explainer = None


def get_explainer():
    """
    Builds the SHAP TreeExplainer once at startup (cached) from the calibrated
    XGBoost base_model, using shap_background.csv as background data.
    Never loads a pickled explainer.
    """
    global _explainer
    if _explainer is None:
        try:
            model = get_model()
            if model is None or not hasattr(model, "base_model"):
                logger.error("Cannot build SHAP explainer: Calibrated model unavailable.")
                return None

            if not os.path.exists(SHAP_BG_PATH):
                logger.error(f"Cannot build SHAP explainer: Background data missing at {SHAP_BG_PATH}.")
                return None

            bg_df = pd.read_csv(SHAP_BG_PATH)[FEATURE_COLS]
            base_xgb = model.base_model
            if hasattr(base_xgb, "set_params"):
                base_xgb.set_params(enable_categorical=False)

            explainer = shap.TreeExplainer(base_xgb, data=bg_df)
            if hasattr(explainer, "model") and hasattr(explainer.model, "_xgb_enable_categorical"):
                explainer.model._xgb_enable_categorical = False

            _explainer = explainer
            logger.info("Successfully initialized SHAP TreeExplainer with real background dataset.")
        except Exception as e:
            logger.error(f"Failed to build SHAP TreeExplainer: {e}")
            _explainer = None
    return _explainer


FEATURE_LABELS = {
    "SatisfactionScore": "Satisfaction rating",
    "DaysSinceLastOrder": "Days since last order",
    "ComplaintCount": "Complaints count",
    "OrderCount": "Order history count",
    "TotalSpent": "Lifetime spend total",
    "TenureMonths": "Account tenure",
    "ReturnRate": "Return rate",
    "DiscountUsageRate": "Discount usage",
}


def format_feature_value(col: str, val: float) -> str:
    if col == "SatisfactionScore":
        return f"{val:.1f} / 5.0"
    elif col == "DaysSinceLastOrder":
        return f"{int(round(val))} days"
    elif col == "ComplaintCount":
        return f"{int(round(val))} complaints"
    elif col == "OrderCount":
        return f"{int(round(val))} orders"
    elif col == "TotalSpent":
        return f"${val:,.2f}"
    elif col == "TenureMonths":
        return f"{val:.1f} months"
    elif col == "ReturnRate":
        return f"{val * 100:.1f}%"
    elif col == "DiscountUsageRate":
        return f"{int(round(val * 100))}%"
    return str(val)


def explain_churn_risk(customer_data: Dict[str, Any], baseline_score: Optional[float] = None) -> Dict[str, Any]:
    """
    Step 6 SHAP Explainability:
    Builds explanation in margin/log-odds space using TreeExplainer, then rescales
    via Platt calibration:
      base_margin = explainer.expected_value
      phi         = SHAP values (log-odds), one per feature
      margin      = base_margin + sum(phi)
      base_score  = calibrate_margin(base_margin) * 100     # computed, never hardcoded
      score       = calibrate_margin(margin) * 100          # equals the customer's score
      points_j    = phi_j * (score - base_score) / sum(phi)

    Returns top 5 factors by absolute points, plus one 'Other factors' row
    holding the remainder so displayed points sum exactly to (score - base_score).
    """
    model = get_model()
    explainer = get_explainer()

    if model is None or explainer is None:
        logger.warning("SHAP explainer or model is unavailable.")
        return {
            "available": False,
            "factors": [],
            "base_score": 0.0,
            "score": baseline_score or 0.0,
        }

    # Prepare features
    row = {col: float(customer_data.get(col, 0.0)) for col in FEATURE_COLS}
    row_df = pd.DataFrame([row])[FEATURE_COLS]

    try:
        phi_raw = explainer.shap_values(row_df)
        if isinstance(phi_raw, list):
            phi = np.array(phi_raw[1][0] if len(phi_raw) > 1 else phi_raw[0][0], dtype=float)
        elif hasattr(phi_raw, "values"):
            phi = np.array(phi_raw.values[0], dtype=float)
        else:
            phi = np.array(phi_raw[0], dtype=float)

        ev = explainer.expected_value
        if isinstance(ev, (list, np.ndarray)):
            base_margin = float(ev[1] if len(ev) > 1 else ev[0])
        else:
            base_margin = float(ev)

        base_score = float(model.calibrate_margin(base_margin) * 100.0)
        sum_phi = float(np.sum(phi))
        margin = base_margin + sum_phi
        model_score = float(model.calibrate_margin(margin) * 100.0)
        score = float(baseline_score) if baseline_score is not None else model_score

        delta = score - base_score

        if abs(sum_phi) < 1e-9:
            points = np.zeros_like(phi)
        else:
            points = phi * delta / sum_phi

    except Exception as e:
        logger.error(f"Error computing SHAP values: {e}")
        return {
            "available": False,
            "factors": [],
            "base_score": 0.0,
            "score": baseline_score or 0.0,
        }

    all_factors = []
    for col, pts, p_val in zip(FEATURE_COLS, points, phi):
        val = row.get(col, 0.0)
        label = FEATURE_LABELS.get(col, col)
        formatted_val = format_feature_value(col, val)
        rounded_pts = round(float(pts), 1)

        all_factors.append({
            "feature": col,
            "label": label,
            "value": formatted_val,
            "points": rounded_pts,
            "raw_points": float(pts),
            "factor": label,
            "impact": int(round(rounded_pts)),
            "description": f"{label}: {formatted_val} ({'+' if rounded_pts >= 0 else ''}{rounded_pts} pts)",
        })

    # Sort by absolute points descending
    all_factors.sort(key=lambda x: abs(x["raw_points"]), reverse=True)

    top_5 = all_factors[:5]
    remaining = all_factors[5:]

    sum_top_5 = sum(f["points"] for f in top_5)
    rounded_delta = round(delta, 1)
    other_pts = round(rounded_delta - sum_top_5, 1)

    other_row = {
        "feature": "OtherFactors",
        "label": "Other factors",
        "value": f"{len(remaining)} features combined",
        "points": other_pts,
        "raw_points": float(other_pts),
        "factor": "Other factors",
        "impact": int(round(other_pts)),
        "description": f"Other factors: combined impact ({'+' if other_pts >= 0 else ''}{other_pts} pts)",
    }

    display_factors = top_5 + [other_row]

    return {
        "available": True,
        "factors": display_factors,
        "base_score": round(base_score, 1),
        "score": round(score, 1),
    }
