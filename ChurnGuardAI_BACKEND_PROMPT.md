# ChurnGuardAI — Backend Build Prompt

Paste this entire file into your Agentic IDE as the instruction for the backend. It covers the full architecture: the database, the basic ML churn model, the ticket sentiment model, the multi-agent system, the scheduled proactive scan, and every API endpoint the frontend expects. Build in the order given at the bottom.

---

## 1. What You Are Building

The backend for **ChurnGuardAI**, a system that:
1. Predicts which e-commerce customers are likely to churn, using a basic ML model trained on customer behavior data.
2. Reads live support tickets and scores their sentiment/urgency.
3. Combines both signals to decide if a customer needs a retention action right now.
4. Runs a small team of AI agents (not one big model) that read the ticket, decide the risk, and draft a personalized retention offer.
5. Holds every drafted offer for human approval before anything is sent.
6. Runs on a schedule too (not just when a ticket comes in) — most churn happens silently, without a ticket ever being filed.
7. Logs outcomes (was the offer accepted? did the customer actually stay?) to close the feedback loop.

---

## 2. Tech Stack (use exactly this)

- **Framework:** FastAPI (Python 3.11+)
- **Server:** Uvicorn
- **Data validation:** Pydantic v2
- **Database:** SQLite for local dev (via SQLAlchemy ORM), structured so it's a one-line swap to PostgreSQL later
- **ML:** pandas, scikit-learn, xgboost, imbalanced-learn (for SMOTE), shap
- **Sentiment model:** VADER (`vaderSentiment`) for MVP speed — no training needed; leave a clear seam to swap in a fine-tuned transformer later
- **Agent orchestration:** LangGraph
- **LLM calls (for agent text generation):** Gemini API (`google-genai` Python SDK) — read the API key from `GEMINI_API_KEY` env var. Never hardcode keys.
- **Knowledge base / RAG:** ChromaDB (local, file-based) + `sentence-transformers` for embeddings, used by the Support Agent to answer FAQs
- **Scheduling:** APScheduler, for the daily/weekly proactive churn scan
- **Real-time:** FastAPI's native WebSocket support for `/ws/agent-activity`
- **CORS:** enabled for the Next.js frontend's origin (read from `FRONTEND_ORIGIN` env var)

---

## 3. Project Structure

```
backend/
├── app/
│   ├── main.py                     # FastAPI app, mounts routers, CORS, WS
│   ├── config.py                   # env var loading (pydantic-settings)
│   ├── api/
│   │   └── routes/
│   │       ├── customers.py
│   │       ├── tickets.py
│   │       ├── offers.py
│   │       ├── dashboard.py
│   │       └── scan.py
│   ├── db/
│   │   ├── models.py               # SQLAlchemy models
│   │   ├── session.py
│   │   └── seed_data.py            # generates/loads sample data
│   ├── ml/
│   │   ├── train_churn_model.py    # EDA + training script (run offline, saves model)
│   │   ├── churn_predictor.py      # loads saved model, exposes predict(customer)
│   │   ├── shap_explainer.py       # loads SHAP explainer, exposes explain(customer)
│   │   └── sentiment_model.py      # VADER wrapper, exposes score(text)
│   ├── agents/
│   │   ├── support_agent.py
│   │   ├── risk_fusion_agent.py
│   │   ├── retention_agent.py
│   │   ├── verifier_agent.py
│   │   └── orchestrator.py         # LangGraph graph wiring all agents together
│   ├── services/
│   │   └── rag_service.py          # FAQ knowledge base (Chroma + embeddings)
│   ├── scheduler/
│   │   └── proactive_scan.py       # APScheduler job: batch-scores every customer
│   └── websocket/
│       └── agent_activity.py       # broadcasts agent step events to connected clients
├── data/
│   ├── ecommerce_churn.csv         # Kaggle dataset (or synthetic fallback — see §5)
│   └── faq_knowledge_base.md       # sample FAQ docs for RAG
├── models/                          # saved model artifacts (.pkl / .joblib)
├── requirements.txt
├── .env.example
└── README.md
```

---

## 4. Database Models (SQLAlchemy)

- **Customer**: id, name, email, signup_date, last_order_date, order_count, total_spent, complaint_count, satisfaction_score, churn_risk_score, churn_status (Safe/Watching/High Risk)
- **Ticket**: id, customer_id (FK), message, sentiment_label, sentiment_score, agent_reply, created_at
- **Offer**: id, customer_id (FK), ticket_id (nullable FK — null if proactively generated, not from a ticket), drafted_message, discount_percent, reasoning, status (Pending/Approved/Rejected/Edited), created_at, decided_at
- **Outcome**: id, offer_id (FK), customer_stayed (bool, nullable until known), checked_at — this is the feedback-loop table

