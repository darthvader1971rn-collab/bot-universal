# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk  # <--- To odpowiada za nowoczesny wygląd
from tkinter import messagebox
from modules import sequence
import sys

def start_bot(active_modes):
    if not active_modes:
        messagebox.showwarning("Uwaga", "Nie wybrano żadnego trybu farmingu!\nBot będzie tylko czuwał.")
    
    root.withdraw()
    
    try:
        sequence.contest_loop(active_modes=active_modes)
    except KeyboardInterrupt:
        print("\nZatrzymano bota ręcznie.")
        sys.exit()
    except Exception as e:
        print(f"\nBłąd krytyczny: {e}")
        import traceback
        traceback.print_exc()

def on_start_click():
    modes = []
    if var_miasta.get(): modes.append("miasta")
    if var_magazyny.get(): modes.append("magazyny")
    if var_kalkulator.get(): modes.append("kalkulator")
    
    print(f"Uruchamiam bota. Wybrano tryby: {modes}")
    start_bot(modes)

if __name__ == "__main__":
    print("Bot konkursowy — Launcher")
    
    root = tk.Tk()
    root.title("Bot Konkursowy")
    
    # Wyśrodkowanie okna na ekranie
    window_width = 350
    window_height = 300
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    center_x = int(screen_width/2 - window_width/2)
    center_y = int(screen_height/2 - window_height/2)
    root.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')
    
    # Stylizacja
    style = ttk.Style()
    style.theme_use('vista') # Próba użycia stylu systemowego (vista/xpnative/winnative)
    
    # Ramka główna dla ładniejszego odstępu
    main_frame = ttk.Frame(root, padding="20")
    main_frame.pack(fill=tk.BOTH, expand=True)

    label = ttk.Label(main_frame, text="Wybierz aktywne strategie:", font=("Segoe UI", 12, "bold"))
    label.pack(pady=(0, 20))
    
    # Zmienne logiczne
    var_miasta = tk.BooleanVar(value=True)
    var_magazyny = tk.BooleanVar(value=False)
    var_kalkulator = tk.BooleanVar(value=False)
    
    # --- NOWOCZESNE CHECKBOXY (TTK) ---
    c1 = ttk.Checkbutton(main_frame, text="Miasta (Standard)", variable=var_miasta)
    c1.pack(pady=5, anchor="w", padx=20)
    
    c2 = ttk.Checkbutton(main_frame, text="Magazyny (Standard)", variable=var_magazyny)
    c2.pack(pady=5, anchor="w", padx=20)
    
    c3 = ttk.Checkbutton(main_frame, text="Kalkulator (Timer)", variable=var_kalkulator)
    c3.pack(pady=5, anchor="w", padx=20)
    
    # Przycisk startu
    # Dodajemy pustą przestrzeń
    tk.Label(main_frame, text="").pack()
    
    btn = tk.Button(main_frame, text="URUCHOM BOTA", command=on_start_click, 
                    bg="#28a745", fg="white", font=("Segoe UI", 11, "bold"), 
                    relief="flat", padx=20, pady=5)
    btn.pack(pady=20)
    
    root.mainloop()