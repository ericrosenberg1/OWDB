from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from api.database import engine
from api.schemas import Match
from api.auth import get_current_user

router = APIRouter(
    prefix="/matches",
    tags=["Matches"],
)

@router.get("/")
def list_matches():
    with Session(engine) as session:
        matches = session.exec(select(Match)).all()
        return matches

@router.get("/{match_id}")
def get_match(match_id: int):
    with Session(engine) as session:
        match = session.get(Match, match_id)
        if not match:
            raise HTTPException(status_code=404, detail="Match not found")
        return match

@router.patch("/{match_id}")
def update_match(match_id: int, match: Match, user=Depends(get_current_user)):
    if user.role not in ["editor", "admin", "superadmin"]:
        raise HTTPException(status_code=403, detail="Not authorized")
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
