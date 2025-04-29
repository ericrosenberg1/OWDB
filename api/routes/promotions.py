from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from api.database import engine
from api.schemas import Promotion
from api.auth import get_current_user

router = APIRouter(
    prefix="/promotions",
    tags=["Promotions"],
)

@router.get("/")
def list_promotions():
    with Session(engine) as session:
        promotions = session.exec(select(Promotion)).all()
        return promotions

@router.get("/{promotion_id}")
def get_promotion(promotion_id: int):
    with Session(engine) as session:
        promotion = session.get(Promotion, promotion_id)
        if not promotion:
            raise HTTPException(status_code=404, detail="Promotion not found")
        return promotion

@router.patch("/{promotion_id}")
def update_promotion(promotion_id: int, promotion: Promotion, user=Depends(get_current_user)):
    if user.role not in ["editor", "admin", "superadmin"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    with Session(engine) as session:
        db_promotion = session.get(Promotion, promotion_id)
        if not db_promotion:
            raise HTTPException(status_code=404, detail="Promotion not found")
        promotion_data = promotion.dict(exclude_unset=True)
        for key, value in promotion_data.items():
            setattr(db_promotion, key, value)
        session.add(db_promotion)
        session.commit()
        session.refresh(db_promotion)
        return db_promotion
