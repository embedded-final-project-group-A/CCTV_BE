from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.auth import auth_router
from routes.store import store_router
from routes.camera import camera_router
from routes.alert import alert_router
from routes.user import user_router

app = FastAPI()

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