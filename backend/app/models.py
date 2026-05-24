import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from .database import Base

def generate_uuid():
    return str(uuid.uuid4())

class Enquiry(Base):
    __tablename__ = "enquiries"

    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    customer_name = Column(String, index=True)
    channel = Column(String, index=True) 
    message = Column(String)
    status = Column(String, default="new") 
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    history = relationship("HistoryEvent", back_populates="enquiry", cascade="all, delete-orphan")

class HistoryEvent(Base):
    __tablename__ = "history_events"

    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    enquiry_id = Column(String, ForeignKey("enquiries.id"))
    action = Column(String) 
    details = Column(JSON, nullable=True) 
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    enquiry = relationship("Enquiry", back_populates="history")