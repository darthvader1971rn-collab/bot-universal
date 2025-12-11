    # -*- coding: utf-8 -*-
import time
import logging
import pyautogui
import pytesseract
from PIL import Image, ImageOps, ImageFilter
import csv
import os
import re
import difflib
import sys
import tkinter as tk
from datetime import datetime, timedelta
import settings

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

# Wyłączenie Fail-Safe
pyautogui.FAILSAFE = False 

pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_PATH

# --- ZMIENNE GLOBALNE ---
VIDEO_ERROR_TIME = 0.0 
VIDEO_PAUSE_END_TIME = 0.0
# -------------------------

# --- KONFIGURACJA AWARYJNA ---
URL_LOBBY = "https://lobby.rail-nation.com/#/start"

SERVER_MAP = {
    "us103.railnation-game.com": "US103 Broadway",
    "us102.railnation-game.com": "US102 Grand Central",
    "m5201.railnation-game.com": "INT5201 Odyssey"
}
# -----------------------------

# --- NOWA FUNKCJA HARD CLICK (GLOBALNE OPÓŹNIENIE 1.5S) ---
def perform_hard_click(x, y, button='left'):
    """Symuluje ludzkie kliknięcie (z lekkim opóźnieniem)."""
    time.sleep(1.5) # <<< POPRAWKA: Opóźnienie przed każdym klikiem
    try:
        pyautogui.moveTo(x, y, duration=0.3)
        time.sleep(0.1)
        pyautogui.mouseDown(button=button)
        pyautogui.mouseUp(button=button)
        time.sleep(1.0) 
    except Exception as e:
        logging.error(f"Błąd Hard Click: {e}")

# --- NOWA FUNKCJA WAKE MOUSE (PRZENIESIONA NA GÓRĘ DLA CZYSTOŚCI) ---
def wake_mouse():
    """
    Ruch myszką + Hard Click w bezpiecznym punkcie (Anti-AFK). 
    Dodano D&D (na wysokości X:5, Y:540) aby zapobiec uśpieniu ekranu.
    """
    w, h = pyautogui.size()
    
    # 1. Standardowy Anti-AFK (Hard Click w lewym górnym rogu)
    tx, ty = 100, 100 
    pyautogui.moveTo(tx, ty, duration=0.4)
    pyautogui.moveRel(15, 0, duration=0.2) 
    pyautogui.moveRel(-15, 0, duration=0.2)
    perform_hard_click(tx, ty) 
    logging.info("Ruch myszką + Klik (Wake Up).")

    # 2. DODATKOWY RUCH D&D NA WYSOKOŚCI 540
    drag_x = 5
    drag_y = 540
    
    logging.info("Wykonywanie Anti-AFK D&D (mały ruch w górę i powrót).")
    pyautogui.moveTo(drag_x, drag_y, duration=0.3)
    time.sleep(0.5)
    
    # Ruch w górę (ujemne Y) o 10px
    pyautogui.dragRel(0, -10, duration=0.4, button='left')
    
    time.sleep(0.2)
    
    # Powrót do pozycji początkowej (ruch w dół o 10px)
    pyautogui.dragRel(0, 10, duration=0.4, button='left')
    
    time.sleep(1.0)
    
    logging.info("Anti-AFK D&D zakończone.")

def park_mouse_safe():
    w, h = pyautogui.size()
    pyautogui.moveTo(w - 200, h - 200)

def load_region(path):
    try:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter=";")
            row = next(reader)
            x = int(row["LewyGorny_X"])
            y = int(row["LewyGorny_Y"])
            w = int(row["Szerokosc"])
            h = int(row["Wysokosc"])
            return (x, y, w, h)
    except Exception as e:
        logging.error(f"Nie udało się wczytać regionu z pliku {path}: {e}")
        return (0, 0, 0, 0)

def check_image_visible(image_name, region=None):
    image_path = os.path.join(settings.GRAPHICS_PATH, image_name)
    if not os.path.exists(image_path): return False
    try:
        if region and region != (0,0,0,0):
            return pyautogui.locateOnScreen(image_path, region=region, confidence=0.8, grayscale=True) is not None
        else:
            return pyautogui.locateOnScreen(image_path, confidence=0.8, grayscale=True) is not None
    except: return False

def click_image(image_name, retry=3, region=None):
    image_path = os.path.join(settings.GRAPHICS_PATH, image_name)
    if not os.path.exists(image_path):
        logging.warning(f"Brak pliku graficznego: {image_path}")
        return False

    for attempt in range(retry):
        try:
            if region and region != (0,0,0,0):
                location = pyautogui.locateCenterOnScreen(image_path, region=region, confidence=0.8, grayscale=True)
            else:
                location = pyautogui.locateCenterOnScreen(image_path, confidence=0.8, grayscale=True)
            
            if location:
                perform_hard_click(location.x, location.y) # Ujednolicone kliknięcie
                logging.info(f"Kliknięto: {image_name}")
                time.sleep(1.5)
                return True
            else:
                time.sleep(0.5)
        except Exception:
            pass
    
    logging.warning(f"Nie znaleziono przycisku: {image_name}")
    return False