---

## 5. Data Setup

Use the Kaggle "E-Commerce Customer Churn" dataset (or an equivalent public churn dataset) if the user has downloaded it into `/data/ecommerce_churn.csv`. **If the file is not present, write a `generate_synthetic_data.py` script that creates a realistic synthetic dataset with the same schema** (customer behavioral features + a churn label, roughly 5,000 rows, realistic class imbalance of ~15-20% churners) so the whole project runs end-to-end immediately without requiring a manual download. Also generate ~50 synthetic support tickets with a mix of angry/neutral/happy tones for demo purposes.

---

## 6. The Basic ML Layer (Layer 1)

Build `train_churn_model.py` as a standalone script (run once, offline, not part of the API request path):
1. Load and clean the churn dataset.
2. Do basic EDA (print/plot churn rate by key features) — keep this in a companion notebook or a `--eda` flag, not required at runtime.
3. Feature engineering: encode categoricals, compute recency/frequency features if not already present.
4. Split train/test.
5. Apply **SMOTE** on the training set only (never on test data) to fix class imbalance.
6. Train and compare **three models**: Logistic Regression, Random Forest, XGBoost. Evaluate all three on Accuracy, Precision, Recall, F1, and ROC-AUC — report all metrics, not just accuracy (accuracy alone is misleading on imbalanced data).
7. Select the best model by ROC-AUC and recall on the churn class (missing a true churner is costlier than a false alarm).
8. Save the final model with `joblib` to `/models/churn_model.pkl`.
9. Fit a `shap.Explainer` on the final model and save it to `/models/shap_explainer.pkl`.

Build `churn_predictor.py` to load the saved model at API startup and expose `predict(customer_features) -> risk_score (0-100)`.

Build `shap_explainer.py` to load the saved explainer and expose `explain(customer_features) -> list of {factor, impact}` — the top 3-5 contributing factors, used by the frontend's "why this score" bar list.

Build `sentiment_model.py` wrapping VADER, exposing `score(ticket_text) -> {label: Angry/Neutral/Happy, urgency: 0-100}`.

---

## 7. The Multi-Agent Layer (Layer 2) — build with LangGraph

Each agent is a node in a LangGraph graph. Build them as separate, testable Python functions/classes first, then wire the graph in `orchestrator.py`.

**`support_agent.py`**
- Input: ticket text + customer_id.
- Uses `rag_service.py` to retrieve relevant FAQ context (ChromaDB similarity search).
- Calls the Gemini API with a prompt template that includes the FAQ context, and drafts a reply.
- Returns: `{reply_text}`.

**`risk_fusion_agent.py`**
- Input: customer_id, optional live sentiment score (null if this is a proactive/scheduled run, not ticket-triggered).
- Fetches the customer's stored churn_risk_score.
- Computes a combined risk: e.g. `combined = 0.7 * churn_risk_score + 0.3 * sentiment_urgency` when a live ticket exists, else just `churn_risk_score`.
- Compares against the configurable threshold (default 70). Returns `{combined_risk, is_high_risk: bool}`.

**`retention_agent.py`**
- Only runs if `is_high_risk` is true.
- Calls the Gemini API with a prompt template including: customer context (tenure, complaint history), the reason for high risk (top SHAP factors + sentiment if applicable), and the business rules (max discount from config).
- Returns: `{drafted_message, discount_percent, reasoning}`.

**`verifier_agent.py`**
- Rule-based (no LLM call needed) — checks the Retention Agent's output against config: `discount_percent <= max_discount`, message length reasonable, no forbidden words/promises. If it fails, send it back to the Retention Agent once with feedback; if it fails twice, flag for manual drafting instead of auto-drafting.

**`orchestrator.py`**
- Wire these as a LangGraph graph: `support_agent` (if ticket-triggered) → `risk_fusion_agent` → conditional edge → (`retention_agent` → `verifier_agent` → save as Pending Offer) or → end.
- Expose one function, `run_agent_pipeline(customer_id, ticket=None)`, callable from both the ticket endpoint (reactive path) and the scheduled scan (proactive path).
- At every node transition, broadcast a status event through `websocket/agent_activity.py` (e.g. `{"agent": "Risk-Fusion Agent", "message": "Flagged customer #124 as High Risk"}`) so the frontend's live feed has something to show.

---

## 8. The Feedback Loop (Layer 3)

