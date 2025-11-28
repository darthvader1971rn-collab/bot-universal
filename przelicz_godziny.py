# -*- coding: utf-8 -*-
import os
import shutil
from datetime import datetime, timedelta

def cofnij_godzine_w_pliku(nazwa_pliku):
    """
    Odejmuje 1 godzinę od czasu w każdej linii pliku formatu 'HH:MM - Miasto'
    """
    if not os.path.exists(nazwa_pliku):
        print(f"Błąd: Plik '{nazwa_pliku}' nie istnieje.")
        return

    # 1. Tworzenie kopii zapasowej
    backup_file = nazwa_pliku + ".bak"
    shutil.copy(nazwa_pliku, backup_file)
    print(f"Utworzono kopię zapasową: {backup_file}")

    nowe_linie = []
    
    # 2. Przetwarzanie linii
    with open(nazwa_pliku, 'r', encoding='utf-8') as f:
        for line in f:
            # Sprawdź czy linia ma format "HH:MM - Miasto"
            if " - " in line:
                try:
                    czas_str, reszta = line.strip().split(" - ", 1)
                    
                    # Konwersja na obiekt daty
                    czas_obj = datetime.strptime(czas_str.strip(), "%H:%M")
                    
                    # Odejmowanie 1 godziny
                    nowy_czas_obj = czas_obj - timedelta(hours=1)
                    
                    # Formatowanie z powrotem na tekst
                    nowy_czas_str = nowy_czas_obj.strftime("%H:%M")
                    
                    # Złożenie nowej linii
                    nowe_linie.append(f"{nowy_czas_str} - {reszta}\n")
                except ValueError:
                    # Jeśli linia nie pasuje do formatu, przepisz ją bez zmian
                    print(f"Pominięto linię (zły format): {line.strip()}")
                    nowe_linie.append(line)
            else:
                nowe_linie.append(line)

    # 3. Zapisywanie zmian
    with open(nazwa_pliku, 'w', encoding='utf-8') as f:
        f.writelines(nowe_linie)
    
    print(f"Gotowe! Przeliczono godziny w pliku: {nazwa_pliku}")

# --- KONFIGURACJA ---
if __name__ == "__main__":
    print("--- PRZELICZANIE GODZIN (-1h) ---")
    
    # Tutaj wpisz nazwę pliku, który chcesz przeliczyć
    plik_do_przerobienia = input("Podaj nazwę pliku (np. miasta - USA.txt): ")
    
    # Usuń ewentualne cudzysłowy jeśli kopiujesz ścieżkę
    plik_do_przerobienia = plik_do_przerobienia.strip('"') 
    
    cofnij_godzine_w_pliku(plik_do_przerobienia)
    
    input("\nNaciśnij Enter, aby zakończyć...")