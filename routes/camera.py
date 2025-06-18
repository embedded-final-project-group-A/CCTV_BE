from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import requests
import os
import shutil
import subprocess
from dependencies.db import get_db, get_connection
from dependencies.schemas import CameraCreate, VideoInfo, CameraOut
from dependencies.models import Camera, Store, User

camera_router = APIRouter()

def sanitize_name(name: str) -> str:
    return name.lower().replace(' ', '_')

def download_file(url: str, dest: str) -> bool:
    import requests
    try:
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            with open(dest, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
        return False
    except Exception as e:
        print(f"Download failed: {e}")
        return False

@camera_router.post("/api/cameras", response_model=CameraOut)
def register_camera(camera: CameraCreate, db: Session = Depends(get_db)):
    # 사용자 및 매장 정보 조회
    user = db.query(User).filter(User.id == camera.user_id).first()
    store = db.query(Store).filter(Store.id == camera.store_id).first()
    if not user or not store:
        raise HTTPException(status_code=404, detail="User or Store not found")

    username = user.username
    storename = store.name
    cam_name = sanitize_name(camera.name)

    # ---- 폴더 경로 생성 ----
    base_path = os.path.join("videos", username, storename)
    captures_path = os.path.join(base_path, "captures")
    clips_path = os.path.join(base_path, "clips")
    output_cam_path = os.path.join("output", username, storename, cam_name)

    os.makedirs(captures_path, exist_ok=True)
    os.makedirs(clips_path, exist_ok=True)
    os.makedirs(output_cam_path, exist_ok=True)

    dest_image_path = os.path.join(captures_path, f"{cam_name}.jpg")
    dest_video_path = os.path.join(clips_path, f"{cam_name}.mp4")

    # ---- 이미지 복사 ----
    try:
        if camera.image_url.startswith("http"):
            temp_image_path = "temp_image.jpg"
            if download_file(camera.image_url, temp_image_path):
                shutil.copy2(temp_image_path, dest_image_path)
                os.remove(temp_image_path)
            else:
                print(f"Image download failed: {camera.image_url}")
        elif os.path.exists(camera.image_url):
            shutil.copy2(camera.image_url, dest_image_path)
        else:
            print(f"Image not found: {camera.image_url}")
    except Exception as e:
        print(f"Image copy error: {e}")

    # ---- 동영상 복사 ----
    try:
        if camera.video_url.startswith("http"):
            temp_video_path = "temp_video.mp4"
            if download_file(camera.video_url, temp_video_path):
                shutil.copy2(temp_video_path, dest_video_path)
                os.remove(temp_video_path)
            else:
                print(f"Video download failed: {camera.video_url}")
        elif os.path.exists(camera.video_url):
            shutil.copy2(camera.video_url, dest_video_path)
        else:
            print(f"Video not found: {camera.video_url}")
    except Exception as e:
        print(f"Video copy error: {e}")

    # ---- HTTP URL 생성 ----
    http_base = "http://localhost:8000"
    image_http_url = f"{http_base}/videos/{username}/{storename}/captures/{cam_name}.jpg"
    video_http_url = f"{http_base}/videos/{username}/{storename}/clips/{cam_name}.mp4"

    # ---- DB 저장 ----
    db_camera = Camera(
        user_id=camera.user_id,
        store_id=camera.store_id,
        name=camera.name,
        image_url=image_http_url,
        video_url=video_http_url,
    )
    db.add(db_camera)
    db.commit()
    db.refresh(db_camera)

    # ---- YOLO 실행 ----
    try:
        yolo_script_path = os.path.abspath("yolo/process_videos.py")
        subprocess.Popen([
            "python", yolo_script_path,
            "--video_dir", clips_path,
            "--output_base", output_cam_path,
            "--debug"
        ])
        print(f"YOLO process started for: {dest_video_path}")
    except Exception as e:
        print(f"Failed to start YOLO process: {e}")

    return db_camera

# 특정 매장-카메라 조합의 이벤트 정보 조회
@camera_router.get("/api/store/events", response_model=List[VideoInfo])
def get_camera_events(store: str = Query(...), camera_label: str = Query(...)):
    conn = get_connection()
    cursor = conn.cursor()

    # 매장 ID 조회
    cursor.execute("SELECT id FROM store WHERE name = ?", (store,))
    store_row = cursor.fetchone()
    if not store_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Store not found")
    store_id = store_row["id"]

    # 카메라 ID 조회
    cursor.execute("SELECT id FROM camera WHERE store_id = ? AND name = ?", (store_id, camera_label))
    cam_row = cursor.fetchone()
    if not cam_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Camera not found")
    camera_id = cam_row["id"]

    # 이벤트 조회
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
            "risk_level": row["risk_level"],
        })

    conn.close()
    return videos

# 매장 이름과 userid로 카메라 목록 조회
@camera_router.get("/api/store/cameras", response_model=List[CameraOut])
def get_cameras_by_store(
    user_id: int = Query(..., description="User ID who owns the store"),
    store: str = Query(..., description="Store name"),
    db: Session = Depends(get_db)
):
    # 1. user_id와 store 이름으로 Store 객체 찾기
    store_obj = db.query(Store).filter(Store.user_id == user_id, Store.name == store).first()
    if not store_obj:
        raise HTTPException(status_code=404, detail="Store not found or user does not own the store")

    # 2. store_id로 카메라 조회
    cameras = db.query(Camera).filter(Camera.store_id == store_obj.id).all()
    return cameras