def click_highest_image(image_name, region=None):
    """Specjalna funkcja dla adopt_schedule - klika w ten najwyżej na ekranie"""
    image_path = os.path.join(settings.GRAPHICS_PATH, image_name)
    if not os.path.exists(image_path): return False
    
    try:
        if region and region != (0,0,0,0):
            matches = list(pyautogui.locateAllOnScreen(image_path, region=region, confidence=0.8, grayscale=True))
        else:
            matches = list(pyautogui.locateAllOnScreen(image_path, confidence=0.8, grayscale=True))
        
        if matches:
            # Sortuj po Y (top), aby znaleźć najwyższy
            matches.sort(key=lambda box: box.top)
            best_match = matches[0]
            center_x = best_match.left + best_match.width // 2
            center_y = best_match.top + best_match.height // 2
            
            logging.info(f"Kliknięto NAJWYŻSZY {image_name} w ({center_x}, {center_y})")
            perform_hard_click(center_x, center_y) # Ujednolicone kliknięcie
            time.sleep(1.5)
            return True
        else:
            logging.warning(f"Nie znaleziono żadnego {image_name} do adopcji.")
            return False
    except Exception as e:
        logging.error(f"Błąd click_highest: {e}")
        return False

def click_from_csv_center(csv_path, description):
    region = load_region(csv_path)
    if region == (0,0,0,0): return False
    center_x = region[0] + region[2] // 2
    center_y = region[1] + region[3] // 2
    perform_hard_click(center_x, center_y) # Ujednolicone kliknięcie
    logging.info(f"Kliknięcie (Fallback/OCR) w {description} -> ({center_x}, {center_y})")
    time.sleep(1.5)
    return True

def perform_drag_list_up(region):
    """Przewija listę w dół (ciągnąc myszkę w górę)"""
    if region == (0,0,0,0): return
    start_x = region[0] + region[2] // 2
    start_y = region[1] + region[3] // 2
    
    pyautogui.moveTo(start_x, start_y, duration=0.2)
    time.sleep(0.3)
    # Drag w górę (ujemne Y)
    pyautogui.dragRel(0, -300, duration=0.8, button='left')
    time.sleep(1.5)

def perform_drag_from_listing():
    """Stara funkcja dla konkursów"""
    logging.info("Rozpoczynam procedurę Drag & Drop (Konkurs)...")
    region = load_region(settings.CSV_REGION_LISTING)
    perform_drag_list_up(region)

def ocr_region(region, debug_filename=None):
    try:
        screenshot = pyautogui.screenshot(region=region)
        width, height = screenshot.size
        screenshot = screenshot.resize((width * 2, height * 2), Image.BICUBIC)
        gray = ImageOps.grayscale(screenshot)
        sharp = gray.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))
        bw = ImageOps.autocontrast(sharp, cutoff=5)
        
        if debug_filename:
            if not os.path.exists(settings.SCREENSHOTS_PATH):
                os.makedirs(settings.SCREENSHOTS_PATH)
            bw.save(os.path.join(settings.SCREENSHOTS_PATH, debug_filename))

        config = "--psm 6 --oem 1 -l eng"
        return pytesseract.image_to_string(bw, config=config)
    except Exception as e:
        logging.error(f"Błąd OCR: {e}")
        return ""


# --- FUNKCJE POMOCNICZE / AWARYJNE ---

def get_current_url():
    try:
        pyautogui.hotkey('ctrl', 'l')
        time.sleep(0.5)
        pyautogui.hotkey('ctrl', 'c')
        time.sleep(0.5)
        park_mouse_safe()
        root = tk.Tk()
        root.withdraw()
        return root.clipboard_get()
    except: return ""

def find_server_text_and_click(text_to_find):
    logging.info(f"[OCR Lobby] Szukam: '{text_to_find}'")
    try:
        park_mouse_safe()
        time.sleep(1)
        screenshot = pyautogui.screenshot()
        gray = ImageOps.grayscale(screenshot)
        bw = ImageOps.autocontrast(gray, cutoff=5)
        data = pytesseract.image_to_data(bw, output_type=pytesseract.Output.DICT, lang='eng')
        key_word = text_to_find.split()[0]
        n_boxes = len(data['text'])
        for i in range(n_boxes):
            if key_word in data['text'][i]:
                x = data['left'][i] + data['width'][i] // 2
                y = data['top'][i] + data['height'][i] // 2
                logging.info(f"[SUKCES] Znaleziono serwer w ({x}, {y}). Klikam.")
                perform_hard_click(x, y) # Ujednolicone kliknięcie
                return True
    except Exception as e: logging.error(f"Błąd OCR Lobby: {e}")
    return False

