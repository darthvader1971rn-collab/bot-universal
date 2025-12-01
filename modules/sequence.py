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

# --- KONFIGURACJA AWARYJNA ---
URL_LOBBY = "https://lobby.rail-nation.com/#/start"

SERVER_MAP = {
    "us103.railnation-game.com": "US103 Broadway",
    "us102.railnation-game.com": "US102 Grand Central",
    "m5201.railnation-game.com": "INT5201 Odyssey"
}
# -----------------------------

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
                pyautogui.click(location)
                logging.info(f"Kliknięto: {image_name}")
                time.sleep(2)
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
            pyautogui.click(center_x, center_y)
            time.sleep(2)
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
    pyautogui.click(center_x, center_y)
    logging.info(f"Kliknięcie (Fallback/OCR) w {description} -> ({center_x}, {center_y})")
    time.sleep(2)
    return True

def perform_drag_list_up(region):
    """Przewija listę w dół (ciągnąc myszkę w górę)"""
    if region == (0,0,0,0): return
    start_x = region[0] + region[2] // 2
    start_y = region[1] + region[3] // 2
    
    pyautogui.moveTo(start_x, start_y)
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

def wake_mouse():
    pyautogui.moveTo(200, 200, duration=0.2)
    pyautogui.moveRel(10, 0, duration=0.2)
    pyautogui.moveRel(-10, 0, duration=0.2)
    pyautogui.click() 
    logging.info("Ruch myszką + Klik (Wake Up).")

def park_mouse_safe():
    w, h = pyautogui.size()
    pyautogui.moveTo(w - 200, h - 200)

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
                pyautogui.click(x, y)
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
            pyautogui.click(center_x, center_y)
            time.sleep(2)
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
                pyautogui.click(item['x'], item['y'])
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
        
        pyautogui.click(region[0] + 10, region[1] + 10)
        time.sleep(0.5)
        new_coords = scan_screen_for_city(region, specific_city=best['city'])
        if new_coords:
            click_x, click_y = new_coords
        else:
            click_x, click_y = best['x'], best['y']
        visited_cities[best['city']] = time.time()
        pyautogui.click(click_x, click_y)
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
    
    reg_rozklad = load_region(settings.CSV_REGION_ROZKLAD)
    if not click_image("rozklad_zapisany.png", retry=3, region=reg_rozklad):
        logging.warning("Brak ikony zapisanych rozkładów.")
        click_image("closed.png")
        return
    
    time.sleep(1)
    if not click_image("rozwiniecie_listy.png", retry=3, region=reg_rozklad):
         logging.warning("Brak ikony rozwijania listy.")
         click_image("closed.png")
         return

    time.sleep(1.5)
    
    reg_listing = load_region(settings.CSV_REGION_LISTING)
    found = False
    image_path = os.path.join(settings.GRAPHICS_PATH, target_image)
    
    for attempt in range(5): 
        try:
            location = pyautogui.locateOnScreen(image_path, region=reg_listing, confidence=0.9, grayscale=True)
            if location:
                # OBLICZANIE WSPÓŁRZĘDNYCH Z UŻYCIEM OFFSETU Z SETTINGS
                anchor_center_x = location.left + location.width // 2
                anchor_center_y = location.top + location.height // 2 # Zmiana na środek
                
                # Dodajemy Offset (automatycznie dobrany w settings.py)
                target_x = anchor_center_x + settings.FARMING_OFFSET_X
                target_y = anchor_center_y + settings.FARMING_OFFSET_Y
                
                logging.info(f"Znaleziono '{farming_type}'. Klikam w teczkę (Offset X+{settings.FARMING_OFFSET_X}, Y+{settings.FARMING_OFFSET_Y}) -> ({target_x}, {target_y})")
                pyautogui.click(target_x, target_y)
                found = True
                break
            else:
                logging.info(f"Nie widzę '{farming_type}'. Przewijam listę ({attempt+1}/5)...")
                perform_drag_list_up(reg_listing)
                time.sleep(1.5)
        except Exception as e:
            logging.error(f"Błąd szukania/przewijania: {e}")

    if not found:
        logging.warning(f"Nie znaleziono rozkładu '{farming_type}' po 5 przewinięciach.")
    
    time.sleep(1)
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
    
    # 4. Adopt Schedule (Najwyższy)
    if not click_highest_image("adopt_schedule.png"):
        logging.warning("[KALKULATOR] Nie znaleziono przycisku 'adopt_schedule.png'.")
        click_image("closed.png")
        return
    time.sleep(2)
    
    # 5. Select All (region listing lub fallback)
    if not click_image("select_all.png", retry=2, region=reg_listing):
        logging.info("[KALKULATOR] 'select_all' niewidoczny (może już zaznaczone?).")
    time.sleep(1)
    
    # 6. Let's Go / Buy Wagons (Używamy inteligentnej funkcji z fallbackiem OCR)
    if handle_lets_go_logic():
        logging.info("[KALKULATOR] Zakończono sukcesem (Lets Go / Buy).")
    else:
        logging.warning("[KALKULATOR] Nie udało się sfinalizować (brak Lets Go/Buy).")

    time.sleep(2)
    click_image("closed.png")
    time.sleep(4)


