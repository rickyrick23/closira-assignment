import logging
from fastapi import FastAPI, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app import models, schemas
from app.database import engine, get_db, SessionLocal

# JSON-friendly structured logging 
logging.basicConfig(
    level=logging.INFO,
    format='{"time": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}'
)
logger = logging.getLogger("closira-backend")

# SQLite tables 
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Closira Enquiry API",
    description="Backend service powering Closira's inbound customer pipeline.",
    version="1.0.0"
)


def process_sops_background(enquiry_id: str):
    """
    Async background task to match messages to SOPs.
    We open a new DB session specifically for this background worker.
    """
    db: Session = SessionLocal()
    try:
        enquiry = db.query(models.Enquiry).filter(models.Enquiry.id == enquiry_id).first()
        if not enquiry:
            return

        msg_lower = enquiry.message.lower()
        matched_sop = None
        suggested_response = None

        # Hardcoded SOP logic 
        if any(word in msg_lower for word in ["price", "cost", "pricing", "quote"]):
            matched_sop = "pricing_question"
            suggested_response = "Here is a link to our standard pricing page."
        elif any(word in msg_lower for word in ["book", "schedule", "appointment"]):
            matched_sop = "booking_enquiry"
            suggested_response = "Let's get you scheduled. Please pick a time on our calendar."
        elif any(word in msg_lower for word in ["angry", "broken", "issue", "complaint"]):
            matched_sop = "complaint"
            suggested_response = "We apologize for the inconvenience. An agent will contact you shortly."
            enquiry.status = "escalated" # Auto-escalate complaints

        #  history event based on the outcome
        if matched_sop:
            logger.info(f"SOP Matched: {matched_sop} for Enquiry: {enquiry_id}")
            action = "sop_matched"
            details = {"sop": matched_sop, "suggested_response": suggested_response}
        else:
            logger.info(f"No SOP matched. Auto-escalating Enquiry: {enquiry_id}")
            enquiry.status = "escalated"
            action = "escalated"
            details = {"reason": "No SOP match. Requires human review."}

        # Save the event and update the database
        event = models.HistoryEvent(enquiry_id=enquiry.id, action=action, details=details)
        db.add(event)
        db.commit()

    except Exception as e:
        logger.error(f"Error processing background task for {enquiry_id}: {str(e)}")
    finally:
        db.close()



@app.post("/enquiry", response_model=schemas.EnquiryResponse, status_code=status.HTTP_202_ACCEPTED)
def create_enquiry(
    enquiry_data: schemas.EnquiryCreate, 
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_db)
):
    # 1.  base enquiry
    new_enquiry = models.Enquiry(**enquiry_data.model_dump())
    db.add(new_enquiry)
    db.commit()
    db.refresh(new_enquiry)

    # 2. Log the initial creation event
    creation_event = models.HistoryEvent(
        enquiry_id=new_enquiry.id, 
        action="created", 
        details={"channel": new_enquiry.channel}
    )
    db.add(creation_event)
    db.commit()

    logger.info(f"Enquiry created: {new_enquiry.id}")

    # 3. Trigger the async worker
    background_tasks.add_task(process_sops_background, new_enquiry.id)

    # 4. Return immediately 
    return schemas.EnquiryResponse(job_id=new_enquiry.id, status=new_enquiry.status)


@app.post("/enquiry/{id}/follow-up")
def schedule_follow_up(id: str, request: schemas.FollowUpRequest, db: Session = Depends(get_db)):
    enquiry = db.query(models.Enquiry).filter(models.Enquiry.id == id).first()
    if not enquiry:
        raise HTTPException(status_code=404, detail="Enquiry not found")

    event = models.HistoryEvent(
        enquiry_id=id, 
        action="follow_up_scheduled", 
        details=request.model_dump()
    )
    db.add(event)
    db.commit()

    logger.info(f"Follow-up scheduled for: {id}")
    return {"status": "success", "message": f"Follow-up scheduled in {request.delay_minutes} minutes."}


@app.post("/enquiry/{id}/escalate")
def escalate_enquiry(id: str, request: schemas.EscalateRequest, db: Session = Depends(get_db)):
    enquiry = db.query(models.Enquiry).filter(models.Enquiry.id == id).first()
    if not enquiry:
        raise HTTPException(status_code=404, detail="Enquiry not found")

    enquiry.status = "escalated"
    event = models.HistoryEvent(
        enquiry_id=id, 
        action="escalated", 
        details={"reason": request.reason, "manual_escalation": True}
    )
    db.add(event)
    db.commit()

    logger.info(f"Manual escalation for: {id}")
    return {"status": "success", "message": "Enquiry escalated successfully."}


@app.get("/enquiry/{id}/history", response_model=schemas.EnquiryHistoryResponse)
def get_enquiry_history(id: str, db: Session = Depends(get_db)):
    enquiry = db.query(models.Enquiry).filter(models.Enquiry.id == id).first()
    if not enquiry:
        raise HTTPException(status_code=404, detail="Enquiry not found")

    # Fetch history events ordered by time
    events = db.query(models.HistoryEvent).filter(
        models.HistoryEvent.enquiry_id == id
    ).order_by(models.HistoryEvent.timestamp.asc()).all()

    return schemas.EnquiryHistoryResponse(
        enquiry_id=enquiry.id,
        customer_name=enquiry.customer_name,
        channel=enquiry.channel,
        current_status=enquiry.status,
        timeline=events
    )

@app.get("/health", tags=["System"])
def health_check():
    return {"status": "healthy", "database": "connected"}