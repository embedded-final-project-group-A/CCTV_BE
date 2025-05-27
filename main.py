from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, Column, Integer, String, or_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from typing import List, Dict, Any
from datetime import datetime
import sqlite3
import bcrypt
import hashlib

# FastAPI 앱 초기화
app = FastAPI()

# DB 설정
DB_PATH = "cctv_system.db"
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
Base = declarative_base()
SessionLocal = sessionmaker(bind=engine, autoflush=False)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 배포 시 수정 권장
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# SQLAlchemy 모델
class User(Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True)
    email = Column(String, unique=True)
    password_hash = Column(String)

Base.metadata.create_all(bind=engine)

# Pydantic 모델
class SignUpModel(BaseModel):
    username: str
    email: EmailStr
    password: str

class SignInRequest(BaseModel):
    identifier: str  # username 또는 email
    password: str

class VideoInfo(BaseModel):
    date: str
    url: str
    type: str
    risk_level: str

class UserProfile(BaseModel):
    id: int
    username: str
    email: EmailStr

class Alert(BaseModel):
    store_id: str
    camera_id: int
    message: str
    timestamp: str

class StoreCreate(BaseModel):
    user_id: int
    name: str
    location: str

class StoreResponse(BaseModel):
    id: int
    user_id: int
    name: str
    location: str

    class Config:
        orm_mode = True

class Store(Base):
    __tablename__ = "store"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    name = Column(String, nullable=False)
    location = Column(String, nullable=False)

    cameras = relationship("Camera", back_populates="store")

Base.metadata.create_all(bind=engine)

# 의존성: DB 세션
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# SQLite 직접 접근 도우미
def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# 회원가입
@app.post("/signup")
def signup(user: SignUpModel, db: Session = Depends(get_db)):
    # 비밀번호 bcrypt 해싱
    hashed_pw = bcrypt.hashpw(user.password.encode(), bcrypt.gensalt()).decode()

    new_user = User(username=user.username, email=user.email, password_hash=hashed_pw)
    try:
        db.add(new_user)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail="Username or email already exists.")
    
    return {"message": "User created successfully"}

