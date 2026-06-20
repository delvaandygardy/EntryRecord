import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

load_dotenv(os.path.join(BASE_DIR, ".env"))

# ANPR externe (Platerecognizer)
PLATERECOGNIZER_API_KEY = os.getenv("PLATERECOGNIZER_API_KEY", "")

# Sécurité JWT
SECRET_KEY = os.getenv("SECRET_KEY", "dev_secret_key_CHANGE_IN_PROD")

# PostgreSQL connection
DB_HOST     = os.getenv("DB_HOST",     "localhost")
DB_PORT     = int(os.getenv("DB_PORT", "5432"))
DB_NAME     = os.getenv("DB_NAME",     "enregistrement_auto")
DB_USER     = os.getenv("DB_USER",     "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

# Camera settings
CAMERA_INDEX = 0
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720
PLATE_DETECT_INTERVAL = 0.5  # seconds between detection attempts

# OCR settings
OCR_LANGUAGES = ["fr", "en"]
OCR_CONFIDENCE_THRESHOLD = 0.6

# Scanner settings
SCANNER_SERIAL_PORT = None  # None = auto-detect
SCANNER_BAUDRATE = 9600
SCANNER_TIMEOUT = 1.0

# UI settings
APP_TITLE = "Système d'Enregistrement Automatique"
APP_WIDTH = 1400
APP_HEIGHT = 800
THEME = "dark"
COLOR_PRIMARY = "#1a73e8"
COLOR_SUCCESS = "#34a853"
COLOR_WARNING = "#fbbc04"
COLOR_DANGER = "#ea4335"

# Auto-clear entries after N seconds (0 = disabled)
AUTO_CLEAR_SECONDS = 0

# Duplicate detection window (seconds)
DUPLICATE_WINDOW = 30
