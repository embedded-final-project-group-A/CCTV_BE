from fastapi import APIRouter
from dependencies.schemas import Alert
from typing import List
from datetime import datetime

alert_router = APIRouter()

alerts: List[Alert] = []

@alert_router.post("/alerts/")
def create_alert(alert: Alert):
    alerts.append(alert)
    return {"message": "Alert received"}

@alert_router.get("/alerts/", response_model=List[Alert])
def get_alerts():
    return alerts

@alert_router.get("/test/notify")
def test_alert():
    now = datetime.now().isoformat()
    alert = Alert(
        store_id="TestStore",
        camera_id=999,
        message="Test event",
        timestamp=now
    )
    alerts.append(alert)
    return {"message": "Test alert generated", "alert": alert}