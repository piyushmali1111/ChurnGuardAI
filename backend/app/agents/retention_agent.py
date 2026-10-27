import os
import json
from typing import Dict, Any, List, Optional
from app.config import settings

BANNED_UNGROUNDED_WORDS = ["cart", "checkout", "promo code", "tracking"]

def build_structured_reasoning(shap_factors: List[dict], ticket_text: Optional[str] = None, urgency: Optional[int] = None) -> str:
    """
    Section 8:
    The reasoning field must be generated from the top SHAP factors and the ticket
    (e.g., 'Satisfaction 1.9/5, 4 past complaints, angry ticket about damaged item'), not free text.
    """
    parts = []
    # Add top 2 SHAP factors
    if shap_factors:
        for factor in shap_factors[:2]:
            lbl = factor.get("label", factor.get("factor", ""))
            val = factor.get("value", "")
            pts = factor.get("points", "")
            pts_str = f" ({'+' if pts > 0 else ''}{pts} pts)" if pts != "" else ""
            if val:
                parts.append(f"{lbl} {val}{pts_str}")
            else:
                parts.append(f"{lbl}{pts_str}")

    if ticket_text:
        snippet = ticket_text[:40].strip()
        if urgency and urgency >= 70:
            parts.append(f"urgent ticket regarding '{snippet}'")
        else:
            parts.append(f"ticket filed: '{snippet}'")
    else:
        parts.append("proactive retention scan")

    return ", ".join(parts)

def calculate_target_discount(combined_risk: int, total_spent: float, max_discount: int) -> int:
    """
    Section 8:
    Discount proportional to risk and lifetime spend within [10, MAX_DISCOUNT_PERCENT].
    """
    # Scale between 10% and max_discount
    risk_factor = max(0.0, min(1.0, combined_risk / 100.0))
    spend_factor = min(1.0, total_spent / 3000.0) if total_spent > 0 else 0.0

    raw_discount = 10 + int(round(risk_factor * 0.7 * (max_discount - 10) + spend_factor * 0.3 * (max_discount - 10)))
    return max(10, min(max_discount, raw_discount))

def run_retention_agent(
    customer_name: str,
    combined_risk: int,
    shap_factors: list,
    ticket_text: str = None,
    total_spent: float = 0.0,
    recency_days: int = 30,
    order_count: int = 0,
    complaint_count: int = 0,
    satisfaction_score: float = 5.0,
    urgency_score: int = None,
    max_discount: int = None,
) -> dict:
    """
    Section 8:
    Retention Agent drafting personalized retention offer messages and discount percents.
    Builds allowed_facts and uses only verified grounded facts.
    """
    effective_max_discount = max_discount if max_discount is not None else settings.MAX_DISCOUNT_PERCENT
    target_discount = calculate_target_discount(combined_risk, total_spent, effective_max_discount)

    # Build structured allowed_facts object
    allowed_facts = {
        "customer_name": customer_name,
        "recency_days": recency_days,
        "order_count": order_count,
        "total_spent": total_spent,
        "complaint_count": complaint_count,
        "satisfaction_score": satisfaction_score,
        "current_ticket": ticket_text,
        "urgency_score": urgency_score,
        "top_shap_factors": [
            {"label": f.get("label", f.get("factor")), "value": f.get("value"), "points": f.get("points")}
            for f in shap_factors[:3]
        ] if shap_factors else []
    }

    # Deterministic grounded reasoning (Section 8 requirement)
    reasoning = build_structured_reasoning(shap_factors, ticket_text, urgency_score)

    api_key = settings.GEMINI_API_KEY
    drafted_message = None

    if api_key and settings.ENABLE_LIVE_LLM:
        try:
            from google import genai
            import concurrent.futures

            def _call_gemini_retention():
                client = genai.Client(api_key=api_key)
                return client.models.generate_content(
                    model="gemini-3.8-flash",
                    contents=prompt
                )

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_call_gemini_retention)
                response = future.result(timeout=2.0)
                if response and response.text:
                    txt = response.text.strip()
                    if "{" in txt and "}" in txt:
                        txt = txt[txt.find("{"):txt.rfind("}")+1]
                    data = json.loads(txt)
                    msg = data.get("drafted_message", "")
                    allowed_str = json.dumps(allowed_facts).lower()
                    has_banned = False
                    for bw in BANNED_UNGROUNDED_WORDS:
                        if bw in msg.lower() and bw not in allowed_str:
                            has_banned = True
                            break
                    if not has_banned and len(msg) >= 15:
                        drafted_message = msg
        except Exception:
            drafted_message = None

    if not drafted_message:
        code_str = customer_name.split()[0].upper() if customer_name else "VIP"
        drafted_message = (
            f"Hi {customer_name}, we appreciate your loyalty with us! "
            f"As a gesture of our commitment to your satisfaction, please enjoy an exclusive "
            f"{target_discount}% discount on your next order with code GUARD{target_discount}-{code_str}."
        )

    # Final sanity check: ensure no banned words are in drafted_message or reasoning
    allowed_str = json.dumps(allowed_facts).lower()
    for bw in BANNED_UNGROUNDED_WORDS:
        if bw in drafted_message.lower() and bw not in allowed_str:
            code_str = customer_name.split()[0].upper() if customer_name else "VIP"
            drafted_message = (
                f"Hi {customer_name}, we appreciate your loyalty with us! "
                f"Please enjoy an exclusive {target_discount}% courtesy discount (code GUARD{target_discount}-{code_str}) "
                f"on your next order."
            )
            break

    return {
        "drafted_message": drafted_message,
        "discount_percent": target_discount,
        "reasoning": reasoning,
        "allowed_facts": allowed_facts,
    }
