import os
from pathlib import Path


ALLOWED_EXTENSIONS = {'mp4', 'mp3', 'jpg', 'jpeg', 'png'}
UPLOAD_FOLDER = str(Path(__file__).resolve().parents[2] / 'dbs' / 'uploads')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
	return '.' in filename and get_file_extension(filename) in ALLOWED_EXTENSIONS

def get_file_extension(filename):
    parts = filename.split(".")
    if len(parts) <= 1:
        return ""
    return parts[-1]