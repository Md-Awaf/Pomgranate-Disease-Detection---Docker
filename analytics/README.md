# Analytics Service (FastAPI)

The **Analytics Service** acts as the backend data store for the system. It continually collects data from other services to enable system-wide monitoring and reporting.

## Features

-   **Centralized Logging**: Receives data from both Web and ML services.
-   **Database Integration**: Uses SQLAlchemy to persist data in a PostgreSQL database.
-   **Resiliency**: Implements startup retry logic to handle database connection delays.

## Database Schema

-   **Table**: `predictions`
    -   `id`: Primary Key
    -   `image_hash`: Unique hash of the analyzed image.
    -   `detected_disease`: The class with the highest probability.
    -   `confidence_data`: JSON string containing full probability distribution.
    -   `timestamp`: Time of prediction.

## API Endpoints

-   `POST /log-prediction`:
    -   **Input**: JSON payload (`PredictionCreate` model).
    -   **Output**: `status: success` and `prediction_id`.

## Configuration

-   `DATABASE_URL`: Connection string for PostgreSQL (e.g., `postgresql://user:pass@host:5432/db`).

## Docker Details

-   **Base Image**: `python:3.9-slim` (Lightweight).
-   **Port**: `8002`
-   **Dependencies**: `libpq-dev` (for `psycopg2`).
