# -*- coding: utf-8 -*-
import os
import pyautogui # Potrzebne do wykrycia rozdzielczości

# --- AUTOMATYCZNE WYKRYWANIE ŚCIEŻKI ---
BASE_PATH = os.path.dirname(os.path.abspath(__file__))

# --- WYKRYWANIE ROZDZIELCZOŚCI ---
screen_width, screen_height = pyautogui.size()

# Domyślne wartości (zabezpieczenie)
CSV_FOLDER_NAME = "config_4k"
GRAPHICS_SUBFOLDER = r"resources\img\en\3840x2160"

# Logika wyboru konfiguracji
if screen_width == 3840:
    # PC (4K)
    print(f"[INFO] Wykryto 4K ({screen_width}x{screen_height}).")
    CSV_FOLDER_NAME = "config_4k"
    GRAPHICS_SUBFOLDER = r"resources\img\en\3840x2160"

elif screen_width == 2560 or screen_width == 2048:
    # PC (2K - 2560x1440)
    # 2560 = Skalowanie 100%
    # 2048 = Skalowanie 125% (2560 / 1.25)
    print(f"[INFO] Wykryto 2K ({screen_width}x{screen_height}).")
    CSV_FOLDER_NAME = "config_2k"
    GRAPHICS_SUBFOLDER = r"resources\img\en\2560x1440"
    
elif screen_width == 1920 or screen_width == 1536: 
    # LAPTOP (Full HD - 1920x1080)
    # 1920 = Skalowanie 100%
    # 1536 = Skalowanie 125%
    print(f"[INFO] Wykryto Full HD ({screen_width}x{screen_height}).")
    CSV_FOLDER_NAME = "config_laptop"
    GRAPHICS_SUBFOLDER = r"resources\img\en\1920x1080"
    
else:
    # Fallback
    print(f"[WARNING] Nieznana rozdzielczość: {screen_width}x{screen_height}. Używam domyślnej 4K.")
    CSV_FOLDER_NAME = "config_4k"
    GRAPHICS_SUBFOLDER = r"resources\img\en\3840x2160"

# --- BUDOWANIE ŚCIEŻEK ---
GRAPHICS_PATH = os.path.join(BASE_PATH, GRAPHICS_SUBFOLDER)
SCREENSHOTS_PATH = os.path.join(BASE_PATH, "screenshots")

CSV_PATH_ROOT = os.path.join(BASE_PATH, CSV_FOLDER_NAME)

# --- Pliki CSV z regionami ---
CSV_REGION_MAIN = os.path.join(CSV_PATH_ROOT, "prostokat.csv")
CSV_REGION_WAGONY = os.path.join(CSV_PATH_ROOT, "prostokat_wagony.csv")
CSV_REGION_LISTING = os.path.join(CSV_PATH_ROOT, "prostokat_listing.csv")

# --- Regiony dla FARMINGU ---
CSV_REGION_POCIAGI = os.path.join(CSV_PATH_ROOT, "prostokat_pociagi.csv")
CSV_REGION_ROZKLAD = os.path.join(CSV_PATH_ROOT, "prostokat_rozklad.csv")

# --- Pliki przycisków (Fallback) ---
CSV_REGION_SIGN_UP = os.path.join(CSV_PATH_ROOT, "prostokat_sign_up.csv")
CSV_REGION_SCHEDULE = os.path.join(CSV_PATH_ROOT, "prostokat_schedule.csv")
CSV_REGION_ADOPT = os.path.join(CSV_PATH_ROOT, "prostokat_adopt.csv")
CSV_REGION_SELECT_ALL = os.path.join(CSV_PATH_ROOT, "prostokat_select_all.csv")
CSV_REGION_LETS_GO = os.path.join(CSV_PATH_ROOT, "prostokat_lets_go.csv")
CSV_REGION_CLOSED = os.path.join(CSV_PATH_ROOT, "prostokat_closed.csv")

# --- RESZTA KONFIGURACJI ---
TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
CONTEST_TIMEOUT = 15 * 60
PLAYER_NICK = "DarthVader1971"

CITIES = [
    "Helena","Memphis","San Antonio","St. Louis","El Paso","Washington","Las Vegas","Montgomery",
    "Charlotte","Columbus","Bismarck","Reno","Minneapolis","Seattle","Little Rock","Salt Lake City",
    "Boise","Denver","Indianapolis","Boston","Detroit","Amarillo","Oklahoma City","Augusta","Phoenix",
    "Norfolk","Omaha","Buffalo","Nashville","Wichita","Portland","Dallas","Eugene","Albuquerque",
    "Midland","Casper","San Francisco","Chicago","Kansas City","New York","Rapid City","Davenport",
    "New Orleans","Miami","San Diego","Jacksonville","Milwaukee","Walla Walla","Houston","Los Angeles",
    "Athens","Madrid","Abuja","Paris","Marrakesh","Berlin","Cairo","Stockholm"
]