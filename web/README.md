# Web Service (Flask)

The **Web Service** is the user-facing frontend of the Pomegranate Disease Detection System. It allows users to upload leaf images and view disease prediction results.

## Features

-   **Image Upload**: Validates and uploads images (JPG, PNG).
-   **Service Orchestration**: Sends images to the ML Service for inference.
-   **Logging**: Logs user activity to the Analytics Service.
-   **Responsive UI**: Basic desktop and mobile support using Bootstrap/Jinja2.

## API & Routes

-   `GET /`: Renders the homepage/upload interface.
-   `POST /upload`: Handles the file upload process.
-   `GET /results?filename=...`: Fetches prediction results for a specific file.

## Configuration

The service is configured via environment variables (defined in `docker-compose.yml`):

-   `ML_SERVICE_URL`: URL of the ML service (default: `http://ml:8000/predict`).
-   `ANALYTICS_SERVICE_URL`: URL of the Analytics service (default: `http://analytics:8002`).
-   `FLASK_ENV`: Deployment environment (e.g., `development`).

## Docker Details

-   **Base Image**: `python:3.9`
-   **Port**: `5000`
-   **Volumes**: `/app/uploads` (Persists uploaded images).
