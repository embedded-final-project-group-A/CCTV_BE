from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from dependencies.db import Base
from datetime import datetime


class User(Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True)
    email = Column(String, unique=True)
    password_hash = Column(String) # 비밀번호 해시 필드 이름 일관성을 위해


class Store(Base):
    __tablename__ = "store"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id")) # ForeignKey로 변경
    name = Column(String, index=True)
    location = Column(String)

    cameras = relationship("Camera", back_populates="store")
    user = relationship("User") # User와의 관계 추가 (Store가 어떤 User에 속하는지)


class Camera(Base):
    __tablename__ = "camera"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id")) # ForeignKey로 변경
    store_id = Column(Integer, ForeignKey("store.id")) # ForeignKey로 변경
    name = Column(String)
    video_url = Column(String)
    image_url = Column(String) # 카메라에 마지막 캡처 이미지 URL을 저장할 수도 있음

    store = relationship("Store", back_populates="cameras")
    user = relationship("User") # User와의 관계 추가 (Camera가 어떤 User에 속하는지)


# --- 새로 추가되는 EventType 클래스 ---
class EventType(Base):
    __tablename__ = "event_type"
    id = Column(Integer, primary_key=True, index=True)
    type = Column(String, unique=True, index=True) # "theft", "helmet", "smoking" 등
    risk_level = Column(String) # "low", "medium", "high" 등


# --- 수정된 Event 클래스 ---
class Event(Base):
    __tablename__ = "event"
    id = Column(Integer, primary_key=True, index=True)
    
    # 다른 테이블의 ID를 참조하도록 ForeignKey로 변경
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    store_id = Column(Integer, ForeignKey("store.id"), nullable=False)
    camera_id = Column(Integer, ForeignKey("camera.id"), nullable=False)
    type_id = Column(Integer, ForeignKey("event_type.id"), nullable=False) # EventType 참조

    event_time = Column(DateTime, default=datetime.utcnow)
    video_url = Column(String, nullable=True)

    # 관계 설정: 다른 모델 객체에 접근할 수 있게 해줌
    user = relationship("User")
    store = relationship("Store")
    camera = relationship("Camera")
    event_type = relationship("EventType") # EventType과의 관계 추가