from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# CORS 허용 (Flutter 앱이 다른 포트/도메인에서 접근 가능하도록)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 실제 운영 시 도메인 제한 권장
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/youtube_link")
async def get_youtube_link():
    return {"youtube_url": "https://www.youtube.com/watch?v=rTQqrmhXgv8"}
