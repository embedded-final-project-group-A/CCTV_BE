from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.auth import auth_router
from routes.store import store_router
from routes.camera import camera_router
from routes.alert import alert_router
from routes.user import user_router
from fastapi.staticfiles import StaticFiles
from routes.events import router as events_router

app = FastAPI()

# 정적 파일(동영상) 경로 설정
app.mount("/videos", StaticFiles(directory="videos"), name="videos")
app.mount("/output", StaticFiles(directory="output"), name="output")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(auth_router)
app.include_router(store_router)
app.include_router(camera_router)
app.include_router(alert_router)
app.include_router(user_router)
app.include_router(events_router)