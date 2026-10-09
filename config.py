import os
from urllib.parse import quote_plus
from decimal import Decimal
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "mobile-world-dev-secret-key-2026")
    
    # Database Settings
    DB_TYPE = os.environ.get("DB_TYPE", "mysql").lower()
    DB_USER = os.environ.get("DB_USER", "mobile_user")
    DB_PASSWORD = os.environ.get("DB_PASSWORD", "MobileWorld@2026")
    DB_HOST = os.environ.get("DB_HOST", "localhost")
    DB_PORT = os.environ.get("DB_PORT", "3306")
    DB_NAME = os.environ.get("DB_NAME", "mobile_world_db")
    
    encoded_password = quote_plus(DB_PASSWORD)
    if DB_TYPE == "mysql":
        SQLALCHEMY_DATABASE_URI = (
            f"mysql+pymysql://{DB_USER}:{encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
        )
    else:
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, 'mobile_world.db')}"

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_recycle": 280,
        "pool_pre_ping": True,
    }

    # Business Rules
    FLAT_DELIVERY_FEE = Decimal(os.environ.get("FLAT_DELIVERY_FEE", "50.00"))
    ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

    # Session & Security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    PERMANENT_SESSION_LIFETIME = 86400  # 24 hours


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
