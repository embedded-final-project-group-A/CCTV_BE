from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dependencies.db import Base, engine
import uvicorn

from routes.auth import auth_router
from routes.store import store_router
from routes.camera import camera_router
from routes.user import user_router
from routes.events import events_router

# DB 테이블 생성
Base.metadata.create_all(bind=engine)

app = FastAPI()

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static 파일
app.mount("/videos", StaticFiles(directory="videos"), name="videos")
app.mount("/output", StaticFiles(directory="output"), name="output")

# 라우터 등록
app.include_router(auth_router)
app.include_router(store_router)
app.include_router(camera_router)
app.include_router(user_router)
app.include_router(events_router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
