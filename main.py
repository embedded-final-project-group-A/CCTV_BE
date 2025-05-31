# CCTV_BE/main.py (최종 수정본)
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import uvicorn
import threading
import time
import os
import glob
import schedule # <--- 추가
from datetime import datetime, timedelta

from dependencies.db import get_db, Base, engine
from dependencies.models import Event, EventType, User, Store, Camera # <--- EventType도 임포트
from fastapi.middleware.cors import CORSMiddleware
from routes.auth import auth_router
from routes.store import store_router
from routes.camera import camera_router
from routes.alert import alert_router
from routes.user import user_router
from routes.events import router as events_router

# 데이터베이스 테이블 생성 (서비스 시작 시 스키마 확인 및 생성)
Base.metadata.create_all(bind=engine)

app = FastAPI()

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(auth_router)
app.include_router(store_router)
app.include_router(camera_router)
app.include_router(alert_router)
app.include_router(user_router)
app.include_router(events_router)

# Static 파일 서빙 (output 폴더 포함)
# `videos` 폴더와 `output` 폴더는 웹 서버를 통해 직접 접근 가능해야 합니다.
app.mount("/videos", StaticFiles(directory="videos"), name="videos")
app.mount("/output", StaticFiles(directory="output"), name="output")

# --- Output 폴더 감시 및 알림 전송 로직 ---

# 감시할 폴더 경로 (CCTV_BE 디렉토리 기준)
OUTPUT_CAPTURES_DIR = "output/captures"
OUTPUT_CLIPS_DIR = "output/clips"

# 이미 처리된 파일들을 추적하기 위한 집합 (중복 알림 방지)
processed_files = set()

# 알림 간 최소 시간 간격 (초 단위) - 너무 많은 알림 방지
MIN_ALERT_INTERVAL = 5 # 5초에 한 번만 알림을 보내도록 설정
last_alert_time_for_auto_event = datetime.min # 자동 이벤트 마지막 알림 시간