def execute_emergency_reconnect(schedule, visited_cities):
    logging.warning("!!! URUCHAMIAM PROCEDURĘ AWARYJNĄ !!!")
    current_url = get_current_url()
    target_server = None
    for url_key, name in SERVER_MAP.items():
        if url_key in current_url:
            target_server = name
            break
    if not target_server:
        logging.error(f"Nie rozpoznano serwera z URL: {current_url}. Przerywam.")
        return
    logging.info(f"Cel: Powrót na serwer {target_server}")
    pyautogui.hotkey('ctrl', 'l')
    time.sleep(1)
    pyautogui.write(URL_LOBBY)
    pyautogui.press('enter')
    logging.info("Czekam 30s na załadowanie Lobby...")
    time.sleep(30)
    success = False
    for i in range(3):
        if find_server_text_and_click(target_server):
            success = True
            break
        time.sleep(10)
    if not success:
        logging.error("Nie udało się znaleźć/kliknąć serwera w Lobby.")
        return
    logging.info("Czekam na załadowanie mapy...")
    for i in range(3):
        time.sleep(60)
        reg_mapa = load_region(settings.CSV_REGION_MAIN)
        visible_list = scan_screen_for_city(reg_mapa, silent=False) 
        if visible_list:
            logging.info("SUKCES! Mapa załadowana. Powrót do pracy.")
            return
        logging.warning(f"Mapa niezaładowana (próba {i+1}/3). Odświeżam (F5)...")
        if i < 2: pyautogui.press('f5')
    logging.error("KRYTYCZNY BŁĄD: Nie udało się wrócić do gry po 3 minutach.")

# -------------------------------------------------------

def smart_schedule_logic(reg_listing):
    """
    Sprawdza, który przycisk jest wyżej: Adopt Schedule czy Keep Current Schedule.
    Zwraca True, jeśli należy kontynuować i ADOPTOWAĆ (czyli Adopt Schedule jest wyżej).
    Zwraca False, jeśli należy ZATRZYMAĆ (czyli Keep Current Schedule jest wyżej) lub są równe.
    """
    logging.info("[SMART] Porównanie pozycji Adopt vs Keep...")
    
    # 1. Znajdź pozycje obu przycisków (UŻYWAMY TRY/EXCEPT DO ZAPOBIEGANIA KRYTYCZNYM BŁĘDOM)
    try:
        adopt_loc = pyautogui.locateCenterOnScreen(os.path.join(settings.GRAPHICS_PATH, "adopt_schedule.png"), 
                                                region=reg_listing, confidence=0.8)
    except pyautogui.ImageNotFoundException:
        adopt_loc = None
        
    try:
        keep_loc = pyautogui.locateCenterOnScreen(os.path.join(settings.GRAPHICS_PATH, "Keep_current_schedule.png"),
                                               region=reg_listing, confidence=0.8)
    except pyautogui.ImageNotFoundException:
        keep_loc = None

    # 2. Logika decyzyjna (pozostaje bez zmian)
    if adopt_loc and keep_loc:
        # Porównanie pozycji Y (im mniejsza wartość Y, tym wyżej na ekranie)
        if adopt_loc.y < keep_loc.y:
            logging.info("[SMART] DECYZJA: Adopt schedule jest WYŻEJ. Kontynuuję ADOPT.")
            return True
        else:
            logging.info("[SMART] DECYZJA: Keep current schedule jest WYŻEJ/RÓWNO. Przerywam, KEEP.")
            return False
    elif adopt_loc:
        logging.info("[SMART] Widzę tylko Adopt schedule. Kontynuuję ADOPT.")
        return True
    elif keep_loc:
        logging.info("[SMART] Widzę tylko Keep current schedule. Przerywam, KEEP.")
        return False
        
    logging.warning("[SMART] Nie znaleziono przycisków Adopt/Keep. Domyślnie: ADOPT.")
    return True # Bezpieczny fallback

def setup_schedule_and_start(reg_listing, is_contest=False):
    """
    Otwiera Asystenta, używa Smart Logic i wykonuje akcję.
    Zwraca True, jeśli rozkład został zmieniony/wysłany, False jeśli został zachowany (Keep) lub wystąpił błąd.
    """
    if not click_image("schedule_assistant.png", region=reg_listing):
        logging.warning("[SETUP] Nie widzę Asystenta Rozkładu.")
        return False
    
    time.sleep(1.5)
    
    should_adopt = smart_schedule_logic(reg_listing)
    
    if should_adopt:
        logging.info("[SETUP] Wybrano ADOPT -> Konfiguruję maszyny.")
        click_image("adopt_schedule.png", retry=1, region=reg_listing)
        time.sleep(1)
        click_image("select_all.png", retry=2, region=reg_listing)
        time.sleep(1)
        
        if handle_lets_go_logic():
            logging.info("[SETUP] Pociągi wysłane (Let's Go / Buy).")
            return True
        else:
            logging.warning("[SETUP] Nie znaleziono przycisku startu. Zamykam awaryjnie.")
            click_image("closed.png")
            return False
            
    else:
        logging.info("[SETUP] Wybrano KEEP -> Zamykam Asystenta.")
        click_image("closed.png")
        time.sleep(1.0)
        return False # Nie wysłano nowych pociągów/rozkładu