def try_click_signup_cascade(reg_listing, reg_wagony):
    if reg_listing != (0,0,0,0):
        if click_image("sign_up.png", retry=1, region=reg_listing): return True
    if click_image("buy_railroad_cars.png", retry=1, region=reg_wagony): return True
    
    if reg_wagony != (0,0,0,0):
        text = ocr_region(reg_wagony, debug_filename="debug_wagons.png")
        if "Buy" in text and "railroad" in text:
            center_x = reg_wagony[0] + reg_wagony[2] // 2
            center_y = reg_wagony[1] + reg_wagony[3] // 2
            pyautogui.click(center_x, center_y)
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
        elif t1 < now: t1 += timedelta(days=1)

        t2 = now.replace(hour=h, minute=31, second=0, microsecond=0)
        if t2 < now and h == (now.hour + 1) % 24: t2 += timedelta(days=1)
        elif t2 < now: t2 += timedelta(days=1)
             
        candidates.append(t1)
        candidates.append(t2)
        
    future_times = [t for t in candidates if t > now]
    if not future_times: return 60
    
    future_times.sort()
    next_slot = future_times[0]
    
    diff = (next_slot - now).total_seconds()
    return diff, next_slot

# --- GŁÓWNA PĘTLA ---

def contest_loop(active_modes=None):
    """
    active_modes: Lista stringów, np. ["miasta", "kalkulator"]
    """
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

    logging.info(f"Bot uruchomiony. AKTYWNE TRYBY: {active_modes}")

    while True:
        sec_to_next_global = get_seconds_to_next_contest(schedule)
        
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
            
            click_image("schedule_assistant.png", region=reg_listing)
            click_image("adopt_schedule.png", region=reg_listing)
            click_image("select_all.png", region=reg_listing)
            time.sleep(1)
            
            if not handle_lets_go_logic():
                click_image("closed.png")
                time.sleep(5)
                current_offset = 120
                continue
            
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
                while time.time() - start_loop < 30:
                    if try_click_signup_cascade(reg_listing, reg_wagony):
                        contest_entered = True
                        perform_drag_from_listing()
                        break
                    time.sleep(1)
            else:
                time.sleep(1)
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
                drag_count = 1
                start_time = time.time()
                last_wake = time.time()
                
                while True:
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
                    
                    if time.time() - start_time > settings.CONTEST_TIMEOUT:
                        click_image("closed.png")
                        final_status = "timeout"
                        skip_tactical_pause = True
                        break

                    if time.time() - last_wake > 90:
                        wake_mouse()
                        last_wake = time.time()
                    time.sleep(10)
            else:
                click_image("closed.png")
                final_status = "error"
            
            if final_status != "won":
                current_offset = 120
            else:
                current_offset = 300
            
            logging.info(f"Koniec konkursu. Wynik: {final_status}.")
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
                            wake_mouse()

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
                            wake_target = time.time() + sec_wait
                            while time.time() < wake_target:
                                wake_mouse()
                                time.sleep(min(60, wake_target - time.time()))
                            
                            logging.info("[TIMER] Wybiła godzina! Uruchamiam KALKULATOR.")
                            run_farming_calculator()
                        else:
                            logging.info("[TIMER] Zbyt blisko konkursu, pomijam slot kalkulatora.")
                            time.sleep(60)
            
            else:
                if should_log: logging.info(f"Czuwanie... (<15 min do {next_city}).")
                wake_mouse()
                time.sleep(5)
                    
            now = time.time()
            for k in [c for c, t in visited_cities.items() if now - t > 3600]: del visited_cities[k]
            time.sleep(5)