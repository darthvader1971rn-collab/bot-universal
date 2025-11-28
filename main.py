# -*- coding: utf-8 -*-
from modules import sequence  # <--- Importujemy z folderu modules

if __name__ == "__main__":
    print("Bot konkursowy — start")
    try:
        # Uruchamiamy funkcję z pliku sequence.py
        sequence.contest_loop()
    except KeyboardInterrupt:
        print("\nZatrzymano bota ręcznie.")
    except Exception as e:
        print(f"\nWystąpił błąd krytyczny: {e}")
        import traceback
        traceback.print_exc() # To pokaże dokładne miejsce błędu
        input("Naciśnij Enter, aby zamknąć...")