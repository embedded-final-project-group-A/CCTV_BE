from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import os
import glob
import threading
import time
import schedule

from firebase_admin import messaging

from dependencies.db import get_db
from dependencies.models import Event, User, Store, Camera, EventType
from dependencies.schemas import Alert, EventCreate

events_router = APIRouter()

# Constantsc
OUTPUT_CAPTURES_DIR = "output/captures"
OUTPUT_CLIPS_DIR = "output/clips"
processed_files = set()
MIN_ALERT_INTERVAL = 1
last_alert_time_for_auto_event = datetime.min

# 서버 시작 시점 저장 (이 모듈 import 시 한번만)
SERVER_START_TIME = datetime.utcnow()

@events_router.get("/api/user/alerts/", response_model=List[Alert])
def get_alerts(db: Session = Depends(get_db)):
    # 서버 시작 이후 생성된 이벤트만 반환하여 과거 알림 제외
    events = (
        db.query(Event)
        .filter(Event.event_time >= SERVER_START_TIME)
        .order_by(Event.event_time.desc())
        .all()
    )
    return [Alert.from_orm(event) for event in events]

@events_router.post("/api/user/alerts/")
def create_event(event_data: EventCreate, db: Session = Depends(get_db)):
    event = Event(
        user_id=event_data.user_id,
        store_id=event_data.store_id,
        camera_id=event_data.camera_id,
        type_id=event_data.type_id,
        event_time=datetime.utcnow(),
        video_url=event_data.video_url
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    send_fcm_alert(event_data.store_id, event_data.camera_id, event_data.type_id)
    return {"message": "Event saved and alert sent"}

def send_fcm_alert(store_id: int, camera_id: int, type_id: int):
    # Firebase 알림 대신 로그만 출력
    print(f"[Alert] Store {store_id}, Camera {camera_id}, EventType {type_id} detected")

def process_new_video_file(db: Session, video_file_path: str):
    global last_alert_time_for_auto_event

    current_time = datetime.utcnow()
    if (current_time - last_alert_time_for_auto_event).total_seconds() < MIN_ALERT_INTERVAL:
        return False

    video_filename = os.path.basename(video_file_path)
    if video_filename in processed_files:
        return False

    # 영상 파일명에서 event_prefix와 index 추출 (예: theft_clip_123.mp4 -> theft, 123)
    name_parts = video_filename.split('_')
    if len(name_parts) < 3:
        return False
    event_prefix = name_parts[0]
    index_str = name_parts[-1].split('.')[0]

    # 매칭하는 이미지 파일명 생성
    image_filename = f"{event_prefix}_capture_{index_str}.jpg"
    image_path = os.path.join(OUTPUT_CAPTURES_DIR, image_filename)
    if not os.path.exists(image_path):
        return False  # 이미지가 존재하지 않으면 처리하지 않음

    video_url = f"http://localhost:8000/output/clips/{video_filename}"
    image_url = f"http://localhost:8000/output/captures/{image_filename}"

    try:
        user_id = 1
        store_id = 1
        camera_id = 1
        type_id = 1  # 고정 event_type id

        # 중복 이벤트 체크: 동일 video_url 존재 여부
        existing_event = db.query(Event).filter(Event.video_url == video_url).first()
        if existing_event:
            processed_files.add(video_filename)
            processed_files.add(image_filename)
            return False

        new_event = Event(
            user_id=user_id,
            store_id=store_id,
            camera_id=camera_id,
            type_id=type_id,
            event_time=current_time,
            video_url=video_url,
        )
        db.add(new_event)
        db.commit()
        db.refresh(new_event)

        processed_files.add(video_filename)
        processed_files.add(image_filename)
        last_alert_time_for_auto_event = current_time

        send_fcm_alert(store_id, camera_id, type_id)

        print(f"[{current_time.strftime('%H:%M:%S')}] New event added: {new_event.id}")
        return True

    except Exception as e:
        print(f"Error processing new video file: {e}")
        db.rollback()
        return False

def scan_clips_folder():
    db = next(get_db())
    try:
        video_files = glob.glob(os.path.join(OUTPUT_CLIPS_DIR, "*.mp4"))
        for video_path in video_files:
            process_new_video_file(db, video_path)
    finally:
        db.close()

def run_scheduler():
    schedule.every(5).seconds.do(scan_clips_folder)
    print("Scheduler started. Monitoring clips folder every 5 seconds...")
    while True:
        schedule.run_pending()
        time.sleep(1)

def start_alert_scheduler():
    # 서버 시작 시 기존 파일들 processed_files에 등록해서 알림 제외
    for file_path in glob.glob(os.path.join(OUTPUT_CLIPS_DIR, "*.mp4")):
        processed_files.add(os.path.basename(file_path))
    for file_path in glob.glob(os.path.join(OUTPUT_CAPTURES_DIR, "*.jpg")):
        processed_files.add(os.path.basename(file_path))

    thread = threading.Thread(target=run_scheduler, daemon=True)
    thread.start()
