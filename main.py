from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import List, Dict, Any
import os
from yolo_handler import run_yolo_on_video # yolo_handler.py가 동일 디렉토리에 있다고 가정
from pydantic import BaseModel

# --- Pydantic 모델 정의 ---
class VideoProcessRequest(BaseModel):
    video_url: str

class VideoProcessResponse(BaseModel):
    message: str
    processed_video_path: str = None

app = FastAPI()

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # 개발 단계에서는 "*" 허용, 실제 서비스 시에는 특정 도메인으로 제한
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
        # imageUrl 필드: 썸네일 이미지 URL
        # videoUrl 필드: 원본 영상 URL
        # label 필드: 카메라 이름
        {"label": "Store1 Main Camera", "videoUrl": "http://localhost:8000/videos/test.mp4", "imageUrl": "http://localhost:8000/videos/test_image.png"},
    ],
    "store2": [
        {"label": "Store2 Aisle Cam", "videoUrl": "http://localhost:8000/videos/test.mp4", "imageUrl": "http://localhost:8000/videos/test_image.png"},
    ],
    "store3": [
        {"label": "Store3 Exit Cam", "videoUrl": "http://localhost:8000/videos/test.mp4", "imageUrl": "http://localhost:8000/videos/test_image.png"},
    ],
    "store4": [], # store4는 현재 영상이 없다고 가정
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