from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from api.database import engine
from api.schemas import Special
from api.auth import get_current_user

router = APIRouter(
    prefix="/specials",
    tags=["Specials/Movies"],
)

@router.get("/")
def list_specials():
    with Session(engine) as session:
        specials = session.exec(select(Special)).all()
        return specials

@router.get("/{special_id}")
def get_special(special_id: int):
    with Session(engine) as session:
        special = session.get(Special, special_id)
        if not special:
            raise HTTPException(status_code=404, detail="Special not found")
        return special

@router.patch("/{special_id}")
def update_special(special_id: int, special: Special, user=Depends(get_current_user)):
    if user.role not in ["editor", "admin", "superadmin"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    with Session(engine) as session:
        db_special = session.get(Special, special_id)
        if not db_special:
            raise HTTPException(status_code=404, detail="Special not found")
        special_data = special.dict(exclude_unset=True)
        for key, value in special_data.items():
            setattr(db_special, key, value)
        session.add(db_special)
        session.commit()
        session.refresh(db_special)
        return db_special
