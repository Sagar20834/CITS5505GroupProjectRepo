import os
from pathlib import Path


class Config:
    BASE_DIR = Path(__file__).resolve().parent.parent
    INSTANCE_DIR = BASE_DIR / "instance"
    REPORT_UPLOAD_DIR = BASE_DIR / "static" / "uploads" / "reports"
    REPORT_UPLOAD_URL_PREFIX = "/static/uploads/reports/"
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL") or f"sqlite:///{(INSTANCE_DIR / 'roadwatch.db').as_posix()}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    REMEMBER_COOKIE_HTTPONLY = True
    SESSION_COOKIE_HTTPONLY = True
    MAPBOX_ACCESS_TOKEN = os.getenv("MAPBOX_ACCESS_TOKEN", "").strip()
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024
