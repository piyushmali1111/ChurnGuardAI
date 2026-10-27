import uuid
import asyncio
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END
from app.agents.support_agent import run_support_agent
from app.agents.risk_fusion_agent import run_risk_fusion_agent
from app.agents.retention_agent import run_retention_agent
from app.agents.verifier_agent import run_verifier_agent
from app.websocket.agent_activity import broadcaster
from app.config import settings

class AgentPipelineGraphState(TypedDict):
    run_id: str
    chip: str
    ticket_id: Optional[str]
    offer_id: Optional[str]
    customer_id: str
    customer_name: str
    ticket_text: Optional[str]
    sentiment_urgency: Optional[int]
    churn_risk_score: int
    shap_factors: list
    total_spent: float
    recency_days: int
    order_count: int
    complaint_count: int
    satisfaction_score: float
    support_reply: Optional[str]
    baseline_score: int
    urgency_score: Optional[int]
    fused_score: int
    combined_risk: int
    is_high_risk: bool
    risk_threshold: int
    max_discount_ceiling: int
    drafted_offer: Optional[dict]
    verified_offer: Optional[dict]

def emit_event(agent: str, message: str, type_label: str, chip: str, run_id: str):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(broadcaster.broadcast_event(
                agent=agent,
                message=message,
                type_label=type_label,
                chip=chip,
                run_id=run_id
            ))
    except Exception:
        pass

def support_agent_node(state: AgentPipelineGraphState) -> AgentPipelineGraphState:
    ticket_text = state.get("ticket_text")
    cust_name = state.get("customer_name", "Customer")
    chip = state.get("chip", "Ticket")
    run_id = state.get("run_id", "")

    if ticket_text:
        reply = run_support_agent(ticket_text, cust_name)
        state["support_reply"] = reply
        tck_id = state.get("ticket_id") or "Ticket"
        emit_event(
            agent="Support Agent",
            message=f"Processed ticket #{tck_id} for {cust_name}: Drafted compliant support reply.",
            type_label="info",
            chip=chip,
            run_id=run_id
        )
    return state

def risk_fusion_node(state: AgentPipelineGraphState) -> AgentPipelineGraphState:
    churn_score = state.get("churn_risk_score", 50)
    urgency = state.get("sentiment_urgency")
    threshold = state.get("risk_threshold", settings.RISK_THRESHOLD)

    res = run_risk_fusion_agent(
        churn_risk_score=churn_score,
        sentiment_urgency=urgency,
        risk_threshold=threshold
    )

    state["baseline_score"] = res["baseline_score"]
    state["urgency_score"] = res["urgency_score"]
    state["fused_score"] = res["fused_score"]
    state["combined_risk"] = res["combined_risk"]
    state["is_high_risk"] = res["is_high_risk"]

    chip = state.get("chip", "Risk")
    run_id = state.get("run_id", "")

    # Section 9 exact format:
    # "Risk-Fusion Agent: Baseline 87, Urgency 92, Fused 88 >= threshold 60. Escalating."
    if urgency is not None:
        if res["is_high_risk"]:
            msg = f"Baseline {res['baseline_score']}, Urgency {urgency}, Fused {res['fused_score']} >= threshold {threshold}. Escalating."
            evt_type = "alert"
        else:
            msg = f"Baseline {res['baseline_score']}, Urgency {urgency}, Fused {res['fused_score']} < threshold {threshold}. No escalation."
            evt_type = "info"
    else:
        if res["is_high_risk"]:
            msg = f"Baseline {res['baseline_score']} >= threshold {threshold}. Escalating."
            evt_type = "alert"
        else:
            msg = f"Baseline {res['baseline_score']} < threshold {threshold}. Safe."
            evt_type = "info"

    emit_event(
        agent="Risk-Fusion Agent",
        message=msg,
        type_label=evt_type,
        chip=chip,
        run_id=run_id
    )

    return state

def retention_agent_node(state: AgentPipelineGraphState) -> AgentPipelineGraphState:
    if not state.get("is_high_risk"):
        return state

    cust_name = state.get("customer_name", "Customer")
    combined_risk = state.get("combined_risk", 60)
    shap = state.get("shap_factors", [])
    tck_text = state.get("ticket_text")
    total_spent = state.get("total_spent", 0.0)
    recency = state.get("recency_days", 30)
    orders = state.get("order_count", 0)
    complaints = state.get("complaint_count", 0)
    sat = state.get("satisfaction_score", 5.0)
    urgency = state.get("urgency_score")
    max_disc = state.get("max_discount_ceiling", settings.MAX_DISCOUNT_PERCENT)

    draft = run_retention_agent(
        customer_name=cust_name,
        combined_risk=combined_risk,
        shap_factors=shap,
        ticket_text=tck_text,
        total_spent=total_spent,
        recency_days=recency,
        order_count=orders,
        complaint_count=complaints,
        satisfaction_score=sat,
        urgency_score=urgency,
        max_discount=max_disc
    )
    state["drafted_offer"] = draft

    chip = state.get("chip", "Retention")
    run_id = state.get("run_id", "")
    emit_event(
        agent="Retention Agent",
        message=f"Drafted {draft['discount_percent']}% win-back offer for customer {cust_name}.",
        type_label="info",
        chip=chip,
        run_id=run_id
    )

    return state

