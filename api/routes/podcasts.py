from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from api.database import engine
from api.schemas import Podcast
from api.auth import get_current_user

router = APIRouter(
    prefix="/podcasts",
    tags=["Podcasts"],
)

@router.get("/")
def list_podcasts():
    with Session(engine) as session:
        podcasts = session.exec(select(Podcast)).all()
        return podcasts

@router.get("/{podcast_id}")
def get_podcast(podcast_id: int):
    with Session(engine) as session:
        podcast = session.get(Podcast, podcast_id)
        if not podcast:
            raise HTTPException(status_code=404, detail="Podcast not found")
        return podcast

@router.patch("/{podcast_id}")
def update_podcast(podcast_id: int, podcast: Podcast, user=Depends(get_current_user)):
    if user.role not in ["editor", "admin", "superadmin"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    with Session(engine) as session:
        db_podcast = session.get(Podcast, podcast_id)
        if not db_podcast:
            raise HTTPException(status_code=404, detail="Podcast not found")
        podcast_data = podcast.dict(exclude_unset=True)
        for key, value in podcast_data.items():
            setattr(db_podcast, key, value)
        session.add(db_podcast)
        session.commit()
        session.refresh(db_podcast)
        return db_podcast
