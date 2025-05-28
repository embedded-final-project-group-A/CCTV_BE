from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from dependencies.db import get_db, get_connection
from dependencies.schemas import StoreCreate, StoreResponse
from dependencies.models import Store
from typing import List

store_router = APIRouter()

@store_router.get("/api/user/stores", response_model=List[str])
def get_user_stores(user_id: str = Query(...)):
    print(f"Received user_id: {user_id}")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM store WHERE user_id = ?", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    print(f"Rows fetched: {rows}")
    if not rows:
        raise HTTPException(status_code=404, detail="User not found or no stores")
    return [row["name"] for row in rows]

@store_router.get("/api/user/stores/detail")
def get_user_stores_detail(user_id: str = Query(...)):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM store WHERE user_id = ?", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        raise HTTPException(status_code=404, detail="User not found or no stores")
    return [{"id": row["id"], "name": row["name"]} for row in rows]

@store_router.post("/api/store/register", response_model=StoreResponse)
def register_store(store: StoreCreate, db: Session = Depends(get_db)):
    db_store = Store(**store.dict())
    db.add(db_store)
    db.commit()
    db.refresh(db_store)
    return db_store