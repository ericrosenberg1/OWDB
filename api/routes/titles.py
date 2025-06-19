from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from api.database import engine
from api.schemas import Title, APIKey, User
from api.auth import get_verified_user, require_api_key

router = APIRouter(
    prefix="/titles",
    tags=["Titles"],
)

@router.get("/")
def list_titles(api_key: APIKey = Depends(require_api_key)):
    with Session(engine) as session:
        titles = session.exec(select(Title)).all()
        return titles

@router.get("/{title_id}")
def get_title(title_id: int, api_key: APIKey = Depends(require_api_key)):
    with Session(engine) as session:
        title = session.get(Title, title_id)
        if not title:
            raise HTTPException(status_code=404, detail="Title not found")
        return title

@router.patch("/{title_id}")
def update_title(
    title_id: int,
    title: Title,
    user: User = Depends(get_verified_user),
):
    with Session(engine) as session:
        db_title = session.get(Title, title_id)
        if not db_title:
            raise HTTPException(status_code=404, detail="Title not found")
        title_data = title.dict(exclude_unset=True)
        for key, value in title_data.items():
            setattr(db_title, key, value)
        session.add(db_title)
        session.commit()
        session.refresh(db_title)
        return db_title
