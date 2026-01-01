"""
Pomegranate Disease Detection Web Service
-----------------------------------------
This Flask application serves as the frontend for the Pomegranate Disease Detection system.
It handles image uploads, displays results, and communicates with the ML and Analytics services.
"""
from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
from werkzeug.utils import secure_filename
import os
import shutil
from datetime import datetime
import httpx
import logging

app = Flask(__name__)

# create a folder to store images
if not os.path.exists(os.path.join(os.getcwd(), 'uploads')):
    os.makedirs(os.path.join(os.getcwd(), 'uploads'))

app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024
app.config['UPLOAD_EXTENSIONS'] = ['.jpg', '.png', '.gif']
app.config['SECRET_KEY'] = 'supersecretkeygoeshere'

import threading

# The URL where your FastAPI server is running
ML_API_URL = os.environ.get("ML_SERVICE_URL", "http://ml:8000/predict")
ANALYTICS_SERVICE_URL = os.environ.get("ANALYTICS_SERVICE_URL", "http://analytics:8002")
ADMIN_SECRET = os.environ.get("ADMIN_SECRET", "supersecretadmin")

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

@app.route('/admin/reset-project', methods=['POST'])
def reset_project():
    # 1. Verify Secret
    secret = request.headers.get('X-Admin-Secret')
    if secret != ADMIN_SECRET:
        log_message(f"Unauthorized reset attempt from IP: {request.remote_addr}")
        return {"status": "error", "message": "Unauthorized"}, 401

    results = {}
    
    # 2. Clear ML Cache
    try:
        # Use http://ml:8000/clear-cache not predict
        ml_base = ML_API_URL.rsplit('/', 1)[0]
        resp = httpx.post(f"{ml_base}/clear-cache", timeout=5.0)
        results['ml_cache'] = resp.json()
    except Exception as e:
        results['ml_cache'] = {"status": "error", "message": str(e)}

    # 3. Clear Analytics Data
    try:
        resp = httpx.post(f"{ANALYTICS_SERVICE_URL}/clear-data", timeout=5.0)
        results['analytics'] = resp.json()
    except Exception as e:
        results['analytics'] = {"status": "error", "message": str(e)}

    # 4. Clear Local Uploads
    try:
        deleted_count = 0
        for filename in os.listdir(app.config['UPLOAD_FOLDER']):
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                    deleted_count += 1
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
                    deleted_count += 1
            except Exception as e:
                log_message(f"Failed to delete {file_path}. Reason: {e}")
        results['uploads'] = {"status": "success", "deleted_files": deleted_count}
    except Exception as e:
        results['uploads'] = {"status": "error", "message": str(e)}

    log_message(f"Project reset triggered by admin. Results: {results}")
    return results


def log_message(message: str):
    # Date-time stamped logging with print
    print(f"[{datetime.now()}] {message}")



@app.route('/favicon.ico')
def favicon():
    return redirect(url_for('static', filename='favicon.ico'))


@app.route('/manifest.json')
def serve_manifest():
    return app.send_static_file('manifest.json', mimetype='application/manifest+json')


@app.route('/service-worker.js')
def sw():
    return app.send_static_file('service-worker.js')

@app.route('/')
def index():
    user_agent = request.headers.get('User-Agent')
    user_agent = user_agent.lower()
    log_message(f"Request from User-Agent: {user_agent} Client IP: {request.remote_addr}")

    if "android" in user_agent or "iphone" in user_agent:
        return render_template('mobile/detect.html')
    else:
        return render_template('desktop/index.html')


@app.route('/upload', methods=('POST',))
def upload():
    log_message(f"Received upload request from client IP: {request.remote_addr}")
    # set session for image results
    if "file_urls" not in session:
        log_message("Initializing file_urls in session")
        session['file_urls'] = []
    # list to hold our uploaded image urls
    file_urls = session['file_urls']

    files = request.files.getlist('files')
    log_message(f"Number of files received: {len(files)} from client IP: {request.remote_addr}")
    for file in files:
        fn = secure_filename(file.filename)
        if fn != '':
            file_ext = os.path.splitext(fn)[1]
            if file_ext not in app.config['UPLOAD_EXTENSIONS']:
                log_message(f"Invalid file type attempted: {file_ext} from client IP: {request.remote_addr}")
                return 'Invalid file type', 400
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], fn))
            log_message(f"Saved file: {fn} from client IP: {request.remote_addr}")
            file_urls.append(fn)
    session['file_urls'] = file_urls
    return "ok" # change to your own logic
    # return redirect(url_for('results')) # change to your own logic

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'],
                               filename)

@app.route('/results')
def results(file_urls=None):
    log_message("Rendering results page")
    user_agent = request.headers.get('User-Agent')
    user_agent = user_agent.lower()
    # print(user_agent)
    # set the file_urls and remove the session variable
    if "file_urls" not in session or session['file_urls'] == []:
        file = request.args.get('filename')
        # check if the file is present in the upload folder
        if not os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], file)):
            # copy file from static/public folder to uploads folder using shutil
            shutil.copy(os.path.join(os.getcwd(), 'static', 'public', file), os.path.join(app.config['UPLOAD_FOLDER'], file))
        file_urls = [file]
    else:
        file_urls = session.pop('file_urls', [])
    # file_urls = ["IMG_20230813_151923.jpg", "IMG_20230910_102304.jpg"]
    # print(file_urls)
    dis_results = []
    # Persistent client for handling multiple files efficiently
    log_message(f"Sending {len(file_urls)} files for prediction to ML API")
    with httpx.Client(timeout=30.0) as client:
        for filename in file_urls:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            if not os.path.exists(file_path):
                log_message(f"File not found: {file_path}, skipping.")
                continue

            with open(file_path, 'rb') as f:
                # Send binary and filename for FastAPI logs
                files = {'file': (filename, f, 'image/jpeg')}
                data = {'original_filename': filename}
                
                try:
                    response = client.post(ML_API_URL, files=files, data=data)
                    if response.status_code == 200:
                        # FastAPI result is already in the correct flat format
                        res = response.json()
                        
                        # Add metadata exactly as your original script did
                        file_stat = os.stat(file_path)
                        res['filename'] = filename
                        res["upload_time"] = datetime.fromtimestamp(file_stat.st_mtime)
                        res["size"] = file_stat.st_size
                        
                        dis_results.append(res)
                except Exception as e:
                    app.logger.error(f"API Error for {filename}: {e}")

    if "android" in user_agent or "iphone" in user_agent:
        print("Mobile")
        return render_template('mobile/results.html', results=dis_results)
    else:
        return render_template('desktop/results.html', results=dis_results)
    # return render_template('results.html', file_urls=file_urls)

@app.route('/detect')
def detect():
    return render_template('desktop/detect.html')

@app.route('/info')
def info():
    return render_template('desktop/hifi-under-development.html')

@app.route('/help')
def help():
    return render_template('desktop/hifi-help.html')

    
    # return render_template('results.html', file_urls=file_urls)

if __name__ == '__main__':
    # app.run(host='192.168.175.193', debug=True)
    app.run(host='0.0.0.0', port=5000, debug=True)


