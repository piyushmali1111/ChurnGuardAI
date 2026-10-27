# ChurnGuardAI: Multimodal Multi-Agent Churn Prevention Platform

**ChurnGuardAI** is an autonomous, explainable e-commerce churn detection and proactive retention platform. It implements a multi-agent swarm architecture with multimodal risk fusion, combine tabular behavioral signals with real-time support interaction sentiment, explainable AI (SHAP), and human-in-the-loop offer approval workflows.

---

## 🌟 Key Capabilities

1. **Multimodal Risk Fusion**:
   - **Baseline Behavioral Score**: Trained XGBoost model with calibrated probabilities (2–98 scale) over customer order recency, frequency, monetary value, complaint count, and satisfaction.
   - **Live Urgency Score**: VADER NLP analysis on live support tickets:
     $$\text{Urgency } U = \text{clamp}\left(\left\lfloor \frac{1 - \text{compound}}{2} \times 100 \right\rfloor, 0, 100\right)$$
   - **Fused Risk Formula**:
     $$\text{Fused Score} = \alpha \cdot \text{Baseline} + (1 - \alpha) \cdot \text{Urgency} \quad (\alpha = 0.7)$$

2. **Autonomous Multi-Agent Swarm**:
   - **Support Agent**: Handles customer inquiries with FAQ retrieval guardrails (strictly barred from making unapproved monetary or shipping commitments).
   - **Risk-Fusion Agent**: Computes calibrated churn probabilities and real-time urgency fusion.
   - **Retention Agent**: Generates tailored discount offers strictly grounded in verified facts.
   - **Verifier Agent**: Deterministic policy enforcement guardrail (enforces maximum discount ceilings, currently 25%).
   - **Human-in-the-Loop Approval**: Queue where store managers review, adjust, approve, or reject drafted retention offers.

3. **Explainable AI (XAI)**:
   - SHAP `TreeExplainer` feature attribution represented in additive points on a 0–100 scale:
     $$\text{points}_j = \frac{\phi_j}{\sum_k \phi_k} (\text{score} - \text{base\_score})$$

4. **Interactive Dashboard**:
   - 8-week cohort retention tracking with dual Y-axes.
   - Real-time WebSocket activity feed with run chips (`#TCK-xxx`, `Proactive Scan`).
   - Server-side paginated customer risk directory (4,850 records).

---

## 🚀 Quickstart Guide

### Prerequisites
- Python 3.10+
- Node.js 18+ and npm

### 1. Backend Setup
```bash
cd backend
pip install -r requirements.txt

# Seed the database with 4,850 calibrated customers and tickets
python -m app.db.seed_data --reseed

# Start the FastAPI server
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
API Documentation will be accessible at: `http://127.0.0.1:8000/docs`

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 🧪 Consistency & Acceptance Testing

To run the automated consistency test suite:
```bash
python tests/test_consistency.py -v
```
All 12 checks validate:
- Zero references to legacy naming conventions
- System settings and dynamic threshold propagation
- Database consistency and calibrated score clamping
- Ticket stories and order recency alignments
- SHAP points conservation and VADER formulas
- Safety guardrails for Support and Retention agents
- 8-week cohort chart labelling (`W1`–`W8`)