def handle_lets_go_logic():
    """Uniwersalna funkcja do klikania Let's Go / Kup Wagony"""
    logging.info("--- Weryfikacja: Let's Go / Buy Wagons ---")
    reg_wagony = load_region(settings.CSV_REGION_WAGONY)
    
    # 1. Let's Go
    if click_image("lets_go.png", retry=2, region=reg_wagony): return True
    
    # 2. Buy Railroad Cars
    logging.info("Nie znaleziono Let's Go. Szukam 'buy_railroad_cars.png'...")
    if click_image("buy_railroad_cars.png", retry=2, region=reg_wagony): return True
    
    # 3. Fallback OCR
    if reg_wagony != (0,0,0,0):
        text = ocr_region(reg_wagony, debug_filename="debug_wagons.png")
        if "Buy" in text or "railroad" in text or "cars" in text:
            logging.info("Wykryto tekst 'Buy/Railroad' (OCR). Klikam.")
            center_x = reg_wagony[0] + reg_wagony[2] // 2
            center_y = reg_wagony[1] + reg_wagony[3] // 2
            perform_hard_click(center_x, center_y) # Ujednolicone kliknięcie
            time.sleep(1.5)
            return True
            
    return False

def load_schedule(file_path):
    schedule = {}
    if not os.path.exists(file_path): return schedule
    with open(file_path, encoding="utf-8") as f:
        for line in f:
            if "-" in line:
                try:
                    time_str, city = line.strip().split(" - ")
                    hour, minute = map(int, time_str.split(":"))
                    if city.strip() not in schedule: schedule[city.strip()] = []
                    schedule[city.strip()].append((hour, minute))
                except: continue
    return schedule

def get_target_click_time(city, schedule, offset_seconds=120):
    if city not in schedule: return None, False, None
    now = datetime.now()
    best_target = None
    best_start = None
    for hour, minute in schedule[city]:
        start_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        click_time = start_time - timedelta(seconds=offset_seconds) 
        end_time = start_time + timedelta(minutes=15)
        if click_time <= now < end_time:
            return click_time, True, start_time
        if now < click_time:
            if best_target is None or click_time < best_target:
                best_target = click_time
                best_start = start_time
    return best_target, False, best_start

def get_seconds_to_next_contest(schedule):
    now = datetime.now()
    min_diff = float('inf')
    for city, times in schedule.items():
        for hour, minute in times:
            start = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if (now - start).total_seconds() > 3600:
                start += timedelta(days=1)
            if start > now:
                diff = (start - now).total_seconds()
                if diff < min_diff:
                    min_diff = diff
    if min_diff == float('inf'): return 0
    return min_diff

def get_seconds_to_next_visible_contest(schedule, visible_cities_names):
    now = datetime.now()
    min_diff = float('inf')
    nearest_city = None
    for city in visible_cities_names:
        if city not in schedule: continue
        for hour, minute in schedule[city]:
            start = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if (now - start).total_seconds() > 3600:
                start += timedelta(days=1)
            if start > now:
                diff = (start - now).total_seconds()
                if diff < min_diff:
                    min_diff = diff
                    nearest_city = city
    if min_diff == float('inf'): return 0, None
    return min_diff, nearest_city

def scan_screen_for_city(region, specific_city=None, silent=False):
    screenshot = pyautogui.screenshot(region=region)
    gray = ImageOps.grayscale(screenshot)
    sharp = gray.filter(ImageFilter.UnsharpMask(radius=2, percent=200, threshold=3))
    bw = sharp.point(lambda p: 255 if p > 180 else 0) 
    if not os.path.exists(settings.SCREENSHOTS_PATH):
        os.makedirs(settings.SCREENSHOTS_PATH)
    bw.save(os.path.join(settings.SCREENSHOTS_PATH, "debug_map.png"))
    data = pytesseract.image_to_data(bw, config="--psm 11 --oem 1 -l eng", output_type=pytesseract.Output.DICT)
    found_candidates = []
    for i, text in enumerate(data["text"]):
        t = text.strip()
        if t and int(data["conf"][i]) >= 40:
            match = difflib.get_close_matches(t, settings.CITIES, n=1, cutoff=0.7)
            matched_city = match[0] if match else None
            if matched_city:
                if specific_city:
                    if matched_city.lower() == specific_city.lower():
                        gx = region[0] + data["left"][i] + data["width"][i] // 2
                        gy = region[1] + data["top"][i] + data["height"][i] // 2
                        return (gx, gy)
                else:
                    if not silent:
                        logging.info(f"[MAPA] Rozpoznano: '{t}' -> Dopasowano: '{matched_city}'")
                    gx = region[0] + data["left"][i] + data["width"][i] // 2
                    gy = region[1] + data["top"][i] + data["height"][i] // 2
                    found_candidates.append({'city': matched_city, 'x': gx, 'y': gy})
    if specific_city: return None
    return found_candidates

