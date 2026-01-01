"""
Pomegranate Disease Detection ML Service
----------------------------------------
This FastAPI application provides the machine learning inference endpoint.
It accepts image uploads, performs disease detection using a TensorFlow model,
and logs predictions to the Analytics service.
"""
import logging
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras.preprocessing import image
import numpy as np
from PIL import Image
import io
import sqlite3
import json
import hashlib
from datetime import datetime
import os
import requests
import threading

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ML_Service")

def log_message(message: str):
    # Date-time stamped logging with print
    print(f"[{datetime.now()}] {message}")

app = FastAPI()

import requests
import threading

MODEL_PATH = "Model/model.h5"
model = keras.models.load_model(MODEL_PATH)
CLASS_LABELS = ['Alternaria', 'Anthracnose', 'Bacterial_Blight', 'Cercospora', 'Healthy']
ANALYTICS_SERVICE_URL = os.environ.get("ANALYTICS_SERVICE_URL", "http://analytics:8002")

def log_prediction_async(image_hash, detected_disease, confidence_data):
    try:
        payload = {
            "image_hash": image_hash,
            "detected_disease": detected_disease,
            "confidence_data": json.dumps(confidence_data)
        }
        requests.post(f"{ANALYTICS_SERVICE_URL}/log-prediction", json=payload)
    except Exception as e:
        print(f"Failed to log prediction: {e}")


# --- SQLite3 Cache Setup ---
import os
if not os.path.exists("data"):
    os.makedirs("data")

DB_FILE = "data/prediction_cache.db"

def init_db():
    """Initializes the database. DROPS existing table to restart with new schema."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # Drop table to ensure fresh schema as requested
    cursor.execute("DROP TABLE IF EXISTS prediction_cache")
    cursor.execute('''
        CREATE TABLE prediction_cache (
            image_hash TEXT PRIMARY KEY,
            result_json TEXT,
            predicted_class TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
    log_message("Initialized SQLite3 cache database with new schema.")

# Run database initialization on startup
init_db()

def get_cached_result(img_hash: str):
    """Retrieves a result from the database if the hash exists."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT result_json FROM prediction_cache WHERE image_hash = ?", (img_hash,))
    row = cursor.fetchone()
    conn.close()
    log_message(f"Checked cache for hash: {img_hash} - Found: {row is not None}")
    return json.loads(row[0]) if row else None

def save_to_cache(img_hash: str, result: dict, predicted_class: str):
    """Saves the prediction result to the database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO prediction_cache (image_hash, result_json, predicted_class, timestamp) 
            VALUES (?, ?, ?, ?)
        ''', (img_hash, json.dumps(result), predicted_class, datetime.now()))
        conn.commit()
        log_message(f"Saved result to cache for hash: {img_hash}")
    except Exception as e:
        log_message(f"Error saving to cache: {e}")
    finally:
        conn.close()

@app.post("/clear-cache")
def clear_cache():
    """Clears the SQLite prediction cache."""
    try:
        # Delete the DB file if it exists
        if os.path.exists(DB_FILE):
            os.remove(DB_FILE)
            log_message(f"Deleted cache file: {DB_FILE}")
        
        # Re-initialize the DB
        init_db()
        return {"status": "success", "message": "Cache cleared and initialized"}
    except Exception as e:
        log_message(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/predict")
async def predict(
    file: UploadFile = File(...), 
    original_filename: str = Form(...) # Metadata for logging
):
    log_message(f"Processing request for file: {original_filename}")
    
    try:
        # 1. Read binary content and generate hash
        contents = await file.read()
        img_hash = hashlib.sha256(contents).hexdigest()
        log_message(f"Generated hash for {original_filename}: {img_hash}")

        # 2. Check SQLite3 Cache
        cached_res = get_cached_result(img_hash)
        if cached_res:
            log_message(f"CACHE HIT: Using SQLite result for {original_filename}")
            # Ensure we log this "view" to analytics even if cached
            try:
                predicted_class = cached_res.get('detected_disease', 'Unknown')
                thread = threading.Thread(target=log_prediction_async, args=(img_hash, predicted_class, cached_res))
                thread.start()
            except Exception as e:
                log_message(f"Error starting analytics thread for cache hit: {e}")
            return cached_res

        # 3. Cache Miss: Perform Inference
        log_message(f"CACHE MISS: Processing {original_filename} via Model")
        img = Image.open(io.BytesIO(contents)).convert('RGB').resize((256, 256))
        img_array = image.img_to_array(img)
        img_array = np.expand_dims(img_array, axis=0) / 255.0
        
        predictions = model.predict(img_array)
        class_index = np.argmax(predictions[0])
        predicted_class = CLASS_LABELS[class_index]
        log_message(f"Model prediction for {original_filename}: {predicted_class}")

        # 4. Format Result (Original Structure)
        result = {
            'detected_disease': predicted_class,
            'Alternaria': f"{(predictions[0][0]*100):.02f}",
            'Anthracnose': f"{(predictions[0][1]*100):.02f}",
            'Bacterial_Blight': f"{(predictions[0][2]*100):.02f}",
            'Cercospora': f"{(predictions[0][3]*100):.02f}",
            'Healthy': f"{(predictions[0][4]*100):.02f}"
        }

        # 5. Save to SQLite3
        save_to_cache(img_hash, result, predicted_class)
        log_message(f"Returning result for {original_filename}: {result}")
        
        # 6. Log to Analytics Service (Async)
        try:
            thread = threading.Thread(target=log_prediction_async, args=(img_hash, predicted_class, result))
            thread.start()
        except Exception as e:
            log_message(f"Error starting analytics thread: {e}")

        return result

    except Exception as e:
        log_message(f"Error processing {original_filename}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error during inference")