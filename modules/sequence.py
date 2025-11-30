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

    area_msg = f"w regionie {region}" if region and region != (0,0,0,0) else "na całym ekranie"
    logging.info(f"Szukam obrazka: {image_name} {area_msg}...")
    
    for attempt in range(retry):
        try:
            if region and region != (0,0,0,0):
                location = pyautogui.locateCenterOnScreen(image_path, region=region, confidence=0.8, grayscale=True)
            else:
                location = pyautogui.locateCenterOnScreen(image_path, confidence=0.8, grayscale=True)
            
            if location:
                pyautogui.click(location)
                logging.info(f"Znaleziono i kliknięto: {image_name} w ({location.x}, {location.y})")
                time.sleep(2)
                return True
            else:
                time.sleep(0.5)
        except Exception:
            try:
                if region and region != (0,0,0,0): location = pyautogui.locateCenterOnScreen(image_path, region=region)
                else: location = pyautogui.locateCenterOnScreen(image_path)
                if location:
                    pyautogui.click(location)
                    return True
            except:
                pass
    
    logging.warning(f"Nie udało się znaleźć przycisku: {image_name}")
    return False

def click_from_csv_center(csv_path, description):
    region = load_region(csv_path)
    if region == (0,0,0,0): return False
    center_x = region[0] + region[2] // 2
    center_y = region[1] + region[3] // 2
    pyautogui.click(center_x, center_y)
    logging.info(f"Kliknięcie (Fallback/OCR) w {description} → ({center_x}, {center_y})")
    time.sleep(2)
    return True

def perform_drag_from_listing():
    logging.info("Rozpoczynam procedurę Drag & Drop (Odświeżenie listy)...")
    region = load_region(settings.CSV_REGION_LISTING)
    if region == (0,0,0,0): return

    start_x = region[0] + region[2] // 2
    start_y = region[1] + region[3] // 2
    
    pyautogui.moveTo(start_x, start_y)
    time.sleep(0.5)
    pyautogui.dragRel(0, -400, duration=1.0, button='left')
    time.sleep(2)

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
    logging.info("Ruch myszką + Klik (Wake Up & Focus).")

def park_mouse_safe():
    w, h = pyautogui.size()
    pyautogui.moveTo(w - 200, h - 200)

# --- FUNKCJE AWARYJNE ---

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
    logging.info("--- Etap: Let's Go / Buy Wagons ---")
    reg_wagony = load_region(settings.CSV_REGION_WAGONY)
    if click_image("lets_go.png", retry=2, region=reg_wagony): return True
    logging.info("Nie znaleziono Let's Go. Szukam 'buy_railroad_cars.png'...")
    if click_image("buy_railroad_cars.png", retry=2, region=reg_wagony): return True
    logging.info("Nie znaleziono obrazków. Próba OCR w regionie wagonów...")
    if reg_wagony != (0,0,0,0):
        text = ocr_region(reg_wagony, debug_filename="debug_wagons.png")
        logging.info(f"OCR tekst: '{text.strip()}'")
        if "Buy" in text or "railroad" in text or "cars" in text:
            logging.info("Wykryto napis 'Buy railroad cars' przez OCR. Klikam.")
            center_x = reg_wagony[0] + reg_wagony[2] // 2
            center_y = reg_wagony[1] + reg_wagony[3] // 2
            pyautogui.click(center_x, center_y)
            time.sleep(2)
            return True
    logging.warning("Nie udało się przejść etapu Let's Go/Buy.")
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
    if farming_mode and candidates_data:
        best = candidates_data[0]
        logging.info(f"[FARMING] Klikam w miasto: {best['city']}...")
        pyautogui.click(best['x'], best['y'])
        time.sleep(10)
        return True, None
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
        logging.info(f"Czas nadszedł! Odświeżam pozycję miasta {best['city']}...")
        pyautogui.click(region[0] + 10, region[1] + 10)
        time.sleep(0.5)
        new_coords = scan_screen_for_city(region, specific_city=best['city'])
        if new_coords:
            logging.info(f"Zaktualizowano współrzędne dla {best['city']}: {new_coords}")
            click_x, click_y = new_coords
        else:
            logging.warning(f"Nie udało się odświeżyć pozycji {best['city']}! Używam starych.")
            click_x, click_y = best['x'], best['y']
        visited_cities[best['city']] = time.time()
        pyautogui.click(click_x, click_y)
        time.sleep(10)
        return True, best['real_start']
    return False, None

