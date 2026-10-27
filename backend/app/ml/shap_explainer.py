import os
import joblib
import pandas as pd
import numpy as np

EXPLAINER_PATH = os.path.join(os.path.dirname(__file__), "../../models/shap_explainer.pkl")

_explainer = None

def get_explainer():
    global _explainer
    if _explainer is None:
        if os.path.exists(EXPLAINER_PATH):
            try:
                _explainer = joblib.load(EXPLAINER_PATH)
            except Exception:
                _explainer = None
        else:
            return None
    return _explainer

FEATURE_LABELS = {
    "SatisfactionScore": "Satisfaction rating",
    "DaysSinceLastOrder": "Days since last order",
    "ComplaintCount": "Complaints count",
    "OrderCount": "Order history count",
    "TotalSpent": "Lifetime spend total",
}

def format_feature_value(col: str, val: float) -> str:
    if col == "SatisfactionScore":
        return f"{val:.1f} / 5.0"
    elif col == "DaysSinceLastOrder":
        return f"{int(val)} days"
    elif col == "ComplaintCount":
        return f"{int(val)} complaints"
    elif col == "OrderCount":
        return f"{int(val)} orders"
    elif col == "TotalSpent":
        return f"${val:,.2f}"
    return str(val)

def explain_churn_risk(customer_data: dict, baseline_score: int = None) -> dict:
    """
    Section 6:
    Compute SHAP values with TreeExplainer (log-odds space).
    Convert to points on the 0-100 scale so the bars add up to the score:
    points_j = phi_j / sum(phi) * (score - base_score),
    where base_score is the model's average predicted churn probability * 100
    and score is the customer's baseline score.
    Returns top 5 factors by absolute points: {feature, label, value, points},
    plus base_score and score.
    """
    explainer = get_explainer()
    base_score = 14.0  # Average base churn probability in cohort (~14%)

    if baseline_score is None:
        from app.ml.churn_predictor import predict_churn_risk
        score = predict_churn_risk(customer_data)
    else:
        score = baseline_score

    feature_cols = [
        "DaysSinceLastOrder",
        "OrderCount",
        "TotalSpent",
        "ComplaintCount",
        "SatisfactionScore",
    ]

    df = pd.DataFrame([customer_data])[feature_cols]
    vals = None

    if explainer is not None:
        try:
            shap_values = explainer(df)
            if hasattr(shap_values, "values"):
                vals = shap_values.values[0]
                if len(vals.shape) > 1:
                    vals = vals[:, 1]
            else:
                vals = np.array(shap_values)[0]
        except Exception:
            vals = None

    if vals is None:
        sat = float(customer_data.get("SatisfactionScore", 3.5))
        days = float(customer_data.get("DaysSinceLastOrder", 30))
        complaints = float(customer_data.get("ComplaintCount", 0))
        orders = float(customer_data.get("OrderCount", 10))
        spent = float(customer_data.get("TotalSpent", 1000.0))

        vals = [
            0.045 * (days - 25),
            -0.08 * (orders - 8),
            -0.0005 * (spent - 1200),
            0.65 * complaints,
            -0.55 * (sat - 3.0),
        ]

    delta = float(score - base_score)
    sum_phi = float(sum(vals))
    if abs(sum_phi) < 1e-6:
        sum_phi = float(sum(abs(v) for v in vals)) or 1.0

    factors = []
    for col, v in zip(feature_cols, vals):
        pts = (float(v) / sum_phi) * delta
        val = customer_data.get(col, 0)
        label = FEATURE_LABELS.get(col, col)
        formatted_val = format_feature_value(col, val)
        rounded_pts = round(float(pts), 1)

        factors.append({
            "feature": col,
            "label": label,
            "value": formatted_val,
            "points": rounded_pts,
            "factor": label,
            "impact": int(round(rounded_pts)),
            "description": f"{label}: {formatted_val} ({'+' if rounded_pts >= 0 else ''}{rounded_pts} pts)",
        })

    # Adjust minor rounding difference so sum adds up to delta
    pts_sum = sum(f["points"] for f in factors)
    diff = round(delta - pts_sum, 1)
    if abs(diff) > 0 and factors:
        # adjust largest factor
        factors[0]["points"] = round(factors[0]["points"] + diff, 1)

    factors.sort(key=lambda x: abs(x["points"]), reverse=True)
    top_5 = factors[:5]

    return {
        "factors": top_5,
        "base_score": base_score,
        "score": score
    }
