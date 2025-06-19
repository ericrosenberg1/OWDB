from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from api.database import engine
from api.schemas import Venue, APIKey, User
from api.auth import get_verified_user, require_api_key

router = APIRouter(
    prefix="/venues",
    tags=["Venues"],
)

@router.get("/")
def list_venues(api_key: APIKey = Depends(require_api_key)):
    with Session(engine) as session:
        venues = session.exec(select(Venue)).all()
        return venues

@router.get("/{venue_id}")
def get_venue(venue_id: int, api_key: APIKey = Depends(require_api_key)):
    with Session(engine) as session:
        venue = session.get(Venue, venue_id)
        if not venue:
            raise HTTPException(status_code=404, detail="Venue not found")
        return venue

@router.post("/")
def create_venue(venue: Venue, user: User = Depends(get_verified_user)):
    with Session(engine) as session:
        session.add(venue)
        session.commit()
        session.refresh(venue)
        return venue

@router.patch("/{venue_id}")
def update_venue(venue_id: int, venue: Venue, user: User = Depends(get_verified_user)):
    with Session(engine) as session:
        db_venue = session.get(Venue, venue_id)
        if not db_venue:
            raise HTTPException(status_code=404, detail="Venue not found")
        venue_data = venue.dict(exclude_unset=True)
        for key, value in venue_data.items():
            setattr(db_venue, key, value)
        session.add(db_venue)
        session.commit()
        session.refresh(db_venue)
        return db_venue