def find_and_click_city(schedule, visited_cities, farming_mode=False, silent=False, offset_seconds=300):
    region = load_region(settings.CSV_REGION_MAIN)
    if region == (0,0,0,0): return False, None
    candidates_data = scan_screen_for_city(region, silent=silent)
    candidates = []
    
    for item in candidates_data:
        miasto = item['city']
        if miasto in visited_cities and (time.time() - visited_cities[miasto]) < 3600: continue
        target_time, is_active, real_start = get_target_click_time(miasto, schedule, offset_seconds)
        if target_time:
            item['time'] = target_time
            item['real_start'] = real_start
            if is_active:
                logging.info(f"AKTYWNY: {miasto} (Szybki start)")
                visited_cities[miasto] = time.time()
                perform_hard_click(item['x'], item['y']) # Ujednolicone kliknięcie
                time.sleep(10)
                return True, real_start
            candidates.append(item)
    if not candidates: return False, None
    candidates.sort(key=lambda x: x['time'])
    best = candidates[0]
    wait_s = (best['time'] - datetime.now()).total_seconds()
    if wait_s > 900: return False, None 
    if wait_s > 0:
        logging.info(f"Czekam na {best['city']} (Start -{offset_seconds}s za: {int(wait_s)}s)...")
        while datetime.now() < best['time']:
            if (best['time'] - datetime.now()).total_seconds() > 60:
                time.sleep(30)
                wake_mouse()
            else: time.sleep(0.5)
        
        # Poprawka: Używamy Hard Click zamiast pyautogui.click
        perform_hard_click(region[0] + 10, region[1] + 10)
        time.sleep(0.5)
        new_coords = scan_screen_for_city(region, specific_city=best['city'])
        if new_coords:
            click_x, click_y = new_coords
        else:
            click_x, click_y = best['x'], best['y']
        visited_cities[best['city']] = time.time()
        perform_hard_click(click_x, click_y) # Ujednolicone kliknięcie
        time.sleep(10)
        return True, best['real_start']
    return False, None

# --- NOWE FUNKCJE FARMINGU ---

def run_farming_standard(farming_type="miasta"):
    """
    Obsługuje typy: 'miasta' i 'magazyny' metodą Anchor+Offset.
    Pobiera offsety dynamicznie z pliku settings.py (dla 4K vs FHD).
    """
    logging.info(f"--- URUCHAMIAM FARMING STANDARDOWY: {farming_type.upper()} ---")
    
    farming_images = {
        "miasta": "farm_miasta.png",
        "magazyny": "farm_magazyny.png"
    }
    target_image = farming_images.get(farming_type, "farm_miasta.png")
    
    reg_pociagi = load_region(settings.CSV_REGION_POCIAGI)
    if not click_image("lista_pociagow.png", retry=3, region=reg_pociagi):
        logging.warning("Nie udało się otworzyć listy pociągów.")
        return

    time.sleep(1)
    
    # Używamy ujednoliconej funkcji setup_schedule_and_start dla standardowego farmingu
    reg_listing = load_region(settings.CSV_REGION_LISTING)
    
    # 1. Otwarcie Asystenta
    if not click_image("schedule_assistant.png", region=reg_listing):
        logging.warning("[SETUP] Nie widzę Asystenta Rozkładu.")
        click_image("closed.png")
        return
    
    time.sleep(1.5)
    
    # 2. Smart Logic / Keep (Jeśli Keep, wraca False i zamyka okno)
    should_adopt = smart_schedule_logic(reg_listing)
    
    if should_adopt:
        logging.info("[SETUP] Wybrano ADOPT (Standard Farming) -> Konfiguruję maszyny.")
        click_image("adopt_schedule.png", retry=1, region=reg_listing)
        time.sleep(1)
        click_image("select_all.png", retry=2, region=reg_listing)
        time.sleep(1)
        
        if handle_lets_go_logic():
            logging.info("[SETUP] Pociągi wysłane (Let's Go / Buy).")
        else:
            logging.warning("[SETUP] Nie znaleziono przycisku startu. Zamykam awaryjnie.")
            click_image("closed.png")
            
    else:
        logging.info("[SETUP] Wybrano KEEP -> Zamykam Asystenta.")
        click_image("closed.png")
        
    time.sleep(4)

