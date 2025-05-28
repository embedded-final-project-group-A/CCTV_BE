from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session
from dependencies.models import User
from dependencies.schemas import UserProfile
from dependencies.db import get_db

user_router = APIRouter()

@user_router.get("/api/user/profile", response_model=UserProfile)
def get_user_profile(user_id: int = Query(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserProfile(id=user.id, username=user.username, email=user.email)