def run_farming_cycle():
    logging.info("--- URUCHAMIAM TRYB FARMINGU (Szybki Rozkład) ---")
    reg_pociagi = load_region(settings.CSV_REGION_POCIAGI)
    if reg_pociagi != (0,0,0,0):
        if click_image("lista_pociagow.png", retry=3, region=reg_pociagi):
            time.sleep(1)
            reg_rozklad = load_region(settings.CSV_REGION_ROZKLAD)
            if reg_rozklad != (0,0,0,0):
                if click_image("rozklad_zapisany.png", retry=3, region=reg_rozklad):
                    time.sleep(1)
                    if click_image("rozwiniecie_listy.png", retry=3, region=reg_rozklad):
                        time.sleep(1)
                        if click_image("wczytanie_listy.png", retry=3, region=reg_rozklad):
                            logging.info("[FARMING] Rozkład wczytany pomyślnie.")
                        else: logging.warning("[FARMING] Brak 'wczytanie_listy.png'")
                    else: logging.warning("[FARMING] Brak 'rozwiniecie_listy.png'")
                else: logging.warning("[FARMING] Brak 'rozklad_zapisany.png'")
            else: logging.error("Błąd pliku prostokat_rozklad.csv!")
            click_image("closed.png")
            time.sleep(5)
        else: logging.warning("[FARMING] Brak 'lista_pociagow.png'")
    else: logging.error("Błąd pliku prostokat_pociagi.csv!")

def try_click_signup_cascade(reg_listing, reg_wagony):
    if reg_listing != (0,0,0,0):
        if click_image("sign_up.png", retry=1, region=reg_listing): return True
    if click_image("buy_railroad_cars.png", retry=1, region=reg_wagony): return True
    if reg_wagony != (0,0,0,0):
        text = ocr_region(reg_wagony, debug_filename="debug_wagons.png")
        if "Buy" in text and "railroad" in text:
            logging.info("Wykryto 'Buy railroad cars' (OCR). Klikam.")
            center_x = reg_wagony[0] + reg_wagony[2] // 2
            center_y = reg_wagony[1] + reg_wagony[3] // 2
            pyautogui.click(center_x, center_y)
            return True
    try:
        if click_from_csv_center(settings.CSV_REGION_SIGN_UP, "Sign Up (CSV)"): return True
    except: pass
    return False

# --- PRZYWRÓCONA I PRZESUNIĘTA FUNKCJA MONITOR_CONTEST ---
def monitor_contest():
    region = load_region(settings.CSV_REGION_LISTING)
    if region == (0,0,0,0): return "unknown"
    
    text = ocr_region(region, debug_filename="debug_listing.png")
    text_inline = text.replace('\n', ' ').strip()
    logging.info(f"[DEBUG OCR]: {text_inline[:150]}") 

    player_nick_safe = re.escape(settings.PLAYER_NICK)
    win_pattern = rf"{player_nick_safe}.*?Completed in"
    loss_pattern = rf"{player_nick_safe}.*?tons delivered"

    if re.search(win_pattern, text, re.DOTALL):
        logging.info(f"Wykryto WON (Regex).")
        return "won"
    
    if re.search(loss_pattern, text, re.DOTALL):
        logging.info(f"Wykryto LOST/END (Regex).")
        return "lost"
    return "unknown"

