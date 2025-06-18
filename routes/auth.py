from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from dependencies.models import User, Store
from dependencies.schemas import SignUpModel, SignInRequest
from dependencies.db import get_db
from routes import events
import hashlib, os, subprocess
from datetime import datetime
from routes.events import start_alert_scheduler

auth_router = APIRouter()

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def normalize_username(username: str) -> str:
    return username.strip().lower().replace(" ", "_")

@auth_router.post("/signup")
def signup(user: SignUpModel, db: Session = Depends(get_db)):
    hashed_pw = hash_password(user.password)
    new_user = User(username=user.username, email=user.email, password_hash=hashed_pw)
    try:
        db.add(new_user)
        db.commit()

        username = user.username
        video_dir = os.path.join("videos", username)
        output_dir = os.path.join("output", username)
        os.makedirs(video_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)

    except:
        db.rollback()
        raise HTTPException(status_code=400, detail="Username or email already exists.")

    return {"message": "User created successfully"}

@auth_router.post("/login")
def login(req: SignInRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(
        (User.email == req.identifier) | (User.username == req.identifier)
    ).first()

    hashed_input_pw = hash_password(req.password)
    if not user or user.password_hash != hashed_input_pw:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    normalized_username = normalize_username(user.username)

    try:
        stores = db.query(Store).filter(Store.user_id == user.id).all()
        for store in stores:
            clips_path = os.path.join("videos", normalized_username, store.name, "clips")
            output_path = os.path.join("output", normalized_username, store.name)
            if not os.path.exists(clips_path):
                continue
            yolo_script = os.path.join("yolo", "process_videos.py")
            cmd = ["python", yolo_script, "--video_dir", clips_path, "--output_base", output_path, "--debug"]
            subprocess.Popen(cmd)

        # 스케줄러 실행
        start_alert_scheduler(user.id, normalized_username)

    except Exception as e:
        print(f"Error during YOLO execution: {e}")
        # 로그인 시간 갱신도 실패할 수 있으니 여기서도 갱신하도록 함
        events.user_last_login_time[user.id] = datetime.utcnow()
        raise HTTPException(status_code=500, detail="Post login processing failed")

    # 로그인 시간 기록 (try-except 밖, 무조건 갱신)
    events.user_last_login_time[user.id] = datetime.utcnow()

    return {
        "message": "Login successful",
        "username": user.username,
        "user_id": user.id
    }

