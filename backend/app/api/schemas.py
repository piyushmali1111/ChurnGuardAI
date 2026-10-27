from typing import List, Optional, Any
from pydantic import BaseModel

class WeeklyTrendPoint(BaseModel):
    week: str
    retained: int
    churned: int
    retention_rate: Optional[float] = None

class DashboardSummaryResponse(BaseModel):
    total_customers: int
    high_risk_today: int
    high_risk_total: Optional[int] = None
    high_risk_new_today: Optional[int] = None
    retention_rate_30d: float
    retention_delta_vs_last_month: float
    pending_offers_count: int
    risk_threshold: Optional[int] = 60
    weekly_trend: List[WeeklyTrendPoint]

class ShapFactorSchema(BaseModel):
    feature: str
    label: str
    value: str
    points: float
    factor: Optional[str] = None
    impact: Optional[int] = None
    description: Optional[str] = None

class CustomerSummaryResponse(BaseModel):
    id: str
    name: str
    email: str
    churn_risk_score: float
    baseline_score: Optional[int] = None
    urgency_score: Optional[int] = None
    fused_score: Optional[float] = None
    churn_status: str
    last_order_date: str
    days_inactive: Optional[int] = None
    total_spent: float
    order_count: int

class PaginatedCustomersResponse(BaseModel):
    items: List[CustomerSummaryResponse]
    total: int
    page: int
    page_size: int

class TicketResponse(BaseModel):
    id: str
    customer_id: str
    customer_name: Optional[str] = None
    message: str
    sentiment_label: str
    sentiment_score: int
    urgency_score: Optional[int] = None
    baseline_score: Optional[int] = None
    fused_score: Optional[float] = None
    agent_reply: Optional[str] = None
    created_at: str

class OfferResponse(BaseModel):
    id: str
    customer_id: str
    customer_name: Optional[str] = None
    ticket_id: Optional[str] = None
    drafted_message: str
    discount_percent: int
    reasoning: str
    baseline_score: Optional[int] = None
    urgency_score: Optional[int] = None
    fused_score: Optional[float] = None
    status: str
    created_at: str
    decided_at: Optional[str] = None

class CustomerDetailResponse(CustomerSummaryResponse):
    signup_date: str
    complaint_count: int
    satisfaction_score: float
    base_score: Optional[float] = None
    shap_factors: List[ShapFactorSchema]
    ticket_history: List[TicketResponse]
    offers: List[OfferResponse]

class TicketCreateRequest(BaseModel):
    customer_id: str
    message: str

class OfferPatchRequest(BaseModel):
    drafted_message: Optional[str] = None
    discount_percent: Optional[int] = None

class ScanRunResponse(BaseModel):
    scanned_customers: Optional[int] = None
    high_risk_flagged: Optional[int] = None
    new_offers_count: int
    scan_timestamp: str

class SettingsResponse(BaseModel):
    risk_threshold: int
    max_discount_percent: int
    scan_frequency: str
    fusion_alpha: float = 0.7

class SettingsUpdateRequest(BaseModel):
    risk_threshold: Optional[int] = None
    max_discount_percent: Optional[int] = None
    scan_frequency: Optional[str] = None
