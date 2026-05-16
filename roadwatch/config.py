import os
from pathlib import Path


class Config:
    BASE_DIR = Path(__file__).resolve().parent.parent
    INSTANCE_DIR = BASE_DIR / "instance"
    SECRET_KEY = os.getenv("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL") or f"sqlite:///{(INSTANCE_DIR / 'roadwatch.db').as_posix()}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    REMEMBER_COOKIE_HTTPONLY = True
    SESSION_COOKIE_HTTPONLY = True
    MAIL_SERVER = os.getenv("MAIL_SERVER")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "true").lower() in {"1", "true", "yes", "on"}
    MAIL_USE_SSL = os.getenv("MAIL_USE_SSL", "false").lower() in {"1", "true", "yes", "on"}
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER") or MAIL_USERNAME or "RoadWatch Perth <noreply@roadwatch.local>"
