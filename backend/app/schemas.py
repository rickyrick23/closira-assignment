from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class EnquiryCreate(BaseModel):
    channel: str = Field(..., description="E.g., whatsapp, email, call")
    customer_name: str
    message: str

class FollowUpRequest(BaseModel):
    delay_minutes: int
    message_template: Optional[str] = None

class EscalateRequest(BaseModel):
    reason: str


class EnquiryResponse(BaseModel):
    job_id: str = Field(..., description="The ID of the async job/enquiry.")
    status: str
    message: str = "Enquiry received. Background processing initiated."

class HistoryEventSchema(BaseModel):
    action: str
    timestamp: datetime
    details: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True

class EnquiryHistoryResponse(BaseModel):
    enquiry_id: str
    customer_name: str
    channel: str
    current_status: str
    timeline: List[HistoryEventSchema]