from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from api.database import engine
from api.schemas import Wrestler, Event, Match
from api.auth import get_current_user

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
)

@router.post("/merge/wrestlers")
def merge_wrestlers(wrestler_id_1: int, wrestler_id_2: int, user=Depends(get_current_user)):
    if user.role != "superadmin":
        raise HTTPException(status_code=403, detail="Only Superadmins can merge")

    with Session(engine) as session:
        wrestler1 = session.get(Wrestler, wrestler_id_1)
        wrestler2 = session.get(Wrestler, wrestler_id_2)
        if not wrestler1 or not wrestler2:
            raise HTTPException(status_code=404, detail="One or both wrestlers not found")

        # Merge simple fields (favor non-empty)
        for field in ["real_name", "aliases", "hometown", "nationality", "finishers", "about"]:
            if getattr(wrestler1, field) is None and getattr(wrestler2, field):
                setattr(wrestler1, field, getattr(wrestler2, field))

        session.delete(wrestler2)
        session.add(wrestler1)
        session.commit()
        session.refresh(wrestler1)

        return {"message": "Merge successful", "wrestler": wrestler1}

# (Similar endpoints for events/matches can be added later cleanly)
