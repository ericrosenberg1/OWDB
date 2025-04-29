from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from api.database import engine
from api.schemas import VideoGame
from api.auth import get_current_user

router = APIRouter(
    prefix="/games",
    tags=["Video Games"],
)

@router.get("/")
def list_games():
    with Session(engine) as session:
        games = session.exec(select(VideoGame)).all()
        return games

@router.get("/{game_id}")
def get_game(game_id: int):
    with Session(engine) as session:
        game = session.get(VideoGame, game_id)
        if not game:
            raise HTTPException(status_code=404, detail="Game not found")
        return game

@router.patch("/{game_id}")
def update_game(game_id: int, game: VideoGame, user=Depends(get_current_user)):
    if user.role not in ["editor", "admin", "superadmin"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    with Session(engine) as session:
        db_game = session.get(VideoGame, game_id)
        if not db_game:
            raise HTTPException(status_code=404, detail="Game not found")
        game_data = game.dict(exclude_unset=True)
        for key, value in game_data.items():
            setattr(db_game, key, value)
        session.add(db_game)
        session.commit()
        session.refresh(db_game)
        return db_game
