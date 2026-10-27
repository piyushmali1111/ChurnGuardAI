# ChurnGuardAI Backend

FastAPI + LangGraph + XGBoost + VADER churn prevention backend.

## Quick Start

```bash
cd backend

# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY

# 3. Generate synthetic training data
python generate_synthetic_data.py

# 4. Train ML models (run once — saves to models/)
python app/ml/train_churn_model.py

# 5. Start the API server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API Docs

Visit http://localhost:8000/docs for Swagger UI.

## Architecture
- **Layer 1 (ML):** XGBoost churn predictor + VADER sentiment + SHAP explainer
- **Layer 2 (Agents):** LangGraph multi-agent: Support → Risk Fusion → Retention → Verifier
- **Layer 3 (Feedback):** Outcome logging + `retrain_from_outcomes.py`
