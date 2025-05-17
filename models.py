from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from database import Base

class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, index=True)
    type = Column(String, index=True)
    video_path = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
