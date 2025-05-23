from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles # StaticFiles 임포트
from typing import List, Dict, Any # Dict도 임포트 필요, Any 추가 (videoUrl 때문에)
import os
from yolo_handler import run_yolo_on_video # yolo_handler.py가 동일 디렉토리에 있다고 가정
from pydantic import BaseModel

# --- Pydantic 모델 정의 ---
class VideoProcessRequest(BaseModel):
    video_url: str # 'url' 대신 'video_url'로 키 변경 (명확성을 위함)

class VideoProcessResponse(BaseModel):
    message: str
    processed_video_path: str = None # 처리된 영상 경로 (상대 경로)

app = FastAPI()

# CORS 설정 (Flutter에서 호출할 경우)
# 모든 origins 허용 (개발 단계에서 편리하지만, 실제 서비스 시에는 도메인 제한 필수)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
        # test.mp4 파일을 store1의 첫 번째 카메라 영상으로 지정합니다.
        {"label": "Store1 Main Camera", "videoUrl": "http://localhost:8000/videos/test.mp4"},
        # 만약 다른 영상 파일이 더 있다면 여기에 추가할 수 있습니다.
        # 예: {"label": "Store1 Entrance Cam", "videoUrl": "http://localhost:8000/videos/another_video.mp4"},
    ],
    "store2": [
        # store2에는 다른 영상 (예: test2.mp4)을 넣거나, test.mp4를 공유해도 됩니다.
        {"label": "Store2 Aisle Cam", "videoUrl": "http://localhost:8000/videos/test.mp4"},
    ],
    "store3": [
        {"label": "Store3 Exit Cam", "videoUrl": "http://localhost:8000/videos/test.mp4"},
    ],
    "store4": [], # store4는 현재 영상이 없다고 가정
}


@app.get("/api/user/stores", response_model=List[str])
async def get_user_stores(user_id: str = Query(..., description="사용자 ID")):
    stores = user_stores_db.get(user_id)
    if stores is None:
        raise HTTPException(status_code=404, detail="User not found")
    return stores

# 새로 추가된 API 엔드포인트: 특정 매장에 대한 카메라 목록 반환
# response_model을 List[Dict[str, Any]]로 변경하여 videoUrl (str)이 아닌 다른 타입도 허용
@app.get("/api/store/cameras", response_model=List[Dict[str, Any]])
async def get_store_cameras(store: str = Query(..., description="매장 이름")):
    """
    특정 매장에 대한 카메라 목록을 반환합니다.
    """
    cameras = dummy_cameras_db.get(store)
    if cameras is None:
        # 해당 스토어에 카메라 데이터가 없으면 빈 리스트를 반환하여 Flutter 앱에서 처리하기 용이하게 합니다.
        return []
    return cameras

# --- 기존 API 엔드포인트: 로컬 영상 URL 처리 ---
@app.post("/api/process_local_video", response_model=VideoProcessResponse)
async def process_local_video(request: VideoProcessRequest):
    """
    로컬 네트워크 상의 영상 URL을 받아 YOLO 처리를 시작합니다.
    """
    local_video_url = request.video_url

    try:
        # yolo_handler.py의 run_yolo_on_video 함수에 직접 URL을 전달합니다.
        # OpenCV (cv2.VideoCapture)는 대부분의 경우 HTTP/RTSP 스트림 URL을 처리할 수 있습니다.
        processed_file_path = run_yolo_on_video(local_video_url)

        # processed_file_path는 static/clips/UUID.mp4 형태일 것입니다.
        # 프론트엔드에서 접근할 수 있도록 상대 경로를 반환합니다.
        # (예: /static/clips/UUID.mp4)
        relative_path = processed_file_path.replace("static/", "/static/")

        return VideoProcessResponse(
            message=f"로컬 영상 '{local_video_url}' 처리 시작됨.",
            processed_video_path=relative_path
        )
    except Exception as e:
        # 영상 스트림 접근 실패, YOLO 처리 중 오류 등 예외 처리
        raise HTTPException(status_code=500, detail=f"영상 처리 중 오류 발생: {str(e)}")

# videos 디렉토리가 없으면 생성
if not os.path.exists("videos"):
    os.makedirs("videos")
# 1. 원본 영상 파일을 제공하기 위한 마운트 추가
app.mount("/videos", StaticFiles(directory="videos"), name="videos")


# static/clips 디렉토리가 없으면 생성
if not os.path.exists("static/clips"):
    os.makedirs("static/clips")
# 2. 처리된 비디오 파일을 제공하기 위한 마운트
app.mount("/static", StaticFiles(directory="static"), name="static")