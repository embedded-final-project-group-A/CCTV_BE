from fastapi import APIRouter, Depends, Request, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import os, time, threading, schedule, subprocess

from dependencies.db import get_db
from dependencies.models import Event, User, Store, Camera, EventType
from dependencies.schemas import Alert, EventCreate

BASE_OUTPUT_DIR = "output"
MIN_ALERT_INTERVAL = 1
processed_files = set()
last_alert_time_for_auto_event = datetime.min
last_alert_lock = threading.Lock()

user_last_login_time = {}
events_router = APIRouter()

@events_router.get("/api/user/alerts/", response_model=List[Alert])
def get_alerts(request: Request, db: Session = Depends(get_db)):
    user_id = int(request.query_params.get("user_id", 0))
    if user_id not in user_last_login_time:
        raise HTTPException(status_code=401, detail="Please login first to view alerts.")

    login_time = user_last_login_time[user_id]
    events = (
        db.query(Event)
        .filter(Event.user_id == user_id)
        .filter(Event.event_time >= login_time)
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
        return None, None, None
    username = parts[1]
    store_name = parts[2]
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return None, None, None
    store = db.query(Store).filter(Store.user_id == user.id, Store.name == store_name).first()
    if not store:
        return user.id, None, None
    camera = db.query(Camera).filter(Camera.store_id == store.id).first()
    return user.id, store.id, camera.id if camera else None

def process_new_video_file(db: Session, video_file_path: str):
    global last_alert_time_for_auto_event
    with last_alert_lock:
        current_time = datetime.utcnow()
        if (current_time - last_alert_time_for_auto_event).total_seconds() < MIN_ALERT_INTERVAL:
            return False

    abs_path = os.path.abspath(video_file_path)
    if abs_path in processed_files:
        return False

    fname = os.path.basename(video_file_path)
    name_parts = fname.split('_')
    if len(name_parts) < 4:
        print(f"[process_new_video_file] Unexpected filename format (less than 4 parts): {fname}")
        return False

    try:
        # 안전하게 필요한 부분만 추출
        timestamp_str = name_parts[0]
        event_type = name_parts[1]
        idx_ext = name_parts[-1]
        index_str = idx_ext.split('.')[0]

        event_type_map = {"theft": 1, "fall": 2, "fight": 3, "smoke": 4}
        type_id = event_type_map.get(event_type.lower())
        if not type_id:
            print(f"[process_new_video_file] Unknown event type: {event_type}")
            return False

        clips_dir = os.path.dirname(video_file_path)
        captures_dir = clips_dir.replace("clips", "captures")
        image_filename = f"{timestamp_str}_{event_type}_capture_{index_str}.jpg"
        image_path = os.path.join(captures_dir, image_filename)

        if not os.path.exists(image_path):
            print(f"[process_new_video_file] Capture image not found: {image_path}")
            return False

        video_url = f"http://localhost:8000/{video_file_path.replace(os.sep, '/')}"
        image_url = f"http://localhost:8000/{image_path.replace(os.sep, '/')}"

        user_id, store_id, camera_id = get_ids_from_path(db, video_file_path)
        if not all([user_id, store_id, camera_id]):
            print(f"[process_new_video_file] Failed to get IDs from path: {video_file_path}")
            return False

        existing_event = db.query(Event).filter(Event.video_url == video_url).first()
        if existing_event:
            processed_files.add(abs_path)
            processed_files.add(os.path.abspath(image_path))
            return False

        new_event = Event(
            user_id=user_id,
            store_id=store_id,
            camera_id=camera_id,
            type_id=type_id,
            event_time=datetime.utcnow(),
            video_url=video_url,
        )
        db.add(new_event)
        db.commit()
        db.refresh(new_event)

        processed_files.add(abs_path)
        processed_files.add(os.path.abspath(image_path))

        with last_alert_lock:
            last_alert_time_for_auto_event = datetime.utcnow()

        send_fcm_alert(store_id, camera_id, type_id)
        return True

    except Exception as e:
        print(f"[process_new_video_file] Error processing new video file: {e}")
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
    while True:
        schedule.run_pending()
        time.sleep(1)

def start_alert_scheduler(user_id: int, username: str):
    user_output_dir = os.path.join(BASE_OUTPUT_DIR, username)
    if not os.path.exists(user_output_dir):
        print(f"Output dir not found for user {username}, skipping processed_files init")
    else:
        for dirpath, _, filenames in os.walk(user_output_dir):
            for fname in filenames:
                if fname.endswith(".mp4") or fname.endswith(".jpg"):
                    abs_path = os.path.abspath(os.path.join(dirpath, fname))
                    processed_files.add(abs_path)

    thread = threading.Thread(target=run_scheduler, daemon=True)
    thread.start()