- When an Offer is approved and sent, schedule a follow-up check (e.g. via APScheduler, 30 days later) that looks at whether the customer placed a new order — write the result to the `Outcome` table.
- Write a `retrain_from_outcomes.py` placeholder script that, in a future iteration, would pull Outcome data back into the training set for `train_churn_model.py`. It doesn't need to be fully automated for the MVP — a script that can be run manually is enough.

---

## 9. The Proactive Scan (Scheduled Path)

Build `scheduler/proactive_scan.py`:
- An APScheduler job, configurable interval (daily/weekly from Settings).
- Loops through all customers, recomputes churn_risk_score via `churn_predictor.py`, updates the DB.
- For any customer crossing the risk threshold, calls `run_agent_pipeline(customer_id, ticket=None)` — this is the proactive path with no live ticket sentiment involved.
- Also expose this as a manually-triggerable endpoint (`POST /api/scan/run`) so it can be demoed on demand instead of waiting for the schedule.

---

## 10. API Endpoints (must match the frontend contract exactly)

```
GET  /api/dashboard/summary
     -> { total_customers, high_risk_today, retention_rate_30d, pending_offers_count, weekly_trend: [...] }

GET  /api/customers
     -> [ { id, name, churn_risk_score, status, last_order_date, ... } ]

GET  /api/customers/{id}
     -> { ...customer fields, shap_factors: [...], ticket_history: [...], offers: [...] }

GET  /api/tickets
     -> [ { id, customer_id, message, sentiment_label, sentiment_score, agent_reply, created_at } ]

POST /api/tickets
     body: { customer_id, message }
     -> creates the ticket, runs the reactive agent pipeline synchronously (or via background task),
        returns the created ticket + agent_reply + any offer created

GET  /api/offers/pending
     -> [ { id, customer_id, drafted_message, discount_percent, reasoning, status, created_at } ]

POST /api/offers/{id}/approve
     -> marks Approved, "sends" the message (can just log/mock actually sending for MVP)

POST /api/offers/{id}/reject
     -> marks Rejected

PATCH /api/offers/{id}
     body: { drafted_message?, discount_percent? }
     -> updates the offer before approval

POST /api/scan/run
     -> manually triggers the proactive batch scan, returns count of new offers created

WS   /ws/agent-activity
     -> broadcasts { agent, message, timestamp } events as agents run
```

Use Pydantic schemas for every request/response body — don't return raw SQLAlchemy objects.

---

## 11. Config & Environment

`.env.example`:
```
GEMINI_API_KEY=
DATABASE_URL=sqlite:///./churnguardai.db
FRONTEND_ORIGIN=http://localhost:3000
MAX_DISCOUNT_PERCENT=20
RISK_THRESHOLD=70
PROACTIVE_SCAN_INTERVAL=daily
```

---

## 12. Build Order

1. Scaffold FastAPI app, config, DB models, and run `seed_data.py` (with synthetic data fallback) so there's data to work with immediately.
2. Build `train_churn_model.py`, run it once, confirm metrics printed for all 3 models, save the model + SHAP explainer.
3. Build `churn_predictor.py`, `shap_explainer.py`, `sentiment_model.py` and unit-test each in isolation (a quick script calling each with sample input is enough).
4. Build the `dashboard`, `customers`, and `tickets` read-only endpoints first — get the frontend something to render against.
5. Build the RAG service + `support_agent.py`.
6. Build `risk_fusion_agent.py`, `retention_agent.py`, `verifier_agent.py`, then wire `orchestrator.py` with LangGraph.
7. Build the `/api/tickets` POST endpoint to trigger the reactive pipeline end-to-end.
8. Build the `offers` endpoints (pending/approve/reject/patch).
9. Build the WebSocket agent-activity broadcaster and wire it into the orchestrator's node transitions.
10. Build `proactive_scan.py` + the APScheduler job + the manual trigger endpoint.
11. Build the `Outcome` table + the placeholder feedback-loop scripts.

## Definition of Done
- [ ] `train_churn_model.py` runs end-to-end and prints a comparison table for Logistic Regression / Random Forest / XGBoost
- [ ] Churn model + SHAP explainer load correctly at API startup
- [ ] All endpoints in §10 implemented and match the shapes exactly
- [ ] Posting a new ticket triggers the full reactive agent pipeline and (if high risk) creates a Pending offer
- [ ] `/api/scan/run` triggers the proactive path and creates offers for high-risk customers with no ticket involved
- [ ] WebSocket clients receive live agent status events during a pipeline run
- [ ] CORS configured so the Next.js frontend (localhost:3000) can call the API without errors
