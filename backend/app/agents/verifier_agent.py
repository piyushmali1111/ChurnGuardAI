import json
from app.config import settings

BANNED_UNGROUNDED_WORDS = ["cart", "checkout", "promo code", "tracking"]

def run_verifier_agent(offer_draft: dict, max_discount_ceiling: int = None) -> dict:
    """
    Section 8 & Section 9:
    Rule-based Verifier Agent checking business guardrails.
    - Rejects draft if message or reasoning contains words from banned list unless supported by allowed_facts.
    - Caps or verifies discount within safety ceiling.
    """
    max_discount = max_discount_ceiling if max_discount_ceiling is not None else settings.MAX_DISCOUNT_PERCENT
    discount = offer_draft.get("discount_percent", 0)
    message = offer_draft.get("drafted_message", "")
    reasoning = offer_draft.get("reasoning", "")
    allowed_facts = offer_draft.get("allowed_facts", {})
    allowed_str = json.dumps(allowed_facts).lower() if allowed_facts else ""

    # Check for banned ungrounded words
    combined_text = f"{message} {reasoning}".lower()
    for bw in BANNED_UNGROUNDED_WORDS:
        if bw in combined_text and bw not in allowed_str:
            return {
                "status": "REJECTED_UNGROUNDED_FACT",
                "is_valid": False,
                "reason": f"Draft contains ungrounded term '{bw}' not supported by customer data.",
                "verified_offer": None,
            }

    if discount > max_discount:
        # Cap discount to ceiling
        offer_draft["discount_percent"] = max_discount
        discount = max_discount
        status = "COMPLIANT_MODIFIED"
        reason = f"Discount capped to ceiling {max_discount}%."
    elif not message or len(message.strip()) < 10:
        return {
            "status": "REJECTED_INVALID_MESSAGE",
            "is_valid": False,
            "reason": "Drafted message too short or empty.",
            "verified_offer": None,
        }
    else:
        status = "VERIFIED_APPROVED"
        reason = f"Discount {discount}% is within ceiling {max_discount}%. Queued for human approval."

    return {
        "status": status,
        "is_valid": True,
        "reason": reason,
        "verified_offer": offer_draft,
    }
