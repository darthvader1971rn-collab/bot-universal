# -*- coding: utf-8 -*-
import pyautogui
import csv
import os
import tkinter as tk
from tkinter import filedialog

def wymiarowanie_z_zapisem():
    print("--- NARZĘDZIE DO WYMIAROWANIA (FORMAT PEŁNY - 6 KOLUMN) ---")
    
    # 1. Wybór pliku przez okienko
    root = tk.Tk()
    root.withdraw() # Ukrywamy główne okno
    
    print("Otwieram okno wyboru pliku do nadpisania...")
    sciezka_csv = filedialog.askopenfilename(
        title="Wybierz plik CSV do nadpisania",
        filetypes=[("Pliki CSV", "*.csv"), ("Wszystkie pliki", "*.*")]
    )

    if not sciezka_csv:
        print("[ANULOWANO] Nie wybrano pliku.")
        return

    print(f"[WYBRANO] {os.path.basename(sciezka_csv)}")
    print("-" * 40)

    # 2. Pomiar
    print("PRZYGOTUJ SIĘ DO POMIARU!")
    input("1. Najedź myszką na LEWY-GÓRNY róg przycisku i naciśnij ENTER w konsoli...")
    x1, y1 = pyautogui.position()
    print(f"   -> Poczatek (LG): ({x1}, {y1})")
    
    input("2. Najedź myszką na PRAWY-DOLNY róg przycisku i naciśnij ENTER w konsoli...")
    x2, y2 = pyautogui.position()
    print(f"   -> Koniec    (PD): ({x2}, {y2})")
    
    # 3. Obliczenia
    width = x2 - x1
    height = y2 - y1
    
    if width <= 0 or height <= 0:
        print("\n[BŁĄD] Zła kolejność! Prawy dolny róg musi być poniżej i na prawo.")
        return

    print("-" * 40)
    print(f"ZMIERZONO: X={x1}, Y={y1}, W={width}, H={height}")

    # 4. Zapis do pliku (Format 6 kolumn)
    potwierdzenie = input(f"Zapisać do '{os.path.basename(sciezka_csv)}' w starym formacie? (t/n): ")
    
    if potwierdzenie.lower() == 't':
        try:
            with open(sciezka_csv, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f, delimiter=';')
                
                # Zapisujemy nagłówek STARY (6 kolumn)
                writer.writerow(['LewyGorny_X', 'LewyGorny_Y', 'PrawyDolny_X', 'PrawyDolny_Y', 'Szerokosc', 'Wysokosc'])
                
                # Zapisujemy dane (obliczamy wszystko)
                writer.writerow([x1, y1, x2, y2, width, height])
            
            print(f"\n[SUKCES] Plik zaktualizowany (format 6 kolumn)!")
        except Exception as e:
            print(f"\n[BŁĄD] Nie udało się zapisać pliku: {e}")
    else:
        print("\n[ANULOWANO] Plik nie został zmieniony.")

if __name__ == "__main__":
    while True:
        wymiarowanie_z_zapisem()
        again = input("\nCzy chcesz zmierzyć kolejny plik? (t/n): ")
        if again.lower() != 't':
            break