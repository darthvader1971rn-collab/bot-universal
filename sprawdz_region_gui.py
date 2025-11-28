# -*- coding: utf-8 -*-
import pyautogui
import csv
import os
import time
import tkinter as tk
from tkinter import filedialog

def zrob_wycinek_z_gui():
    print("--- DIAGNOSTYKA REGIONU (GUI) ---")
    
    # 1. Inicjalizacja Tkinter (ukrywamy główne okno)
    root = tk.Tk()
    root.withdraw() 

    # 2. Otwarcie okna wyboru pliku
    print("Otwieram okno wyboru pliku...")
    sciezka_csv = filedialog.askopenfilename(
        title="Wybierz plik CSV z definicją regionu",
        filetypes=[("Pliki CSV", "*.csv"), ("Wszystkie pliki", "*.*")]
    )

    # Sprawdzenie czy użytkownik coś wybrał
    if not sciezka_csv:
        print("[ANULOWANO] Nie wybrano żadnego pliku.")
        return

    print(f"[WYBRANO] {sciezka_csv}")

    # 3. Wczytanie współrzędnych
    try:
        with open(sciezka_csv, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter=";")
            row = next(reader)
            x = int(row["LewyGorny_X"])
            y = int(row["LewyGorny_Y"])
            w = int(row["Szerokosc"])
            h = int(row["Wysokosc"])
            
        print(f"[DANE] Region: X={x}, Y={y}, Szer={w}, Wys={h}")
        
    except Exception as e:
        print(f"[BŁĄD] Nie udało się odczytać danych z CSV: {e}")
        print("Upewnij się, że plik ma nagłówki: LewyGorny_X;LewyGorny_Y;Szerokosc;Wysokosc")
        return

    # 4. Odliczanie i zrzut
    print("\n>>> PRZYGOTUJ EKRAN GRY! <<<")
    for i in range(3, 0, -1):
        print(f"Zrzut za {i}...")
        time.sleep(1)
    
    try:
        # Budujemy ścieżkę do pliku wynikowego w tym samym folderze co CSV
        folder_pliku = os.path.dirname(sciezka_csv)
        nazwa_zrzutu = os.path.join(folder_pliku, "PODGLAD.png")
        
        screenshot = pyautogui.screenshot(region=(x, y, w, h))
        screenshot.save(nazwa_zrzutu)
        
        print(f"\n[SUKCES] Zapisano obraz: {nazwa_zrzutu}")
        print("-> Otwórz ten plik i sprawdź, czy widać na nim ikony.")
        
        # Opcjonalnie: Automatyczne otwarcie obrazka (działa na Windows)
        os.startfile(nazwa_zrzutu)
        
    except Exception as e:
        print(f"[BŁĄD] Nie udało się zrobić screenshota: {e}")

if __name__ == "__main__":
    zrob_wycinek_z_gui()
    # input("\nNaciśnij Enter, aby zamknąć...") # Opcjonalne, jeśli konsola zamyka się za szybko