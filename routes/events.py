from fastapi import APIRouter, UploadFile, File
from database import SessionLocal
from models import Event
from yolo_handler import run_yolo_on_video
import shutil
import os

router = APIRouter()

@router.post("/upload/")
async def upload_video(file: UploadFile = File(...)):
    video_path = f"static/clips/{file.filename}"
    with open(video_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # YOLO 처리 후 저장된 영상 경로 리턴
    result_path = run_yolo_on_video(video_path)

    # DB 저장
    db = SessionLocal()
    new_event = Event(type="suspicious", video_path=result_path)
    db.add(new_event)
    db.commit()
    db.close()

    return {"message": "Processed", "path": result_path}

@router.get("/events/")
def get_events():
    db = SessionLocal()
    events = db.query(Event).all()
    db.close()
    return events