def contest_loop():
    schedule_usa = load_schedule("miasta - USA.txt")
    schedule_eu = load_schedule("miasta - Europa_Afryka.txt")
    schedule = {**schedule_usa, **schedule_eu}
    visited_cities = {}
    skip_tactical_pause = False
    last_farming_time = 0
    next_map_log_time = 0
    
    no_cities_start_time = None
    
    current_offset = 300
    
    logging.info("Bot uruchomiony (Wersja: FIXED FINAL).")

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
            no_cities_start_time = None
            
            logging.info("Wchodzenie w interfejs konkursu...")
            
            # BRAMKA BEZPIECZEŃSTWA DLA SZYBKIEGO STARTU
            if contest_start_time:
                time_diff_check = (contest_start_time - datetime.now()).total_seconds()
                if time_diff_check <= 30: # Jesteśmy "po" lub "w trakcie"
                    logging.info("Weryfikacja czy konkurs nie jest już zakończony...")
                    time.sleep(2)
                    pre_check = monitor_contest()
                    if pre_check in ["won", "lost"]:
                        logging.warning(f"Konkurs już zakończony ({pre_check})! Zamykam.")
                        click_image("closed.png")
                        time.sleep(5)
                        continue

            reg_listing = load_region(settings.CSV_REGION_LISTING)
            reg_wagony = load_region(settings.CSV_REGION_WAGONY)
            
            click_image("schedule_assistant.png", region=reg_listing)
            click_image("adopt_schedule.png", region=reg_listing)
            click_image("select_all.png", region=reg_listing)
            time.sleep(1)
            
            success = handle_lets_go_logic()
            if not success:
                logging.warning("Nie udało się przejść dalej. Wracam.")
                click_image("closed.png")
                time.sleep(5)
                current_offset = 120
                continue
            
            # LOGIKA STARTU
            if contest_start_time:
                time_to_start = (contest_start_time - datetime.now()).total_seconds()
            else: time_to_start = 0

            if skip_tactical_pause or time_to_start <= 5:
                 logging.info("SZYBKI START (Po czasie/Timeout).")
                 is_fast_start = True
                 skip_tactical_pause = False
            else:
                 logging.info(f"ROZKŁADOWY START. Czekam {int(time_to_start)}s na sekwencję 00:00...")
                 if time_to_start > 10:
                     time.sleep(time_to_start - 10)
                 
                 logging.info("[-10s] Pre-start Drag.")
                 perform_drag_from_listing()
                 
                 time_left = (contest_start_time - datetime.now()).total_seconds()
                 if time_left > 0:
                     time.sleep(time_left)
                 
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
                # SZTYWNA OŚ CZASU (EARLY BIRD)
                time.sleep(1) 
                logging.info("[00:01] Klikam Sign Up.")
                if try_click_signup_cascade(reg_listing, reg_wagony): contest_entered = True
                
                time.sleep(2.5)
                logging.info("[00:04] Drag & Drop.")
                perform_drag_from_listing()
                
                time.sleep(1.5)
                logging.info("[00:06] Weryfikacja Sign Up.")
                if check_image_visible("sign_up.png", region=reg_listing):
                    logging.info("Przycisk widoczny - ponawiam.")
                    click_image("sign_up.png", retry=1, region=reg_listing)
                    contest_entered = True
                
                logging.info("Czekam do +60s na start monitoringu...")
                time.sleep(54)

            final_status = "unknown"
            if contest_entered:
                last_drag_time = time.time()
                drag_count = 1
                logging.info("Monitoring aktywny...")
                start_time = time.time()
                last_wake = time.time()
                next_log_time = time.time() + 60
                
                while True:
                    elapsed_drag = time.time() - last_drag_time
                    if (elapsed_drag > 90) and (drag_count < 10):
                        drag_count += 1
                        logging.info(f"Drag #{drag_count}/10")
                        perform_drag_from_listing()
                        last_drag_time = time.time()
                    
                    if time.time() > next_log_time:
                        logging.info(f"Status: Czas od Drag: {int(elapsed_drag)}s")
                        next_log_time = time.time() + 60

                    status = monitor_contest()
                    if status in ["lost", "won"]:
                        logging.info(f"Wykryto {status}. Weryfikacja...")
                        time.sleep(5)
                        if monitor_contest() == status:
                            logging.info("Potwierdzono. Zamykam.")
                            click_image("closed.png")
                            final_status = status
                            skip_tactical_pause = False 
                            break
                    
                    if time.time() - start_time > settings.CONTEST_TIMEOUT:
                        logging.warning("Timeout. Zamykam.")
                        click_image("closed.png")
                        final_status = "timeout"
                        skip_tactical_pause = True
                        break

                    if time.time() - last_wake > 90:
                        wake_mouse()
                        last_wake = time.time()
                    time.sleep(10)
            else:
                logging.warning("Brak wejścia do konkursu. Wracam.")
                click_image("closed.png")
                final_status = "error"
            
            sec_to_next = get_seconds_to_next_contest(schedule)
            min_to_next = sec_to_next / 60
            
            current_offset = 300
            if final_status != "won":
                logging.info("Brak wygranej -> Standardowy start (2min) przy następnym.")
                current_offset = 120
            
            if contest_start_time:
                time_since_start = (datetime.now() - contest_start_time).total_seconds() / 60
            else: time_since_start = 999
            
            logging.info(f"[Status] Wynik: {final_status}, Next: {int(min_to_next)}m")
            
            cond_farming = ((final_status == "won") or (time_since_start > 45)) and (min_to_next > 60)
            
            if cond_farming:
                logging.info("Uruchamiam FARMING.")
                run_farming_cycle()
                last_farming_time = time.time()
            
            logging.info("Powrót do mapy...")
            next_map_log_time = 0
            time.sleep(5)
        else:
            reg_mapa = load_region(settings.CSV_REGION_MAIN)
            visible_list = scan_screen_for_city(reg_mapa, silent=True)
            
            if not visible_list:
                if no_cities_start_time is None:
                    no_cities_start_time = time.time()
                else:
                    elapsed_no_cities = (time.time() - no_cities_start_time) / 60
                    if time.time() % 60 < 5:
                        logging.warning(f"[OSTRZEŻENIE] Brak miast od {int(elapsed_no_cities)} min. Restart za {int(15 - elapsed_no_cities)} min.")
                    
                    if elapsed_no_cities > 15:
                        logging.error("BRAK MIAST PRZEZ 15 MINUT! Uruchamiam RECONNECT...")
                        execute_emergency_reconnect(schedule, visited_cities)
                        no_cities_start_time = None
            else:
                no_cities_start_time = None
            
            visible_names = [item['city'] for item in visible_list]
            sec_to_next, next_city = get_seconds_to_next_visible_contest(schedule, visible_names)
            min_to_next = sec_to_next / 60
            
            if (min_to_next > 60) and (time.time() - last_farming_time > 45 * 60):
                logging.info(f"Długa przerwa ({int(min_to_next)}min). Uruchamiam FARMING.")
                run_farming_cycle()
                last_farming_time = time.time()
                next_map_log_time = 0
            elif min_to_next > 20:
                sleep_duration = sec_to_next - 900
                if sleep_duration > 0:
                    logging.info(f"Deep Sleep: Budzik za {int(sleep_duration)}s.")
                    wake_time = time.time() + sleep_duration
                    while time.time() < wake_time:
                        wake_mouse()
                        reg_check = load_region(settings.CSV_REGION_MAIN)
                        if not scan_screen_for_city(reg_check, silent=True):
                            logging.warning("BUDZIK: Brak miast podczas snu! Wybudzanie.")
                            no_cities_start_time = time.time() - 840 
                            break
                        time.sleep(120)
                    logging.info("Pobudka!")
                    next_map_log_time = 0
            else:
                if should_log:
                    if next_city: logging.info(f"Czekam... Najbliższy widoczny: {next_city} za {int(min_to_next)} min.")
                    else: logging.info("Czekam... Brak miast w widoku.")
                    wake_mouse()
                elif time.time() % 60 < 5:
                    wake_mouse()
                    
            now = time.time()
            for k in [c for c, t in visited_cities.items() if now - t > 3600]: del visited_cities[k]
            time.sleep(5)