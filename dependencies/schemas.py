from pydantic import BaseModel, EmailStr
from typing import List, Dict, Any

class SignUpModel(BaseModel):
    username: str
    email: EmailStr
    password: str

class SignInRequest(BaseModel):
    identifier: str
    password: str

class UserProfile(BaseModel):
    id: int
    username: str
    email: EmailStr

class StoreCreate(BaseModel):
    user_id: int
    name: str
    location: str

class StoreResponse(BaseModel):
    id: int
    user_id: int
    name: str
    location: str
    class Config:
        orm_mode = True

class CameraCreate(BaseModel):
    user_id: int
    store_id: int
    name: str
    video_url: str
    image_url: str

class CameraOut(BaseModel):
    id: int
    user_id: int
    store_id: int
    name: str
    video_url: str
    image_url: str

    class Config:
        from_attributes = True

class VideoInfo(BaseModel):
    date: str
    url: str
    type: str
    risk_level: str

class Alert(BaseModel):
    store_id: str
    camera_id: int
    message: str
    timestamp: str
