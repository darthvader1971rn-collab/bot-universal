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
    pyautogui.dragRel(0, -200, duration=1.0, button='left')
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

def get_target_click_time(city, schedule):
    if city not in schedule: return None, False, None
    now = datetime.now()
    best_target = None
    best_start = None
    
    for hour, minute in schedule[city]:
        start_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        click_time = start_time - timedelta(seconds=120) 
        end_time = start_time + timedelta(minutes=15)
        
        if click_time <= now < end_time:
            return click_time, True, start_time
        
        if now < click_time:
            if best_target is None or click_time < best_target:
                best_target = click_time
                best_start = start_time
                
    return best_target, False, best_start

def get_seconds_to_next_visible_contest(schedule, visible_cities_names):
    """
    Sprawdza czas do konkursu TYLKO dla miast widocznych na ekranie.
    """
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
    
    # Jeśli nie ma żadnego konkursu w widocznych miastach (lub brak miast),
    # zwracamy dużą liczbę, aby umożliwić farming (bo nic nas nie goni).
    if min_diff == float('inf'): return 999999, None
    return min_diff, nearest_city

def scan_screen_for_city(region, specific_city=None):
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
                    logging.info(f"[MAPA] Rozpoznano: '{t}' -> Dopasowano: '{matched_city}'")
                    gx = region[0] + data["left"][i] + data["width"][i] // 2
                    gy = region[1] + data["top"][i] + data["height"][i] // 2
                    found_candidates.append({'city': matched_city, 'x': gx, 'y': gy})
    if specific_city: return None
    return found_candidates

def find_and_click_city(schedule, visited_cities, farming_mode=False):
    region = load_region(settings.CSV_REGION_MAIN)
    if region == (0,0,0,0): return False, None
    
    candidates_data = scan_screen_for_city(region)
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
        target_time, is_active, real_start = get_target_click_time(miasto, schedule)
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
    
    if wait_s > 900: 
        return False, None 
    
    if wait_s > 0:
        logging.info(f"Czekam na {best['city']} (Start -120s za: {int(wait_s)}s)...")
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

def wake_mouse():
    pyautogui.moveTo(200, 200, duration=0.2)
    pyautogui.moveRel(10, 0, duration=0.2)
    pyautogui.moveRel(-10, 0, duration=0.2)
    logging.info("Ruch myszką (Wake Up).")

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
            
            logging.info("[FARMING] Próba zamknięcia okna...")
            closed_ok = False
            for _ in range(3):
                if click_image("closed.png", retry=2):
                    time.sleep(1)
                    try:
                        if not pyautogui.locateOnScreen(os.path.join(settings.GRAPHICS_PATH, "closed.png"), confidence=0.8, grayscale=True):
                            closed_ok = True
                            break
                    except: pass
            if not closed_ok: logging.warning("[FARMING] Nie udało się potwierdzić zamknięcia okna.")
            time.sleep(5)
        else: logging.warning("[FARMING] Brak 'lista_pociagow.png'")
    else: logging.error("Błąd pliku prostokat_pociagi.csv!")

