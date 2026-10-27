from app.config import settings

def run_risk_fusion_agent(
    churn_risk_score: int,
    sentiment_urgency: int = None,
    risk_threshold: int = None,
    alpha: float = None
) -> dict:
    """
    Section 5:
    Fuses baseline ML churn risk score with dynamic live ticket sentiment urgency.
    fused_score = FUSION_ALPHA * baseline + (1 - FUSION_ALPHA) * urgency
    For proactive scans with no ticket, urgency_score is null and fused_score = baseline_score.
    """
    threshold = risk_threshold if risk_threshold is not None else settings.RISK_THRESHOLD
    fusion_alpha = alpha if alpha is not None else settings.FUSION_ALPHA

    baseline = churn_risk_score

    if sentiment_urgency is not None:
        fused = int(round(fusion_alpha * baseline + (1.0 - fusion_alpha) * sentiment_urgency))
        urgency = sentiment_urgency
    else:
        fused = baseline
        urgency = None

    fused = max(0, min(100, fused))
    is_high_risk = fused >= threshold

    return {
        "baseline_score": baseline,
        "urgency_score": urgency,
        "fused_score": fused,
        "combined_risk": fused,
        "is_high_risk": is_high_risk,
        "threshold": threshold,
    }
