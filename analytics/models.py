from sqlalchemy import Column, Integer, String, DateTime, Float
from database import Base
from datetime import datetime

class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    image_hash = Column(String, index=True)
    detected_disease = Column(String, index=True)
    confidence_data = Column(String) # Storing JSON as string for simplicity
    timestamp = Column(DateTime, default=datetime.utcnow)