def run_farming_calculator():
    """
    Specjalny tryb KALKULATORA.
    Sekwencja: Lista -> Career -> Calculator -> Adopt (Highest) -> Select All -> Lets Go / Buy
    """
    logging.info("--- URUCHAMIAM FARMING: KALKULATOR (Maintenance) ---")
    
    reg_pociagi = load_region(settings.CSV_REGION_POCIAGI)
    reg_listing = load_region(settings.CSV_REGION_LISTING)
    
    # 1. Lista pociągów
    if not click_image("lista_pociagow.png", retry=3, region=reg_pociagi):
        logging.warning("[KALKULATOR] Nie otwarto listy pociągów.")
        return
    time.sleep(1.5)

    # 2. Silnik Kariery
    if not click_image("Career_engine.png", retry=3, region=reg_listing):
        logging.warning("[KALKULATOR] Brak 'Career_engine.png'.")
        click_image("closed.png")
        return
    time.sleep(1.5)
    
    # 3. Kalkulator Rozkładu
    if not click_image("Timetable_calculator.png", retry=3, region=reg_listing):
        logging.warning("[KALKULATOR] Brak 'Timetable_calculator.png'.")
        click_image("closed.png")
        return
    time.sleep(2)
    
    # 4. Smart Logic / Adopt Schedule (Najwyższy)
    
    should_adopt = smart_schedule_logic(reg_listing)
    
    if should_adopt:
        logging.info("[SETUP] Wybrano ADOPT (Kalkulator) -> Konfiguruję maszyny.")
        click_highest_image("adopt_schedule.png")
        time.sleep(2)
        click_image("select_all.png", retry=2, region=reg_listing)
        time.sleep(1)
        
        if handle_lets_go_logic():
            logging.info("[KALKULATOR] Zakończono sukcesem (Lets Go / Buy).")
        else:
            logging.warning("[KALKULATOR] Nie udało się sfinalizować (brak Lets Go/Buy).")
    else:
        logging.info("[SETUP] Wybrano KEEP -> Zamykam Asystenta.")

    time.sleep(2)
    click_image("closed.png")
    time.sleep(4)


def try_click_signup_cascade(reg_listing, reg_wagony):
    # POPRAWKA: Opóźnienie kliknięcia Sign Up do T+4s
    time.sleep(4) 
    
    if reg_listing != (0,0,0,0):
        if click_image("sign_up.png", retry=1, region=reg_listing): return True
    if click_image("buy_railroad_cars.png", retry=1, region=reg_wagony): return True
    
    if reg_wagony != (0,0,0,0):
        text = ocr_region(reg_wagony, debug_filename="debug_wagons.png")
        if "Buy" in text and "railroad" in text:
            center_x = reg_wagony[0] + reg_wagony[2] // 2
            center_y = reg_wagony[1] + reg_wagony[3] // 2
            perform_hard_click(center_x, center_y) # Ujednolicone kliknięcie
            time.sleep(1.5)
            return True
    
    try:
        if click_from_csv_center(settings.CSV_REGION_SIGN_UP, "Sign Up (CSV)"): return True
    except: pass
    return False

def monitor_contest():
    region = load_region(settings.CSV_REGION_LISTING)
    if region == (0,0,0,0): return "unknown"
    
    text = ocr_region(region, debug_filename="debug_listing.png")
    player_nick_safe = re.escape(settings.PLAYER_NICK)
    
    if re.search(rf"{player_nick_safe}.*?Completed in", text, re.DOTALL):
        return "won"
    if re.search(rf"{player_nick_safe}.*?tons delivered", text, re.DOTALL):
        return "lost"
    return "unknown"

def get_seconds_to_next_slot():
    """Oblicza ile sekund do najbliższego XX:01 lub XX:31"""
    now = datetime.now()
    candidates = []
    
    for h in [now.hour, (now.hour + 1) % 24]:
        t1 = now.replace(hour=h, minute=1, second=0, microsecond=0)
        if t1 < now and h == (now.hour + 1) % 24: t1 += timedelta(days=1)
        elif t1 < now: t1 += timedelta(hours=1)

        t2 = now.replace(hour=h, minute=31, second=0, microsecond=0)
        if t2 < now and h == (now.hour + 1) % 24: t2 += timedelta(days=1)
        elif t2 < now: t2 += timedelta(hours=1)
             
        candidates.append(t1)
        candidates.append(t2)
        
    future_times = [t for t in candidates if t > now]
    if not future_times: return 60, datetime.now() + timedelta(minutes=1)
    
    future_times.sort()
    next_slot = future_times[0]
    
    diff = (next_slot - now).total_seconds()
    return diff, next_slot

# --- GŁÓWNA PĘTLA ---

# ... (reszta kodu bez zmian) ...

