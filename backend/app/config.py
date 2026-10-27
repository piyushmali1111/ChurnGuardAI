import os
from pydantic_settings import BaseSettings

base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
raw_db_url = os.getenv("DATABASE_URL", "sqlite:///./churnguardai.db")
if raw_db_url.startswith("sqlite:///./"):
    db_name = raw_db_url.replace("sqlite:///./", "")
    resolved_db_url = f"sqlite:///{os.path.join(base_dir, db_name)}"
else:
    resolved_db_url = raw_db_url

class Settings(BaseSettings):
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    ENABLE_LIVE_LLM: bool = os.getenv("ENABLE_LIVE_LLM", "false").lower() == "true"
    DATABASE_URL: str = resolved_db_url
    FRONTEND_ORIGIN: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")
    MAX_DISCOUNT_PERCENT: int = int(os.getenv("MAX_DISCOUNT_PERCENT", "25"))
    RISK_THRESHOLD: int = int(os.getenv("RISK_THRESHOLD", "60"))
    FUSION_ALPHA: float = float(os.getenv("FUSION_ALPHA", "0.7"))
    PROACTIVE_SCAN_INTERVAL: str = os.getenv("PROACTIVE_SCAN_INTERVAL", "daily")

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