def verifier_agent_node(state: AgentPipelineGraphState) -> AgentPipelineGraphState:
    draft = state.get("drafted_offer")
    chip = state.get("chip", "Verifier")
    run_id = state.get("run_id", "")
    max_ceiling = state.get("max_discount_ceiling", settings.MAX_DISCOUNT_PERCENT)
    offer_id = state.get("offer_id") or "OFFER-NEW"

    if draft:
        v_res = run_verifier_agent(draft, max_discount_ceiling=max_ceiling)
        state["verified_offer"] = v_res["verified_offer"]

        # Section 9 exact format:
        # "Offer #OFFER-105 discount 20% is within ceiling 25%. Queued for human approval."
        if v_res["is_valid"]:
            disc = draft.get("discount_percent", max_ceiling)
            msg = f"Offer #{offer_id} discount {disc}% is within ceiling {max_ceiling}%. Queued for human approval."
            evt_type = "success"
        else:
            msg = f"Offer #{offer_id} rejected by guardrail: {v_res['reason']}"
            evt_type = "alert"

        emit_event(
            agent="Verifier Agent",
            message=msg,
            type_label=evt_type,
            chip=chip,
            run_id=run_id
        )

    return state

def should_draft_offer(state: AgentPipelineGraphState) -> str:
    if state.get("is_high_risk"):
        return "retention_agent"
    return END

# Build LangGraph workflow
workflow = StateGraph(AgentPipelineGraphState)
workflow.add_node("support_agent", support_agent_node)
workflow.add_node("risk_fusion", risk_fusion_node)
workflow.add_node("retention_agent", retention_agent_node)
workflow.add_node("verifier_agent", verifier_agent_node)

workflow.set_entry_point("support_agent")
workflow.add_edge("support_agent", "risk_fusion")
workflow.add_conditional_edges("risk_fusion", should_draft_offer)
workflow.add_edge("retention_agent", "verifier_agent")
workflow.add_edge("verifier_agent", END)

app_graph = workflow.compile()

def run_agent_pipeline(
    customer_id: str,
    customer_name: str,
    churn_risk_score: int,
    shap_factors: list,
    total_spent: float,
    ticket_text: Optional[str] = None,
    sentiment_urgency: Optional[int] = None,
    ticket_id: Optional[str] = None,
    offer_id: Optional[str] = None,
    recency_days: int = 30,
    order_count: int = 0,
    complaint_count: int = 0,
    satisfaction_score: float = 5.0,
    risk_threshold: Optional[int] = None,
    max_discount_ceiling: Optional[int] = None,
) -> dict:
    run_id = f"RUN-{uuid.uuid4().hex[:6].upper()}"
    chip = f"#{ticket_id}" if ticket_id else "Proactive Scan"

    initial_state: AgentPipelineGraphState = {
        "run_id": run_id,
        "chip": chip,
        "ticket_id": ticket_id,
        "offer_id": offer_id,
        "customer_id": customer_id,
        "customer_name": customer_name,
        "ticket_text": ticket_text,
        "sentiment_urgency": sentiment_urgency,
        "churn_risk_score": churn_risk_score,
        "shap_factors": shap_factors,
        "total_spent": total_spent,
        "recency_days": recency_days,
        "order_count": order_count,
        "complaint_count": complaint_count,
        "satisfaction_score": satisfaction_score,
        "support_reply": None,
        "baseline_score": churn_risk_score,
        "urgency_score": sentiment_urgency,
        "fused_score": churn_risk_score,
        "combined_risk": churn_risk_score,
        "is_high_risk": False,
        "risk_threshold": risk_threshold if risk_threshold is not None else settings.RISK_THRESHOLD,
        "max_discount_ceiling": max_discount_ceiling if max_discount_ceiling is not None else settings.MAX_DISCOUNT_PERCENT,
        "drafted_offer": None,
        "verified_offer": None,
    }

    final_state = app_graph.invoke(initial_state)
    return final_state
