import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db.models import Base
from app.db.session import engine
from app.db.seed_data import seed_db
from app.api.routes import dashboard, customers, tickets, offers, scan, settings as settings_route
from app.websocket.agent_activity import broadcaster
from app.scheduler.proactive_scan import start_scheduler, stop_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("[*] ChurnGuardAI Backend starting up...")
    Base.metadata.create_all(bind=engine)
    seed_db()
    start_scheduler()
    print("[+] API ready.")
    yield
    # Shutdown
    stop_scheduler()
    print("[*] ChurnGuardAI Backend shutting down.")

app = FastAPI(
    title="ChurnGuardAI API",
    description="Autonomous E-Commerce Churn Prevention — FastAPI backend with ML, LangGraph agents, and RAG.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN, "http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount REST routers
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(customers.router, prefix="/api/customers", tags=["Customers"])
app.include_router(tickets.router, prefix="/api/tickets", tags=["Tickets"])
app.include_router(offers.router, prefix="/api/offers", tags=["Offers"])
app.include_router(scan.router, prefix="/api/scan", tags=["Scan"])
app.include_router(settings_route.router, prefix="/api/settings", tags=["Settings"])

# WebSocket endpoint for live agent activity stream
@app.websocket("/ws/agent-activity")
async def ws_agent_activity(websocket: WebSocket):
    await broadcaster.connect(websocket)
    try:
        # Keep connection alive
        while True:
            await asyncio.sleep(30)
            await websocket.send_text('{"type":"ping"}')
    except WebSocketDisconnect:
        broadcaster.disconnect(websocket)
    except Exception:
        broadcaster.disconnect(websocket)

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "ChurnGuardAI API"}
