from fastapi import APIRouter, HTTPException, Depends, Header
from sqlmodel import Session, select
from api.database import engine
from api.schemas import User, APIKey
from passlib.hash import bcrypt
import jwt
import os
from datetime import datetime, timedelta
from uuid import uuid4
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request
from fastapi.security import OAuth2PasswordBearer
from fastapi import Request

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)

templates = Jinja2Templates(directory="api/templates")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "supersecretjwt")


def send_verification_email(email: str, token: str) -> None:
    # Placeholder for email sending logic
    print(f"Verify your account: http://localhost:8000/auth/verify/{token}")

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
        token = uuid4().hex
        hashed_password = bcrypt.hash(password)
        new_user = User(
            username=username,
            email=email,
            hashed_password=hashed_password,
            verification_token=token,
        )
        session.add(new_user)
        session.commit()
        session.refresh(new_user)
        send_verification_email(email, token)
        return {"message": "Signup successful. Please verify your email."}

@router.post("/login")
def login(username: str, password: str):
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == username)).first()
        if not user or not bcrypt.verify(password, user.hashed_password):
            raise HTTPException(status_code=400, detail="Incorrect username or password")
        token = create_token(user)
        return {"access_token": token, "token_type": "bearer", "role": user.role}


@router.get("/verify/{token}", response_class=HTMLResponse)
def verify_email(token: str, request: Request):
    with Session(engine) as session:
        user = session.exec(select(User).where(User.verification_token == token)).first()
        if not user:
            raise HTTPException(status_code=400, detail="Invalid token")
        user.is_verified = True
        user.verification_token = None
        session.add(user)
        session.commit()
    return templates.TemplateResponse("verify_email.html", {"request": request})


def get_verified_user(user: User = Depends(get_current_user)) -> User:
    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Email not verified")
    return user


def require_api_key(x_api_key: str = Header(...)) -> APIKey:
    with Session(engine) as session:
        key = session.exec(select(APIKey).where(APIKey.key == x_api_key, APIKey.is_active == True)).first()
        if not key:
            raise HTTPException(status_code=403, detail="Invalid API key")
        now = datetime.utcnow()
        if now - key.last_reset > timedelta(days=1):
            key.usage_count = 0
            key.last_reset = now
        limit = 1000 if key.is_paid else 100
        if key.usage_count >= limit:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        key.usage_count += 1
        session.add(key)
        session.commit()
        return key


@router.post("/api-key")
def create_api_key(user: User = Depends(get_verified_user)):
    with Session(engine) as session:
        token = uuid4().hex
        api_key = APIKey(user_id=user.id, key=token)
        session.add(api_key)
        session.commit()
        session.refresh(api_key)
        return {"api_key": api_key.key}
