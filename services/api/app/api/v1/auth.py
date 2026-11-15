import time
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.security import create_token, hash_password, verify_password
from app.db.session import get_db
from app.models import User, UserPreference
from app.schemas.auth import LoginIn, RegisterIn, TokenOut, UserOut

router = APIRouter()
_hits: dict[str, list[float]] = defaultdict(list)


def rate_limit(request: Request):
    """Fixed in-process limiter; callers cannot weaken it with query parameters.

    Move this state to Redis before running multiple API instances.
    """
    limit, window = 10, 60
    key = request.client.host if request.client else "unknown"
    now = time.time()
    _hits[key] = [t for t in _hits[key] if now - t < window]
    if len(_hits[key]) >= limit:
        raise HTTPException(429, "Too many attempts. Try again in a minute.")
    _hits[key].append(now)


@router.post("/register", response_model=TokenOut, status_code=201, dependencies=[Depends(rate_limit)])
def register(body: RegisterIn, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.email == body.email.lower())):
        raise HTTPException(409, "An account with this email already exists.")
    user = User(email=body.email.lower(), display_name=body.display_name, password_hash=hash_password(body.password))
    user.preferences = UserPreference()
    db.add(user)
    db.commit()
    return TokenOut(access_token=create_token(user.id))


@router.post("/login", response_model=TokenOut, dependencies=[Depends(rate_limit)])
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Incorrect email or password.")
    return TokenOut(access_token=create_token(user.id))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user