# 파일을 처리하고 DB에 알림을 보내는 함수
def process_new_output_file(db: Session, file_path: str):
    global last_alert_time_for_auto_event
    
    current_time = datetime.now()
    if (current_time - last_alert_time_for_auto_event).total_seconds() < MIN_ALERT_INTERVAL:
        # print(f"[{datetime.now().strftime('%H:%M:%S')}] Auto event creation interval not met. Skipping.")
        return False # 알림 간격 미충족 시 처리 중단

    filename = os.path.basename(file_path)
    
    # 이미 처리된 파일인지 확인
    if filename in processed_files:
        return False

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Processing new file: {file_path}")

    # 파일 이름 패턴을 기반으로 연관된 이미지/클립 경로 추론
    # detect.py가 'helmet_capture_N.jpg'와 'helmet_clip_N.mp4'를 생성한다고 가정합니다.
    name_parts = filename.split('_')
    if len(name_parts) < 3:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Skipping file with unexpected name pattern: {filename}")
        return False

    event_prefix = name_parts[0] # 'helmet'
    index_str = name_parts[-1].split('.')[0] # '0', '1', '2' 등

    image_file_name = None
    video_file_name = None

    if 'capture' in filename: # 이미지 파일이 생성되었을 경우
        image_file_name = filename
        # 해당 이미지에 상응하는 비디오 클립 찾기
        video_pattern = f"{event_prefix}_clip_{index_str}.mp4"
        potential_video_paths = glob.glob(os.path.join(OUTPUT_CLIPS_DIR, video_pattern))
        if potential_video_paths:
            video_file_name = os.path.basename(potential_video_paths[0])
    elif 'clip' in filename: # 비디오 파일이 생성되었을 경우 (일반적으로 이미지가 먼저 생성되므로 이 경우는 백업 로직)
        video_file_name = filename
        # 해당 비디오에 상응하는 이미지 캡처 찾기
        image_pattern = f"{event_prefix}_capture_{index_str}.jpg"
        potential_image_paths = glob.glob(os.path.join(OUTPUT_CAPTURES_DIR, image_pattern))
        if potential_image_paths:
            image_file_name = os.path.basename(potential_image_paths[0])
            
    if not image_file_name or not video_file_name:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Could not find matching image/video for {filename}. Waiting for both.")
        return False # 둘 중 하나라도 없으면 아직 처리하지 않음

    # 백엔드에 전송할 URL 생성 (FastAPI의 StaticFiles 마운트 경로와 일치해야 함)
    image_url_for_backend = f"http://localhost:8000/output/captures/{image_file_name}"
    video_url_for_backend = f"http://localhost:8000/output/clips/{video_file_name}"

    # 데이터베이스에 이벤트 저장
    try:
        # test_db.py에 있는 'testuser1', 'store1', 'Main Camera'와 매칭되는지 확인
        user = db.query(User).filter(User.username == "testuser1").first()
        store = db.query(Store).filter(Store.name == "store1", Store.user_id == user.id).first()
        camera = db.query(Camera).filter(Camera.name == "Main Camera", Camera.user_id == user.id, Camera.store_id == store.id).first()
        event_type = db.query(EventType).filter(EventType.type == "theft").first() # <--- 'theft' 타입으로 고정

        if not all([user, store, camera, event_type]):
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Missing required data (user, store, camera, event_type). Ensure test_db.py created them.")
            return False

        # 기존에 동일한 이미지 URL로 저장된 이벤트가 있는지 확인하여 중복 방지
        existing_event = db.query(Event).filter(Event.image_url == image_url_for_backend).first()
        if existing_event:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Event for {image_url_for_backend} already exists. Skipping.")
            processed_files.add(image_file_name) # 이미 처리된 것으로 추가
            processed_files.add(video_file_name) # 이미 처리된 것으로 추가
            return False

        new_event = Event(
            user_id=user.id,
            store_id=store.id,
            camera_id=camera.id,
            type_id=event_type.id,
            event_time=datetime.now(), # 현재 시간으로 설정
            video_url=video_url_for_backend,
            image_url=image_url_for_backend
        )
        db.add(new_event)
        db.commit()
        db.refresh(new_event)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Event (Type: theft) recorded to DB: {new_event.id}")
        
        # 처리된 파일 목록에 추가
        processed_files.add(image_file_name)
        processed_files.add(video_file_name)
        last_alert_time_for_auto_event = current_time # 알림 성공 시 시간 업데이트

        return True

    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Error saving event to DB: {e}")
        db.rollback() # 에러 발생 시 롤백
        return False

# output 폴더를 주기적으로 스캔하는 함수
def scan_output_folder():
    db = next(get_db()) # DB 세션 가져오기
    try:
        # captures 폴더 스캔
        for file_path in glob.glob(os.path.join(OUTPUT_CAPTURES_DIR, "*.jpg")):
            process_new_output_file(db, file_path)
        
        # clips 폴더 스캔 (혹시 비디오가 먼저 생성될 경우를 대비)
        for file_path in glob.glob(os.path.join(OUTPUT_CLIPS_DIR, "*.mp4")):
            process_new_output_file(db, file_path)
    finally:
        db.close() # DB 세션 닫기

# 백그라운드 스케줄러 실행 함수
def run_scheduler():
    # 5초마다 output 폴더 스캔
    schedule.every(5).seconds.do(scan_output_folder)
    print("Background scheduler started, scanning output folder every 5 seconds...")
    while True:
        schedule.run_pending()
        time.sleep(1)

# FastAPI 앱 시작 시 스케줄러 스레드 시작
@app.on_event("startup")
async def startup_event():
    # 필요한 경우, 이미 존재하는 파일들을 processed_files에 초기화하여 중복 처리 방지
    # (서버 재시작 시 이미 존재하는 파일들이 재처리되는 것을 막음)
    # 서버 시작 전에 output 폴더에 이미 있던 파일들은 무시합니다.
    for folder in [OUTPUT_CAPTURES_DIR, OUTPUT_CLIPS_DIR]:
        if os.path.exists(folder): # 폴더가 없을 경우를 대비
            for file_path in glob.glob(os.path.join(folder, "*")):
                processed_files.add(os.path.basename(file_path))
    
    # 백그라운드 스레드 시작
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()

# FastAPI 앱 실행 (uvicorn main:app --reload)
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)