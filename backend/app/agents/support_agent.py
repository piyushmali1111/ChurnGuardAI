import os
from app.services.rag_service import query_faq_context
from app.config import settings

BANNED_COMMITMENT_PHRASES = [
    "has been issued",
    "have issued",
    "refunded",
    "credit has been",
    "we are reshipping",
    "will be reshipped",
    "% off",
    "discount",
]

def contains_banned_commitment(text: str) -> bool:
    lowered = text.lower()
    return any(phrase in lowered for phrase in BANNED_COMMITMENT_PHRASES)

def safe_fallback_reply(customer_name: str) -> str:
    return f"Hi {customer_name}, we're sorry about this. We've flagged your case to our team and will follow up shortly with next steps."

def run_support_agent(ticket_text: str, customer_name: str) -> str:
    """
    RAG-augmented Support Agent drafting customer replies.
    Section 7:
    The agent may apologize, acknowledge the problem, answer from the FAQ
    and say the case has been flagged for review.
    It must not state that a refund, credit, discount, replacement, reshipment
    or any other money or logistics action has been issued, completed or guaranteed.
    """
    faq_context = query_faq_context(ticket_text)
    api_key = settings.GEMINI_API_KEY

    system_instruction = f"""
    You are an empathetic, professional e-commerce customer support representative for ChurnGuardAI.
    Draft a reassuring response to this customer ticket.

    Customer Name: {customer_name}
    Ticket Message: "{ticket_text}"

    Knowledge Base Context:
    {faq_context}

    CRITICAL RULES:
    1. Apologize sincerely and acknowledge the specific problem described by the customer.
    2. Inform the customer that their case has been logged and escalated to our operations team for review.
    3. You MUST NOT state or imply that a refund, store credit, discount, coupon, replacement, or reshipment has been issued, granted, or completed.
    4. You may say: "our team is reviewing this and will confirm next steps shortly."
    5. Keep the response concise, professional, and reassuring.
    """

    candidate_reply = None

    if api_key and settings.ENABLE_LIVE_LLM:
        try:
            from google import genai
            import concurrent.futures

            def _call_gemini():
                client = genai.Client(api_key=api_key)
                return client.models.generate_content(
                    model="gemini-3.8-flash",
                    contents=system_instruction
                )

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_call_gemini)
                response = future.result(timeout=2.0)
                if response and response.text:
                    candidate_reply = response.text.strip()
        except Exception:
            candidate_reply = None

    if not candidate_reply or contains_banned_commitment(candidate_reply):
        # Deterministic compliant fallbacks
        lowered = ticket_text.lower()
        if "damage" in lowered or "crush" in lowered or "broken" in lowered:
            candidate_reply = f"Hi {customer_name}, we deeply apologize for the damaged item! We have flagged your ticket for urgent inspection, and our team is reviewing this and will confirm next steps shortly."
        elif "delay" in lowered or "pending" in lowered or "late" in lowered or "week" in lowered:
            candidate_reply = f"Dear {customer_name}, we sincerely apologize for the shipping delay. We have contacted our courier team to trace your package, and our team is reviewing this and will confirm next steps shortly."
        elif "pause" in lowered or "cancel" in lowered:
            candidate_reply = f"Hello {customer_name}, thank you for contacting us regarding your account. Our support team is reviewing your request and will follow up with full details."
        else:
            candidate_reply = safe_fallback_reply(customer_name)

    # Final safeguard
    if contains_banned_commitment(candidate_reply):
        candidate_reply = safe_fallback_reply(customer_name)

    return candidate_reply
