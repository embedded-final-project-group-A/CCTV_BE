from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from dependencies.models import User
from dependencies.schemas import SignUpModel, SignInRequest
from dependencies.db import get_db
import bcrypt, hashlib

auth_router = APIRouter()

def hash_password(password: str) -> str:
    """SHA-256 기반 비밀번호 해시 함수"""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

@auth_router.post("/signup")
def signup(user: SignUpModel, db: Session = Depends(get_db)):
    hashed_pw = hash_password(user.password)
    new_user = User(username=user.username, email=user.email, password_hash=hashed_pw)
    try:
        db.add(new_user)
        db.commit()
    except:
        db.rollback()
        raise HTTPException(status_code=400, detail="Username or email already exists.")
    return {"message": "User created successfully"}

@auth_router.post("/login")
def login(req: SignInRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(
        (User.email == req.identifier) | (User.username == req.identifier)
    ).first()
    hashed_input_pw = hashlib.sha256(req.password.encode()).hexdigest()
    if not user or user.password_hash != hashed_input_pw:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"message": "Login successful", "username": user.username, "user_id": user.id}