# 로그인
@app.post("/login")
def login(req: SignInRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(
        (User.email == req.identifier) | (User.username == req.identifier)
    ).first()

    hashed_input_pw = hashlib.sha256(req.password.encode()).hexdigest()

    if not user or user.password_hash != hashed_input_pw:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return {
        "message": "Login successful",
        "username": user.username,
        "user_id": user.id
    }


# 사용자 ID로 store 목록 조회
@app.get("/api/user/stores", response_model=List[str])
def get_user_stores(user_id: str = Query(...)):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM store WHERE user_id = ?", (user_id,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        raise HTTPException(status_code=404, detail="User not found or no stores")
    return [row["name"] for row in rows]

# store 이름으로 camera 목록 조회
@app.get("/api/store/cameras", response_model=List[Dict[str, Any]])
def get_store_cameras(store: str = Query(...)):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM store WHERE name = ?", (store,))
    store_row = cursor.fetchone()
    if not store_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Store not found")

    store_id = store_row["id"]
    cursor.execute("SELECT id, name, video_url, image_url FROM camera WHERE store_id = ?", (store_id,))
    cameras = [
        {"id": row["id"], "name": row["name"], "video_url": row["video_url"], "image_url": row["image_url"]}
        for row in cursor.fetchall()
    ]
    conn.close()
    return cameras

# 이벤트 영상 목록 조회
@app.get("/api/store/events", response_model=List[VideoInfo])
def get_camera_events(store: str = Query(...), camera_label: str = Query(...)):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM store WHERE name = ?", (store,))
    store_row = cursor.fetchone()
    if not store_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Store not found")
    store_id = store_row["id"]

    cursor.execute("SELECT id FROM camera WHERE store_id = ? AND name = ?", (store_id, camera_label))
    cam_row = cursor.fetchone()
    if not cam_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Camera not found")
    camera_id = cam_row["id"]

    cursor.execute('''
        SELECT e.event_time, e.video_url, et.type, et.risk_level
        FROM event e
        JOIN event_type et ON e.type_id = et.id
        WHERE e.store_id = ? AND e.camera_id = ?
        ORDER BY e.event_time DESC
    ''', (store_id, camera_id))

    videos = []
    for row in cursor.fetchall():
        try:
            formatted_date = datetime.fromisoformat(row["event_time"]).strftime("%Y-%m-%d")
        except Exception:
            formatted_date = row["event_time"]
        videos.append({
            "date": formatted_date,
            "url": row["video_url"],
            "type": row["type"],
            "risk_level": row["risk_level"]
        })

    conn.close()
    return videos

# profile
@app.get("/api/user/profile", response_model=UserProfile)
def get_user_profile(user_id: int = Query(..., description="User ID"), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserProfile(id=user.id, username=user.username, email=user.email)

# 알림 관련 기능
alerts: List[Alert] = []

# 알림 수신 (프론트에서 사용)
@app.post("/alerts/")
def create_alert(alert: Alert):
    alerts.append(alert)
    return {"message": "Alert received"}

# 알림 목록 조회
@app.get("/alerts/", response_model=List[Alert])
def get_alerts():
    return alerts

# 테스트용 알림 생성 엔드포인트
@app.get("/test/notify")
def test_alert():
    now = datetime.now().isoformat()
    alert = Alert(
        store="TestStore",
        camera="EntranceCam",
        event="Loitering",
        timestamp=now
    )
    alerts.append(alert)
    return {"message": "Test alert generated", "alert": alert}

# Store 등록 API
@app.post("/api/store/register", response_model=StoreResponse)
def register_store(store: StoreCreate, db: Session = Depends(get_db)):
    db_store = Store(**store.dict())
    db.add(db_store)
    db.commit()
    db.refresh(db_store)
    return db_store

class CameraCreate(BaseModel):
    user_id: int
    store_id: int
    name: str
    video_url: str
    image_url: str

    class Config:
        orm_mode = True

class Camera(Base):
    __tablename__ = "camera"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    store_id = Column(Integer, ForeignKey("store.id"), nullable=False)
    name = Column(String, nullable=False)
    video_url = Column(String, nullable=False)
    image_url = Column(String, nullable=False)

    store = relationship("Store", back_populates="cameras")

@app.post("/cameras/")
def create_camera(camera: CameraCreate, db: Session = Depends(get_db)):
    db_camera = Camera(**camera.dict())
    db.add(db_camera)
    db.commit()
    db.refresh(db_camera)
    return db_camera




# # 알림 시뮬레이션 함수: camera_event_db에서 랜덤 알림을 주기적으로 추가
# def simulate_alerts():
#     while True:
#         store = random.choice(list(camera_event_db.keys()))
#         if not camera_event_db[store]:
#             time.sleep(1)
#             continue
#         camera = random.choice(list(camera_event_db[store].keys()))
#         if not camera_event_db[store][camera]:
#             time.sleep(1)
#             continue
#         event_data = random.choice(camera_event_db[store][camera])
        
#         alert = Alert(
#             store=store,
#             camera=camera,
#             event=event_data["type"],
#             timestamp=datetime.now(timezone.utc)
#         )
#         alerts.append(alert)
#         print(f"Simulated alert: {alert}")
#         time.sleep(10)


# @app.post("/api/process_local_video", response_model=VideoProcessResponse)
# async def process_local_video(request: VideoProcessRequest):
#     """
#     로컬 네트워크 상의 영상 URL을 받아 YOLO 처리를 시작합니다.
#     """
#     local_video_url = request.video_url

#     try:
#         processed_file_path = run_yolo_on_video(local_video_url)

#         relative_path = processed_file_path.replace("static/", "/static/")

#         return VideoProcessResponse(
#             message=f"로컬 영상 '{local_video_url}' 처리 시작됨.",
#             processed_video_path=relative_path
#         )
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"영상 처리 중 오류 발생: {str(e)}")


# # videos 디렉토리가 없으면 생성
# if not os.path.exists("videos"):
#     os.makedirs("videos")
# # 1. 원본 영상 및 썸네일 파일을 제공하기 위한 마운트 추가
# app.mount("/videos", StaticFiles(directory="videos"), name="videos")


# # static/clips 디렉토리가 없으면 생성
# if not os.path.exists("static/clips"):
#     os.makedirs("static/clips")
# # 2. 처리된 비디오 파일을 제공하기 위한 마운트
# app.mount("/static", StaticFiles(directory="static"), name="static")

# # # 데몬 스레드로 시뮬레이션 시작
# threading.Thread(target=simulate_alerts, daemon=True).start()