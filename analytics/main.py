"""
Pomegranate Disease Detection Analytics Service
-----------------------------------------------
This FastAPI application manages analytics data for the system.
It stores prediction logs in a PostgreSQL database.
"""
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
import models
from database import engine, get_db, SessionLocal

# Database creation moved to startup event
app = FastAPI()

import time
from sqlalchemy.exc import OperationalError
import sqlalchemy

@app.on_event("startup")
def startup():
    # Retry connection to DB and create tables
    retries = 10
    while retries > 0:
        try:
            # Try to create tables (this will test connection too)
            models.Base.metadata.create_all(bind=engine)
            print("Database connection and tables created successfully.")
            break
        except Exception as e:
            print(f"Database connection failed, retrying in 2s... Error: {e}")
            retries -= 1
            time.sleep(2)
            if retries == 0:
                print("Could not connect to database after retries.")
                # We let it fail so Docker can potentially restart it if configured, 
                # but for now this helps debugging log.




class PredictionCreate(BaseModel):
    image_hash: str
    detected_disease: str
    confidence_data: str



@app.post("/log-prediction")
def log_prediction(pred: PredictionCreate, db: Session = Depends(get_db)):
    db_pred = models.Prediction(
        image_hash=pred.image_hash, 
        detected_disease=pred.detected_disease,
        confidence_data=pred.confidence_data
    )
    db.add(db_pred)
    db.commit()
    db.refresh(db_pred)
    return {"status": "success", "prediction_id": db_pred.id}

@app.post("/clear-data")
def clear_data(db: Session = Depends(get_db)):
    """Deletes all records from the predictions table."""
    try:
        db.query(models.Prediction).delete()
        db.commit()
        return {"status": "success", "message": "All analytics data cleared"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health():
    return {"status": "up"}
