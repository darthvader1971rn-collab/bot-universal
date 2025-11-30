# -*- coding: utf-8 -*-
import pyautogui
import csv
import os
import time
import tkinter as tk
from tkinter import filedialog
import pytesseract
from PIL import Image, ImageOps, ImageFilter
import settings

# Konfiguracja Tesseracta
pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_PATH

def testuj_tekst_ocr():
    print("=== TESTER OCR: WYPISYWANIE TEKSTU ===")
    
    root = tk.Tk()
    root.withdraw()

    while True:
        print("\n" + "="*50)
        print("1. Wybierz plik CSV w okienku...")
        
        sciezka_csv = filedialog.askopenfilename(
            title="Wybierz plik CSV regionu",
            filetypes=[("Pliki CSV", "*.csv")]
        )
        
        if not sciezka_csv:
            if input("Zakończyć? (t/n): ").lower() == 't': break
            else: continue

        print(f"[PLIK]: {os.path.basename(sciezka_csv)}")

        # Wczytanie regionu
        try:
            with open(sciezka_csv, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f, delimiter=";")
                row = next(reader)
                x = int(row["LewyGorny_X"])
                y = int(row["LewyGorny_Y"])
                w = int(row["Szerokosc"])
                h = int(row["Wysokosc"])
        except Exception as e:
            print(f"[BŁĄD CSV]: {e}")
            continue

        print("2. Ustaw ekran gry! (Zrzut za 3 sekundy)")
        for i in range(3, 0, -1):
            print(f"{i}...")
            time.sleep(1)

        try:
            # Zrzut
            screenshot = pyautogui.screenshot(region=(x, y, w, h))
            
            # Obróbka (Musi być taka sama jak w sequence.py dla list)
            width, height = screenshot.size
            processed = screenshot.resize((width * 2, height * 2), Image.BICUBIC)
            gray = ImageOps.grayscale(processed)
            sharp = gray.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))
            final_img = ImageOps.autocontrast(sharp, cutoff=5)
            
            # Zapis podglądu (żebyś widział co poszło do OCR)
            nazwa_zrzutu = "PODGLAD_OCR.png"
            final_img.save(nazwa_zrzutu)
            os.startfile(nazwa_zrzutu) # Otwiera obrazek

            # Wykonanie OCR
            config = "--psm 6 --oem 1 -l eng"
            text = pytesseract.image_to_string(final_img, config=config)
            
            # --- WYPISANIE WYNIKU ---
            print("\n" + "#"*30)
            print(">>> ROZPOZNANY TEKST (START) <<<")
            print("#"*30 + "\n")
            
            print(text.strip())
            
            print("\n" + "#"*30)
            print(">>> ROZPOZNANY TEKST (KONIEC) <<<")
            print("#"*30)
            
            # Szybka analiza pod kątem wygranej (dla Twojej wygody)
            if settings.PLAYER_NICK in text:
                print(f"\n[INFO] Twój nick ({settings.PLAYER_NICK}) ZOSTAL znaleziony w tekście.")
                if "Completed" in text:
                    print("[SUKCES] Znaleziono też 'Completed' - bot uznałby wygraną.")
            else:
                print(f"\n[UWAGA] Twój nick ({settings.PLAYER_NICK}) NIE ZOSTAL znaleziony.")

        except Exception as e:
            print(f"[BŁĄD]: {e}")

        if input("\nSprawdzić inny region? (t/n): ").lower() != 't':
            break

if __name__ == "__main__":
    testuj_tekst_ocr()