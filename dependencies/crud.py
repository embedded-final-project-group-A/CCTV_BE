from sqlalchemy.orm import Session
from models import Camera
from schemas import CameraCreate

def create_camera(db: Session, camera: CameraCreate):
    video_url = camera.camera_url + ".mp4"
    image_url = camera.camera_url + ".png"
    db_camera = Camera(
        user_id=camera.user_id,
        store_id=camera.store_id,
        name=camera.name,
        video_url=video_url,
        image_url=image_url
    )
    db.add(db_camera)
    db.commit()
    db.refresh(db_camera)
    return db_camera
