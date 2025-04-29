from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from api.database import engine
from api.schemas import Event
from api.auth import get_current_user

router = APIRouter(
    prefix="/events",
    tags=["Events"],
)

@router.get("/")
def list_events():
    with Session(engine) as session:
        events = session.exec(select(Event)).all()
        return events

@router.get("/{event_id}")
def get_event(event_id: int):
    with Session(engine) as session:
        event = session.get(Event, event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        return event

@router.patch("/{event_id}")
def update_event(event_id: int, event: Event, user=Depends(get_current_user)):
    if user.role not in ["editor", "admin", "superadmin"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    with Session(engine) as session:
        db_event = session.get(Event, event_id)
        if not db_event:
            raise HTTPException(status_code=404, detail="Event not found")
        event_data = event.dict(exclude_unset=True)
        for key, value in event_data.items():
            setattr(db_event, key, value)
        session.add(db_event)
        session.commit()
        session.refresh(db_event)
        return db_event
