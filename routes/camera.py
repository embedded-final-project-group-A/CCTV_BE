from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import requests
from PIL import Image
import os

from dependencies.db import get_db, get_connection
from dependencies.schemas import CameraCreate, VideoInfo, CameraOut
from dependencies.models import Camera, Store, User

camera_router = APIRouter()

def sanitize_name(name: str) -> str:
    return name.lower().replace(' ', '_')

import subprocess

def sanitize_name(name: str) -> str:
    return "".join(c for c in name if c.isalnum() or c in (' ', '_', '-')).rstrip()

def download_file(url, dest_path):
    try:
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            with open(dest_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=1024):
                    f.write(chunk)
            return True
    except Exception as e:
        print(f"Download error: {e}")
    return False

@camera_router.post("/api/cameras", response_model=CameraOut)
def register_camera(camera: CameraCreate, db: Session = Depends(get_db)):
    # DB 저장
    db_camera = Camera(**camera.dict())
    db.add(db_camera)
    db.commit()
    db.refresh(db_camera)

    # 사용자명, 매장명 조회
    user = db.query(User).filter(User.id == camera.user_id).first()
    store = db.query(Store).filter(Store.id == camera.store_id).first()
    if not user or not store:
        raise HTTPException(status_code=404, detail="User or Store not found")

    username = user.username
    storename = store.name

    # 폴더 경로 생성
    base_path = os.path.join("videos", username, storename)
    captures_path = os.path.join(base_path, "captures")
    clips_path = os.path.join(base_path, "clips")
    os.makedirs(captures_path, exist_ok=True)
    os.makedirs(clips_path, exist_ok=True)

    # 파일 이름 처리
    cam_name = sanitize_name(camera.name)
    dest_video_path = os.path.join(clips_path, f"{cam_name}.mp4")
    dest_image_path = os.path.join(captures_path, f"{cam_name}.jpg")

    # ---- 이미지 처리 ----
    try:
        temp_image_path = "temp_image.jpg"
        if camera.image_url.startswith("http"):
            if download_file(camera.image_url, temp_image_path):
                with Image.open(temp_image_path) as img:
                    img.convert("RGB").save(dest_image_path, "JPEG")
        elif os.path.exists(camera.image_url):
            with Image.open(camera.image_url) as img:
                img.convert("RGB").save(dest_image_path, "JPEG")
        else:
            print(f"Image not found: {camera.image_url}")
    except Exception as e:
        print(f"Image error: {e}")

    # ---- 비디오 처리 ----
    try:
        temp_video_path = "temp_video.mp4"
        input_video_path = ""

        if camera.video_url.startswith("http"):
            if download_file(camera.video_url, temp_video_path):
                input_video_path = temp_video_path
        elif os.path.exists(camera.video_url):
            input_video_path = camera.video_url
        else:
            print(f"Video not found: {camera.video_url}")

        if input_video_path:
            cmd = [
                "ffmpeg", "-y", "-i", input_video_path,
                "-vcodec", "libx264", "-profile:v", "baseline",
                "-level", "3.0", "-pix_fmt", "yuv420p",
                "-acodec", "aac", "-strict", "experimental",
                dest_video_path
            ]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode != 0:
                print(f"FFmpeg error: {result.stderr.decode()}")

    except Exception as e:
        print(f"Video encoding error: {e}")

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