from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from api.database import engine
from api.schemas import Wrestler, APIKey, User
from api.auth import get_verified_user, require_api_key

router = APIRouter(
    prefix="/wrestlers",
    tags=["Wrestlers"],
)

@router.get("/")
def list_wrestlers(api_key: APIKey = Depends(require_api_key)):
    with Session(engine) as session:
        wrestlers = session.exec(select(Wrestler)).all()
        return wrestlers

@router.get("/{wrestler_id}")
def get_wrestler(wrestler_id: int, api_key: APIKey = Depends(require_api_key)):
    with Session(engine) as session:
        wrestler = session.get(Wrestler, wrestler_id)
        if not wrestler:
            raise HTTPException(status_code=404, detail="Wrestler not found")
        return wrestler

@router.patch("/{wrestler_id}")
def update_wrestler(
    wrestler_id: int,
    wrestler: Wrestler,
    user: User = Depends(get_verified_user),
):
    with Session(engine) as session:
        db_wrestler = session.get(Wrestler, wrestler_id)
        if not db_wrestler:
            raise HTTPException(status_code=404, detail="Wrestler not found")
        wrestler_data = wrestler.dict(exclude_unset=True)
        for key, value in wrestler_data.items():
            setattr(db_wrestler, key, value)
        session.add(db_wrestler)
        session.commit()
        session.refresh(db_wrestler)
        return db_wrestler
