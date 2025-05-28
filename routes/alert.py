from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from dependencies.models import Event
from dependencies.db import get_db
from datetime import datetime
from firebase_admin import messaging
from dependencies.schemas import Alert, EventCreate
from typing import List, Optional

alert_router = APIRouter()

@alert_router.get("/api/user/alerts/", response_model=List[Alert])
def get_alerts(db: Session = Depends(get_db)):
    events = db.query(Event).order_by(Event.event_time.desc()).all()
    # Event 객체 리스트 → Alert 모델 리스트 변환
    alert_list = [Alert.from_orm(event) for event in events]
    print(f"Converted alerts: {alert_list}")
    return alert_list

@alert_router.post("/api/user/alerts/")
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

def send_fcm_alert(store_id: str, camera_id: int, type_id: int):
    notification = messaging.Message(
        notification=messaging.Notification(
            title=f"New Event - Store {store_id}",
            body=f"Camera {camera_id}: Event Type {type_id} detected"
        ),
        topic="alerts"
    )
    response = messaging.send(notification)
    print("Push notification sent:", response)
