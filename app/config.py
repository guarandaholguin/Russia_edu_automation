"""
Configuration settings for the Russia-Edu Scraper application.
"""
import os
from pathlib import Path

# Application information
APP_NAME = "Russia-Edu Status Checker"
APP_VERSION = "1.0.0"
APP_AUTHOR = "Your Organization"

# Debug mode
DEBUG_MODE = os.environ.get("DEBUG", "False").lower() in ("true", "1", "t")

# URL and scraping settings
BASE_URL = "https://russia-edu.minobrnauki.gov.ru"
TRACKING_URL = f"{BASE_URL}/"
CAPTCHA_TIMEOUT = 30  # seconds to wait for CAPTCHA solving
PAGE_LOAD_TIMEOUT = 60  # seconds to wait for page loading
BROWSER_HEADLESS = not DEBUG_MODE  # Show browser in debug mode

# Browser settings
DEFAULT_BROWSER = "chromium"  # chromium, firefox, or webkit
BROWSER_ARGS = ["--disable-dev-shm-usage"]

# Data extraction settings
MAX_RETRY_ATTEMPTS = 3
REQUEST_DELAY = 1.5  # seconds between requests to avoid being blocked

# UI settings
THEME_MODE = "system"  # system, light, or dark
DEFAULT_WINDOW_SIZE = (1024, 768)
UI_SCALING = 1.0

# Default paths
ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DOWNLOAD_PATH = ROOT_DIR / "downloads"
DEFAULT_DOWNLOAD_PATH.mkdir(exist_ok=True)

# Excel settings
DEFAULT_EXCEL_FILENAME = "student_status_results.xlsx"
EXCEL_COLUMNS = [
    "Número de Solicitud",
    "Email",
    "Nombre Completo (Cirílico)",
    "Nombre Completo (Latino)",
    #"Número de Registro",
    "País",
    "Estado de Solicitud",
    "Mensaje de Estado",
    "Nivel de Educación",
    "Programa Educativo",
    "Facultad Preparatoria",
    "Fecha de Consulta",
    "Error"
]

# 2Captcha API configuration
TWO_CAPTCHA_API_KEY = "797ba32617e59dc7877023d0f11cd338"  # Tu clave API