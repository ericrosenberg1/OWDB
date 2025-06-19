from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from api.database import engine
from api.schemas import Match, APIKey, User
from api.auth import get_verified_user, require_api_key

router = APIRouter(
    prefix="/matches",
    tags=["Matches"],
)

@router.get("/")
def list_matches(api_key: APIKey = Depends(require_api_key)):
    with Session(engine) as session:
        matches = session.exec(select(Match)).all()
        return matches

@router.get("/{match_id}")
def get_match(match_id: int, api_key: APIKey = Depends(require_api_key)):
    with Session(engine) as session:
        match = session.get(Match, match_id)
        if not match:
            raise HTTPException(status_code=404, detail="Match not found")
        return match

@router.patch("/{match_id}")
def update_match(
    match_id: int,
    match: Match,
    user: User = Depends(get_verified_user),
):
    with Session(engine) as session:
        db_match = session.get(Match, match_id)
        if not db_match:
            raise HTTPException(status_code=404, detail="Match not found")
        match_data = match.dict(exclude_unset=True)
        for key, value in match_data.items():
            setattr(db_match, key, value)
        session.add(db_match)
        session.commit()
        session.refresh(db_match)
        return db_match
