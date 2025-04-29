from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from api.database import engine
from api.schemas import Wrestler
from api.auth import get_current_user

router = APIRouter(
    prefix="/wrestlers",
    tags=["Wrestlers"],
)

@router.get("/")
def list_wrestlers():
    with Session(engine) as session:
        wrestlers = session.exec(select(Wrestler)).all()
        return wrestlers

@router.get("/{wrestler_id}")
def get_wrestler(wrestler_id: int):
    with Session(engine) as session:
        wrestler = session.get(Wrestler, wrestler_id)
        if not wrestler:
            raise HTTPException(status_code=404, detail="Wrestler not found")
        return wrestler

@router.patch("/{wrestler_id}")
def update_wrestler(wrestler_id: int, wrestler: Wrestler, user=Depends(get_current_user)):
    if user.role not in ["editor", "admin", "superadmin"]:
        raise HTTPException(status_code=403, detail="Not authorized")
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
