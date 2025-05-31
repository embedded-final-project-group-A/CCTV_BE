from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from dependencies.db import get_db, get_connection
from dependencies.schemas import CameraCreate, VideoInfo, CameraOut
from dependencies.models import Camera, Store

camera_router = APIRouter()


# 📌 카메라 등록
@camera_router.post("/api/cameras", response_model=CameraOut)
def register_camera(camera: CameraCreate, db: Session = Depends(get_db)):
    db_camera = Camera(**camera.dict())
    db.add(db_camera)
    db.commit()
    db.refresh(db_camera)
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