def contest_loop():
    schedule_usa = load_schedule("miasta - USA.txt")
    schedule_eu = load_schedule("miasta - Europa_Afryka.txt")
    schedule = {**schedule_usa, **schedule_eu}
    visited_cities = {}
    skip_tactical_pause = False
    last_farming_time = 0
    last_idle_wake = time.time()
    
    logging.info("Bot uruchomiony (Wersja: Visible Only Check).")

    while True:
        # Szukanie miasta konkursowego
        found, contest_start_time = find_and_click_city(schedule, visited_cities)
        
        if found:
            logging.info("Wchodzenie w interfejs konkursu...")
            reg_listing = load_region(settings.CSV_REGION_LISTING)
            click_image("schedule_assistant.png", region=reg_listing)
            click_image("adopt_schedule.png", region=reg_listing)
            click_image("select_all.png", region=reg_listing)
            time.sleep(1)
            
            success = handle_lets_go_logic()
            if not success:
                logging.warning("Nie udało się przejść dalej. Wracam.")
                click_image("closed.png")
                time.sleep(5)
                continue
            
            if skip_tactical_pause:
                logging.info("Szybki start (Timeout) - POMIJAM pauzę.")
                skip_tactical_pause = False
            else:
                time_diff = (contest_start_time - datetime.now()).total_seconds() if contest_start_time else 0
                if time_diff <= 5:
                    logging.info(f"Szybki start (Opóźnienie) - POMIJAM pauzę.")
                else:
                    wait_time = max(10, int(time_diff))
                    logging.info(f"Pauza taktyczna: czekam {wait_time}s...")
                    time.sleep(wait_time)
            
            contest_entered = False
            logging.info("Szukam Sign Up...")
            start_signup_search = time.time()
            while time.time() - start_signup_search < 95:
                if reg_listing != (0,0,0,0):
                    if click_image("sign_up.png", retry=2, region=reg_listing):
                        contest_entered = True
                        break
                reg_wagony = load_region(settings.CSV_REGION_WAGONY)
                if not contest_entered:
                    if click_image("buy_railroad_cars.png", retry=2, region=reg_wagony):
                        logging.info("Kupiono wagony.")
                        contest_entered = True
                        break
                if not contest_entered:
                    if reg_wagony != (0,0,0,0):
                        text = ocr_region(reg_wagony, debug_filename="debug_wagons.png")
                        if "Buy" in text and "railroad" in text:
                            logging.info("Kupiono wagony (OCR).")
                            center_x = reg_wagony[0] + reg_wagony[2] // 2
                            center_y = reg_wagony[1] + reg_wagony[3] // 2
                            pyautogui.click(center_x, center_y)
                            time.sleep(2)
                            contest_entered = True
                            break
                if not contest_entered:
                    try:
                        if click_from_csv_center(settings.CSV_REGION_SIGN_UP, "Sign Up (CSV)"):
                            contest_entered = True
                            break
                    except: pass
                time.sleep(30)

            final_status = "unknown"
            if contest_entered:
                time.sleep(1)
                perform_drag_from_listing()
                last_drag_time = time.time()
                drag_count = 1
                logging.info("Czekam 30s...")
                time.sleep(30)
                logging.info("Monitoring...")
                start_time = time.time()
                last_wake = time.time()
                next_log_time = time.time() + 60
                
                while True:
                    elapsed_drag = time.time() - last_drag_time
                    if (elapsed_drag > 90) and (drag_count < 9):
                        drag_count += 1
                        logging.info(f"Drag #{drag_count}/9")
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
                            skip_tactical_pause = False
                            final_status = status
                            break
                    
                    if time.time() - start_time > settings.CONTEST_TIMEOUT:
                        logging.warning("Timeout. Zamykam.")
                        click_image("closed.png")
                        skip_tactical_pause = True
                        final_status = "timeout"
                        break

                    if time.time() - last_wake > 90:
                        wake_mouse()
                        last_wake = time.time()
                    time.sleep(10)
            else:
                logging.warning("Brak Sign Up. Wracam.")
                click_image("closed.png")
                final_status = "error"
            
            # --- LOGIKA FARMINGU (PO KONKURSIE) ---
            if contest_start_time:
                time_since_start = (datetime.now() - contest_start_time).total_seconds() / 60
            else: time_since_start = 999
            
            # 1. Sprawdzamy, co WIDZIMY
            reg_mapa = load_region(settings.CSV_REGION_MAIN)
            visible_list = scan_screen_for_city(reg_mapa)
            visible_names = [item['city'] for item in visible_list]
            
            # 2. Liczymy czas TYLKO do widocznych
            sec_to_next, next_city = get_seconds_to_next_visible_contest(schedule, visible_names)
            min_to_next = sec_to_next / 60
            
            logging.info(f"[Farming Check] Status: {final_status}, Minęło: {int(time_since_start)}min, Następny WIDOCZNY za: {int(min_to_next)}min")
            
            condition_1 = (final_status == "won") or (time_since_start > 45)
            condition_2 = (min_to_next > 30)
            
            if condition_1 and condition_2:
                logging.info("Uruchamiam FARMING.")
                run_farming_cycle()
                last_farming_time = time.time()
            else:
                logging.info("Warunki farmingu niespełnione.")
            
            logging.info("Powrót do mapy...")
            time.sleep(5)
        else:
            # --- TRYB IDLE ---
            if time.time() - last_idle_wake > 60:
                wake_mouse()
                last_idle_wake = time.time()

            reg_mapa = load_region(settings.CSV_REGION_MAIN)
            visible_list = scan_screen_for_city(reg_mapa)
            visible_names = [item['city'] for item in visible_list]
            
            sec_to_next_visible, next_city_visible = get_seconds_to_next_visible_contest(schedule, visible_names)
            min_to_next_visible = sec_to_next_visible / 60
            
            if (min_to_next_visible > 30) and (time.time() - last_farming_time > 45 * 60):
                logging.info(f"Długa przerwa w widoku ({int(min_to_next_visible)}min). Uruchamiam FARMING.")
                run_farming_cycle()
                last_farming_time = time.time()
            else:
                if time.time() % 60 < 5:
                    if next_city_visible:
                        logging.info(f"Czekam... Najbliższy widoczny: {next_city_visible} za {int(min_to_next_visible)} min.")
                    else:
                        logging.info("Czekam... Brak miast konkursowych w obecnym widoku.")
            
            now = time.time()
            for k in [c for c, t in visited_cities.items() if now - t > 3600]: del visited_cities[k]
            time.sleep(5)