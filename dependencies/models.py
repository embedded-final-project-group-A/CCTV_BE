from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from dependencies.db import Base

class User(Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True)
    email = Column(String, unique=True)
    password_hash = Column(String)

class Store(Base):
    __tablename__ = "store"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"))
    name = Column(String, index=True)
    location = Column(String)

    cameras = relationship("Camera", back_populates="store")

class Camera(Base):
    __tablename__ = "camera"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"))
    store_id = Column(Integer, ForeignKey("store.id"))
    name = Column(String)
    video_url = Column(String)
    image_url = Column(String)

    store = relationship("Store", back_populates="cameras")  # 수정된 부분
