from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import List, Dict, Any
import os
from yolo_handler import run_yolo_on_video  # yolo_handler.py가 동일 디렉토리에 있다고 가정
from pydantic import BaseModel
from datetime import datetime, timezone
import threading, time
import random

# --- Pydantic 모델 정의 ---
class VideoProcessRequest(BaseModel):
    video_url: str

class VideoProcessResponse(BaseModel):
    message: str
    processed_video_path: str = None

class VideoInfo(BaseModel):
    date: str
    type: str
    videoUrl: str

class Alert(BaseModel):
    store: str
    camera: str
    event: str
    timestamp: datetime = datetime.now(timezone.utc)

app = FastAPI()

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발 단계에서는 "*" 허용, 실제 서비스 시에는 특정 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 샘플 데이터 (DB 대신)
user_stores_db = {
    "user1": ["store1", "store2", "store3", "store4"],
    "user2": [],  # 가게 없음
    "user3": ["store4"],
}

dummy_cameras_db = {
    "store1": [
        {"label": "Store1 Main Camera", "videoUrl": "http://localhost:8000/videos/test.mp4", "imageUrl": "http://localhost:8000/videos/test_image.png"},
        {"label": "Store1 Back Camera", "videoUrl": "http://localhost:8000/videos/test.mp4", "imageUrl": "http://localhost:8000/videos/test_image.png"},
        {"label": "Store1 Entrance Cam", "videoUrl": "http://localhost:8000/videos/test.mp4", "imageUrl": "http://localhost:8000/videos/test_image.png"},
    ],
    "store2": [
        {"label": "Store2 Aisle Cam", "videoUrl": "http://localhost:8000/videos/test.mp4", "imageUrl": "http://localhost:8000/videos/test_image.png"},
    ],
    "store3": [
        {"label": "Store3 Exit Cam", "videoUrl": "http://localhost:8000/videos/test.mp4", "imageUrl": "http://localhost:8000/videos/test_image.png"},
    ],
    "store4": [],  # store4는 현재 영상이 없다고 가정
}

camera_event_db = {
    "store1": {
        "Store1 Main Camera": [
            {"date": "2023-10-01T12:00:00Z", "type": "도난", "videoUrl": "http://localhost:8000/videos/test.mp4"},
            {"date": "2023-10-01T12:05:00Z", "type": "유기", "videoUrl": "http://localhost:8000/videos/test.mp4"},
        ],
        "Store1 Back Camera": [
            {"date": "2023-10-01T12:02:00Z", "type": "폭행", "videoUrl": "http://localhost:8000/videos/test.mp4"},
        ],
        "Store1 Entrance Cam": [
            {"date": "2023-10-01T12:07:00Z", "type": "흡연", "videoUrl": "http://localhost:8000/videos/test.mp4"},
        ]
    },
    "store2": {
        "Store2 Aisle Cam": [
            {"date": "2023-10-01T12:10:00Z", "type": "폭행", "videoUrl": "http://localhost:8000/videos/test.mp4"},
        ]
    },
    "store3": {
        "Store3 Exit Cam": [
            {"date": "2023-10-01T12:15:00Z", "type": "흡연", "videoUrl": "http://localhost:8000/videos/test.mp4"},
        ]
    },
    "store4": {}
}

@app.get("/api/user/stores", response_model=List[str])
async def get_user_stores(user_id: str = Query(..., description="사용자 ID")):
    stores = user_stores_db.get(user_id)
    if stores is None:
        raise HTTPException(status_code=404, detail="User not found")
    return stores


@app.get("/api/store/cameras", response_model=List[Dict[str, Any]])
async def get_store_cameras(store: str = Query(..., description="매장 이름")):
    """
    특정 매장에 대한 카메라 목록을 반환합니다.
    """
    cameras = dummy_cameras_db.get(store)
    if cameras is None:
        return []
    return cameras


@app.get("/api/store/events", response_model=List[VideoInfo])
async def get_camera_events(store: str = Query(...), camera_label: str = Query(...)):
    """
    특정 매장과 카메라 라벨에 대한 이벤트(이상행동 영상) 목록을 반환합니다.
    """
    store_cameras = camera_event_db.get(store)
    if store_cameras is None:
        raise HTTPException(status_code=404, detail="Store not found")

    videos = store_cameras.get(camera_label, [])
    
    # 날짜를 yyyy-mm-dd 형식으로 변환
    for video in videos:
        if "date" in video:
            try:
                dt = datetime.fromisoformat(video["date"].replace("Z", "+00:00"))
                video["date"] = dt.strftime("%Y-%m-%d")
            except Exception:
                pass

    return videos

alerts: List[Alert] = []

@app.post("/alerts/")
async def create_alert(alert: Alert):
    alerts.append(alert)
    return {"message": "Alert received"}

@app.get("/alerts/", response_model=List[Alert])
async def get_alerts():
    return alerts

# 알림 시뮬레이션 함수: camera_event_db에서 랜덤 알림을 주기적으로 추가
def simulate_alerts():
    while True:
        store = random.choice(list(camera_event_db.keys()))
        if not camera_event_db[store]:
            time.sleep(1)
            continue
        camera = random.choice(list(camera_event_db[store].keys()))
        if not camera_event_db[store][camera]:
            time.sleep(1)
            continue
        event_data = random.choice(camera_event_db[store][camera])
        
        alert = Alert(
            store=store,
            camera=camera,
            event=event_data["type"],
            timestamp=datetime.now(timezone.utc)
        )
        alerts.append(alert)
        print(f"Simulated alert: {alert}")
        time.sleep(10)


@app.post("/api/process_local_video", response_model=VideoProcessResponse)
async def process_local_video(request: VideoProcessRequest):
    """
    로컬 네트워크 상의 영상 URL을 받아 YOLO 처리를 시작합니다.
    """
    local_video_url = request.video_url

    try:
        processed_file_path = run_yolo_on_video(local_video_url)

        relative_path = processed_file_path.replace("static/", "/static/")

        return VideoProcessResponse(
            message=f"로컬 영상 '{local_video_url}' 처리 시작됨.",
            processed_video_path=relative_path
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"영상 처리 중 오류 발생: {str(e)}")


# videos 디렉토리가 없으면 생성
if not os.path.exists("videos"):
    os.makedirs("videos")
# 1. 원본 영상 및 썸네일 파일을 제공하기 위한 마운트 추가
app.mount("/videos", StaticFiles(directory="videos"), name="videos")


# static/clips 디렉토리가 없으면 생성
if not os.path.exists("static/clips"):
    os.makedirs("static/clips")
# 2. 처리된 비디오 파일을 제공하기 위한 마운트
app.mount("/static", StaticFiles(directory="static"), name="static")

# 데몬 스레드로 시뮬레이션 시작
threading.Thread(target=simulate_alerts, daemon=True).start()