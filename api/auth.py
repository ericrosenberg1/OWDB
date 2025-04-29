from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from api.database import engine
from api.schemas import User
from passlib.hash import bcrypt
import jwt
import os
from datetime import datetime, timedelta
from fastapi.security import OAuth2PasswordBearer
from fastapi import Request

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "supersecretjwt")

def create_token(user: User):
    payload = {
        "sub": user.id,
        "username": user.username,
        "role": user.role,
        "exp": datetime.utcnow() + timedelta(hours=12)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id: int = payload.get("sub")
        with Session(engine) as session:
            user = session.get(User, user_id)
            return user
    except (jwt.ExpiredSignatureError, jwt.JWTError):
        raise HTTPException(status_code=401, detail="Invalid or expired token")

@router.post("/signup")
def signup(username: str, email: str, password: str):
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == username)).first()
        if user:
            raise HTTPException(status_code=400, detail="Username already exists")
        hashed_password = bcrypt.hash(password)
        new_user = User(username=username, email=email, hashed_password=hashed_password, role="rookie")
        session.add(new_user)
        session.commit()
        session.refresh(new_user)
        return {"message": "Signup successful, awaiting approval."}

@router.post("/login")
def login(username: str, password: str):
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == username)).first()
        if not user or not bcrypt.verify(password, user.hashed_password):
            raise HTTPException(status_code=400, detail="Incorrect username or password")
        token = create_token(user)
        return {"access_token": token, "token_type": "bearer", "role": user.role}
