from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List

app = FastAPI()

# CORS 설정 (Flutter에서 호출할 경우)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 실제 서비스 시에는 도메인 제한 필요
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 샘플 데이터 (DB 대신)
user_stores_db = {
    "user1": ["store1", "store2", "store3", "store4"],
    "user2": [],  # 가게 없음
    "user3": ["store4"],
}

@app.get("/api/user/stores", response_model=List[str])
async def get_user_stores(user_id: str = Query(..., description="사용자 ID")):
    stores = user_stores_db.get(user_id)
    if stores is None:
        raise HTTPException(status_code=404, detail="User not found")
    return stores