def contest_loop(active_modes=None):
    if active_modes is None: active_modes = []
    
    schedule_usa = load_schedule("miasta - USA.txt")
    schedule_eu = load_schedule("miasta - Europa_Afryka.txt")
    schedule = {**schedule_usa, **schedule_eu}
    visited_cities = {}
    
    skip_tactical_pause = False
    next_map_log_time = 0
    no_cities_start_time = None
    current_offset = 300
    
    # --- FLAGI STERUJĄCE ---
    farming_done_in_this_break = False
    calc_immediate_done = False 
    last_wake_time = time.time()
    
    logging.info(f"Bot uruchomiony. AKTYWNE TRYBY: {active_modes}")

    while True:
        # --- ANTI-AFK CO 5 MINUT ---
        if time.time() - last_wake_time > 300:
             wake_mouse()
             last_wake_time = time.time()

        sec_to_next_global = get_seconds_to_next_contest(schedule)
        
        # === NOWA LOGIKA OFFSETU T-420s (7 MINUT) ===
        if current_offset == 300 and sec_to_next_global <= 420:
             logging.info("[OFFSET_CONTROL] Konkurs zbliża się (<420s). Reset offsetu na T-300s w celu wczesnego wejścia.")
             current_offset = 300 # Potwierdzamy, że T-300s jest aktywne, aby wymusić wejście
        # ============================================

        should_log = False
        if sec_to_next_global < 1200:
            should_log = True
        elif time.time() > next_map_log_time:
            should_log = True
            delay = max(300, sec_to_next_global / 3)
            next_map_log_time = time.time() + delay
            
        found, contest_start_time = find_and_click_city(schedule, visited_cities, silent=not should_log, offset_seconds=current_offset)
        
        if found:
            # RESET FLAG PO ZNALEZIENIU MIASTA/KONKURSIE
            no_cities_start_time = None
            farming_done_in_this_break = False 
            calc_immediate_done = False        
            last_wake_time = time.time() # Reset AFK timer
            
            logging.info("Wchodzenie w interfejs konkursu...")
            
            # --- SEKWENCJA KONKURSOWA ---
            if contest_start_time:
                if (contest_start_time - datetime.now()).total_seconds() <= 30:
                    time.sleep(2)
                    if monitor_contest() in ["won", "lost"]:
                        click_image("closed.png")
                        time.sleep(5)
                        continue

            reg_listing = load_region(settings.CSV_REGION_LISTING)
            reg_wagony = load_region(settings.CSV_REGION_WAGONY)
            
            # Ustawianie rozkładu z logiką Adopt/Keep
            setup_schedule_and_start(reg_listing, is_contest=True)
            
            if contest_start_time:
                time_to_start = (contest_start_time - datetime.now()).total_seconds()
            else: time_to_start = 0

            if skip_tactical_pause or time_to_start <= 5:
                 is_fast_start = True
                 skip_tactical_pause = False
            else:
                 if time_to_start > 10: time.sleep(time_to_start - 10)
                 perform_drag_from_listing()
                 time_left = (contest_start_time - datetime.now()).total_seconds()
                 if time_left > 0: time.sleep(time_left)
                 is_fast_start = False
            
            contest_entered = False
            if is_fast_start:
                start_loop = time.time()
                # Zostawiamy pętlę, ale kluczowe opóźnienie 4s jest w try_click_signup_cascade
                while time.time() - start_loop < 30:
                    if try_click_signup_cascade(reg_listing, reg_wagony):
                        contest_entered = True
                        perform_drag_from_listing()
                        break
                    time.sleep(1)
            else:
                time.sleep(1)
                # Tu też opóźnienie jest w try_click_signup_cascade
                if try_click_signup_cascade(reg_listing, reg_wagony): contest_entered = True
                time.sleep(2.5)
                perform_drag_from_listing()
                time.sleep(1.5)
                if check_image_visible("sign_up.png", region=reg_listing):
                    click_image("sign_up.png", retry=1, region=reg_listing)
                    contest_entered = True
                time.sleep(54)

            final_status = "unknown"
            if contest_entered:
                last_drag_time = time.time()
                last_reload_time = time.time() 
                drag_count = 1
                start_monitor_time = time.time() 
                last_wake = time.time()
                
                # Ustawiamy nowy, sztywny timeout na 45 minut (2700 sekund)
                CONTEST_HARD_TIMEOUT = 2700 
                
                while True:
                    time_elapsed = time.time() - start_monitor_time
                    
                    # --- LOGIKA ODŚWIEŻANIA (RELOAD) ---
                    # Warunek 1: Czas > 30s
                    # Warunek 2: Minęło > 60s od ostatniego odświeżenia
                    if time_elapsed >= 30 and (time.time() - last_reload_time >= 60):
                        logging.info("[MONITORING] Klik w reload_competiton.png (Odświeżenie listy).")
                        if click_image("reload_competiton.png", retry=1, region=reg_listing):
                            last_reload_time = time.time()
                            # Po odświeżeniu, daj czas na ustabilizowanie się listy
                            time.sleep(5) 
                        else:
                            logging.warning("Nie znaleziono przycisku odświeżania.")
                    
                    # Sprawdzenie twardego limitu czasu (45 minut)
                    if time.time() - start_monitor_time > CONTEST_HARD_TIMEOUT: 
                        logging.error(f"[MONITORING] Twardy Timeout {CONTEST_HARD_TIMEOUT / 60} min. Awaryjne wyjście.")
                        click_image("closed.png")
                        final_status = "timeout_45min"
                        skip_tactical_pause = True
                        break # Wychodzimy, wracamy na mapę i farming
                        
                    # Sprawdzanie innych konkursów (jak w oryginalnym kodzie)
                    sec_next = get_seconds_to_next_contest(schedule)
                    if 0 < sec_next < 120:
                         logging.warning(f"[MONITORING] Inny konkurs za {int(sec_next)}s. Uciekam, aby się przygotować.")
                         click_image("closed.png")
                         final_status = "interrupted_by_next"
                         break
                         
                    if (time.time() - last_drag_time > 90) and (drag_count < 10):
                        drag_count += 1
                        perform_drag_from_listing()
                        last_drag_time = time.time()
                    
                    status = monitor_contest()
                    if status in ["lost", "won"]:
                        time.sleep(5)
                        if monitor_contest() == status:
                            click_image("closed.png")
                            final_status = status
                            skip_tactical_pause = False 
                            break
                    
                    if time.time() - last_wake > 90:
                        wake_mouse()
                        last_wake = time.time()
                    time.sleep(10)
            else:
                click_image("closed.png")
                final_status = "error"
            
            # Aktualizacja offsetu na podstawie wyniku
            if final_status != "won":
                current_offset = 120 # Agresywny (T-120s)
            else:
                current_offset = 300 # Bezpieczny (T-300s)
            
            logging.info(f"Koniec konkursu. Wynik: {final_status}. Nowy Offset: T-{current_offset}s.")
            time.sleep(5)

        else:
            # --- BRAK MIAST / OCZEKIWANIE ---
            reg_mapa = load_region(settings.CSV_REGION_MAIN)
            visible_list = scan_screen_for_city(reg_mapa, silent=True)
            
            if not visible_list:
                if no_cities_start_time is None:
                    no_cities_start_time = time.time()
                elif (time.time() - no_cities_start_time) > 900: # 15 min
                    execute_emergency_reconnect(schedule, visited_cities)
                    no_cities_start_time = None
            else:
                no_cities_start_time = None
            
            # --- LOGIKA DECYZYJNA (15 MINUT) ---
            visible_names = [item['city'] for item in visible_list]
            sec_to_next, next_city = get_seconds_to_next_visible_contest(schedule, visible_names)
            min_to_next = sec_to_next / 60
            
            # WARUNEK 15 MIN: Farming dozwolony
            if min_to_next > 15:
                
                # 1. SPRAWDZAMY STANDARDOWY FARMING (Miasta lub Magazyny)
                std_mode_to_run = None
                if "miasta" in active_modes: std_mode_to_run = "miasta"
                elif "magazyny" in active_modes: std_mode_to_run = "magazyny"
                
                if std_mode_to_run:
                    if not farming_done_in_this_break:
                        logging.info(f"[FARMING] Długa przerwa ({int(min_to_next)} min). Wykonuję: {std_mode_to_run}.")
                        run_farming_standard(std_mode_to_run)
                        farming_done_in_this_break = True 
                    else:
                        if "kalkulator" not in active_modes and min_to_next > 20:
                            logging.info(f"Farming zrobiony. Deep Sleep ({int(min_to_next)} min do {next_city}).")
                            time.sleep(120)
                            
                # 2. SPRAWDZAMY KALKULATOR
                if "kalkulator" in active_modes:
                    if not calc_immediate_done:
                        logging.info(f"[FARMING] Długa przerwa. Wykonuję KALKULATOR (Pierwszy start).")
                        run_farming_calculator()
                        calc_immediate_done = True
                    
                    else:
                        sec_wait, next_slot_dt = get_seconds_to_next_slot()
                        future_sec_to_next = sec_to_next - sec_wait
                        
                        if future_sec_to_next > 900: # > 15 min
                            logging.info(f"[TIMER] Czekam na slot {next_slot_dt.strftime('%H:%M')} (za {int(sec_wait)}s)...")
                            # Nowa, czysta logika oczekiwania:
                            wait_until = time.time() + sec_wait
                            while time.time() < wait_until:
                                # Używamy tylko małego sleepa, główny Anti-AFK budzi co 5 min
                                time.sleep(min(60, wait_until - time.time()))
                            
                            logging.info("[TIMER] Wybiła godzina! Uruchamiam KALKULATOR.")
                            run_farming_calculator()
                        else:
                            logging.info("[TIMER] Zbyt blisko konkursu, pomijam slot kalkulatora.")
                            time.sleep(60)
            
            else:
                if should_log: logging.info(f"Czuwanie... (<15 min do {next_city}).")
                # Główny Anti-AFK budzi co 5 min, tu wystarczy mały sleep.
                time.sleep(5)
                    
            now = time.time()
            for k in [c for c, t in visited_cities.items() if now - t > 3600]: del visited_cities[k]
            time.sleep(5)

if __name__ == "__main__":
    # Przykład wywołania (Jeśli uruchamiasz main.py)
    # contest_loop(active_modes=["miasta", "kalkulator"])
    pass