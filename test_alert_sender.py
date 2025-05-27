import requests
import random
import time
from datetime import datetime

API_URL = "http://localhost:8000/alerts/"

stores = ["StoreA", "StoreB", "StoreC"]
cameras = ["Cam1", "Cam2", "Entrance", "Backdoor"]
events = ["Intrusion detected", "Fire detected", "Suspicious movement", "Glass break"]

def send_fake_alert():
    store = random.choice(stores)
    camera = random.choice(cameras)
    event = random.choice(events)
    timestamp = datetime.utcnow().isoformat()

    alert = {
        "camera_id": random.randint(1, 10),
        "message": f"{store} - {camera}: {event}",
        "timestamp": timestamp,
    }

    response = requests.post(API_URL, json=alert)
    print(f"Sent: {alert} | Response: {response.status_code}")

if __name__ == "__main__":
    while True:
        send_fake_alert()
        time.sleep(10)  # 10초마다 알림 전송
