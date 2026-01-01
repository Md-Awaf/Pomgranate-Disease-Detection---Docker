# ML Service (FastAPI)

The **ML Service** is the inference engine of the system. It hosts the deep learning model and processes image classification requests.

## Features

-   **Disease Detection**: Uses a pre-trained Keras/TensorFlow model (`model.h5`) to classify leaf diseases.
-   **Intelligent Caching**: Uses SQLite (`data/prediction_cache.db`) to cache results by image hash, avoiding redundant inference.
-   **Async Logging**: Sends prediction results to the Analytics Service asynchronously to prevent blocking the response.

## Supported Classes

1.  `Alternaria`
2.  `Anthracnose`
3.  `Bacterial_Blight`
4.  `Cercospora`
5.  `Healthy`

## API Endpoints

-   `POST /predict`:
    -   **Input**: Multipart form-data with `file` (image) and `original_filename`.
    -   **Output**: JSON object with class probabilities and the detected disease.

## Configuration

-   `ANALYTICS_SERVICE_URL`: URL of the Analytics Service for logging.

## Docker Details

-   **Base Image**: `python:3.9`
-   **System Dependencies**: `libgl1`, `libglib2.0-0` (Required for OpenCV/Pillow image processing).
-   **Port**: `8000`
