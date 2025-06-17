from fastapi import BackgroundTasks, APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import os
import threading
import time
import schedule
import subprocess

from dependencies.db import get_db
from dependencies.models import Event, User, Store, Camera, EventType
from dependencies.schemas import Alert, EventCreate

events_router = APIRouter()

# Constants
BASE_OUTPUT_DIR = "output"
MIN_ALERT_INTERVAL = 1  # seconds

processed_files = set()
last_alert_time_for_auto_event = datetime.min
last_alert_lock = threading.Lock()

SERVER_START_TIME = datetime.utcnow()


@events_router.get("/api/user/alerts/", response_model=List[Alert])
def get_alerts(db: Session = Depends(get_db)):
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


@events_router.post("/api/start-detection/")
async def start_detection(store_id: int, camera_id: int, background_tasks: BackgroundTasks):
    def run_detect_script():
        try:
            subprocess.run(["python", "yolo/detect.py"], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Detection script failed: {e}")
    background_tasks.add_task(run_detect_script)
    return {"message": "Detection started"}


def send_fcm_alert(store_id: int, camera_id: int, type_id: int):
    print(f"[Alert] Store {store_id}, Camera {camera_id}, EventType {type_id} detected")


def get_ids_from_path(db: Session, video_path: str):
    parts = video_path.split(os.sep)
    if len(parts) < 3:
        print(f"Path too short for ID extraction: {video_path}")
        return None, None, None

    # output/user1/store1/...
    username = parts[1]
    store_name = parts[2]

    user = db.query(User).filter(User.username == username).first()
    if not user:
        print(f"User not found for username: {username}")
        return None, None, None

    store = db.query(Store).filter(Store.user_id == user.id, Store.name == store_name).first()
    if not store:
        print(f"Store not found for user_id={user.id} store_name={store_name}")
        return user.id, None, None

    camera = db.query(Camera).filter(Camera.store_id == store.id).first()
    if not camera:
        print(f"Camera not found for store_id={store.id}")

    return user.id, store.id, camera.id if camera else None


def process_new_video_file(db: Session, video_file_path: str):
    global last_alert_time_for_auto_event

    with last_alert_lock:
        current_time = datetime.utcnow()
        elapsed = (current_time - last_alert_time_for_auto_event).total_seconds()
        if elapsed < MIN_ALERT_INTERVAL:
            return False

    video_abs_path = os.path.abspath(video_file_path)
    if video_abs_path in processed_files:
        return False

    video_filename = os.path.basename(video_file_path)
    name_parts = video_filename.split('_')
    if len(name_parts) < 4:
        print(f"Invalid video filename format: {video_filename}")
        return False

    timestamp_str = name_parts[0]       # ex) 2025-06-18T01-47-24
    event_type = name_parts[1]          # ex) smoke
    index_str = name_parts[-1].split('.')[0]  # ex) 0

    clips_dir = os.path.dirname(video_file_path)  # .../clips
    captures_dir = clips_dir.replace("clips", "captures")
    image_filename = f"{timestamp_str}_{event_type}_capture_{index_str}.jpg"
    image_path = os.path.join(captures_dir, image_filename)

    if not os.path.exists(image_path):
        print(f"Capture image not found: {image_path}")
        return False

    video_url = f"http://localhost:8000/{video_file_path.replace(os.sep, '/')}"
    image_url = f"http://localhost:8000/{image_path.replace(os.sep, '/')}"

    try:
        user_id, store_id, camera_id = get_ids_from_path(db, video_file_path)
        if not all([user_id, store_id, camera_id]):
            print(f"Missing ID mapping for: {video_file_path} user_id={user_id}, store_id={store_id}, camera_id={camera_id}")
            return False

        existing_event = db.query(Event).filter(Event.video_url == video_url).first()
        if existing_event:
            processed_files.add(video_abs_path)
            processed_files.add(os.path.abspath(image_path))
            return False

        new_event = Event(
            user_id=user_id,
            store_id=store_id,
            camera_id=camera_id,
            type_id=1,  # 필요시 이벤트 타입 매핑 로직 추가
            event_time=current_time,
            video_url=video_url,
        )
        db.add(new_event)
        db.commit()
        db.refresh(new_event)

        processed_files.add(video_abs_path)
        processed_files.add(os.path.abspath(image_path))
        with last_alert_lock:
            last_alert_time_for_auto_event = current_time

        send_fcm_alert(store_id, camera_id, 1)
        print(f"[{current_time.strftime('%H:%M:%S')}] New event added: {new_event.id}")
        return True

    except Exception as e:
        print(f"Error processing new video file: {e}")
        db.rollback()
        return False


def scan_clips_folder():
    with next(get_db()) as db:
        for dirpath, _, filenames in os.walk(BASE_OUTPUT_DIR):
            if os.path.basename(dirpath) != "clips":
                continue
            for fname in filenames:
                if fname.endswith(".mp4"):
                    full_path = os.path.join(dirpath, fname)
                    process_new_video_file(db, full_path)


def run_scheduler():
    schedule.every(5).seconds.do(scan_clips_folder)
    print("Scheduler started. Monitoring clips folder every 5 seconds...")
    while True:
        schedule.run_pending()
        time.sleep(1)


def start_alert_scheduler():
    # 기존 mp4, jpg 절대경로로 등록
    for dirpath, _, filenames in os.walk(BASE_OUTPUT_DIR):
        for fname in filenames:
            if fname.endswith(".mp4") or fname.endswith(".jpg"):
                abs_path = os.path.abspath(os.path.join(dirpath, fname))
                processed_files.add(abs_path)

    thread = threading.Thread(target=run_scheduler, daemon=True)
    thread.start()
