import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image

# Definicje szerokości dla standardów
RESOLUTIONS = {
    "4K (3840 px)": 3840,
    "2K (2560 px)": 2560,
    "FHD (1920 px)": 1920
}

class ResizerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Zmiana Rozdzielczości (FHD / 2K / 4K)")
        self.root.geometry("500x350")

        # Zmienne
        self.src_folder = tk.StringVar()
        self.dst_folder = tk.StringVar()
        self.base_res = tk.StringVar(value="FHD (1920 px)")
        self.target_res = tk.StringVar(value="4K (3840 px)")

        # GUI Layout
        self.create_widgets()

    def create_widgets(self):
        # Sekcja folderów
        tk.Label(self.root, text="1. Wybierz foldery", font=("Arial", 10, "bold")).pack(pady=(10, 5))
        
        frame_src = tk.Frame(self.root)
        frame_src.pack(pady=2, fill='x', padx=20)
        tk.Button(frame_src, text="Folder Źródłowy", command=self.select_src, width=15).pack(side='left')
        tk.Entry(frame_src, textvariable=self.src_folder, state='readonly').pack(side='left', fill='x', expand=True, padx=5)

        frame_dst = tk.Frame(self.root)
        frame_dst.pack(pady=2, fill='x', padx=20)
        tk.Button(frame_dst, text="Folder Docelowy", command=self.select_dst, width=15).pack(side='left')
        tk.Entry(frame_dst, textvariable=self.dst_folder, state='readonly').pack(side='left', fill='x', expand=True, padx=5)

        # Sekcja rozdzielczości
        tk.Label(self.root, text="2. Wybierz formaty", font=("Arial", 10, "bold")).pack(pady=(20, 5))
        
        frame_res = tk.Frame(self.root)
        frame_res.pack(pady=5)

        tk.Label(frame_res, text="Z (Bazowa):").grid(row=0, column=0, padx=5)
        self.combo_base = ttk.Combobox(frame_res, textvariable=self.base_res, values=list(RESOLUTIONS.keys()), state="readonly", width=20)
        self.combo_base.grid(row=0, column=1, padx=5)

        tk.Label(frame_res, text="NA (Docelowa):").grid(row=0, column=2, padx=5)
        self.combo_target = ttk.Combobox(frame_res, textvariable=self.target_res, values=list(RESOLUTIONS.keys()), state="readonly", width=20)
        self.combo_target.grid(row=0, column=3, padx=5)

        # Przycisk start
        tk.Button(self.root, text="URUCHOM SKALOWANIE", command=self.process_images, bg="#dddddd", font=("Arial", 10, "bold"), height=2).pack(pady=30, fill='x', padx=50)

    def select_src(self):
        path = filedialog.askdirectory(title="Wybierz folder źródłowy")
        if path:
            self.src_folder.set(path)
            # Domyślnie ustaw docelowy na ten sam, jeśli jest pusty
            if not self.dst_folder.get():
                self.dst_folder.set(path)

    def select_dst(self):
        path = filedialog.askdirectory(title="Wybierz folder docelowy")
        if path:
            self.dst_folder.set(path)

    def process_images(self):
        src = self.src_folder.get()
        dst = self.dst_folder.get()
        
        if not src or not dst:
            messagebox.showerror("Błąd", "Musisz wybrać folder źródłowy i docelowy!")
            return

        # Obliczanie skali
        try:
            w_base = RESOLUTIONS[self.base_res.get()]
            w_target = RESOLUTIONS[self.target_res.get()]
            scale_factor = w_target / w_base
        except Exception:
            messagebox.showerror("Błąd", "Nieprawidłowy wybór rozdzielczości.")
            return

        files = [f for f in os.listdir(src) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff'))]
        
        if not files:
            messagebox.showwarning("Pusto", "Brak plików graficznych w folderze źródłowym.")
            return

        count = 0
        os.makedirs(dst, exist_ok=True) # Upewnij się, że folder docelowy istnieje

        print(f"--- START ---")
        print(f"Mnożnik skali: {scale_factor:.2f}x (z {w_base} na {w_target})")

        for file in files:
            src_path = os.path.join(src, file)
            dst_path = os.path.join(dst, file)
            
            try:
                with Image.open(src_path) as img:
                    # Oblicz nowe wymiary
                    new_width = int(img.width * scale_factor)
                    new_height = int(img.height * scale_factor)
                    
                    # Skalowanie (LANCZOS dla najlepszej jakości)
                    resized_img = img.resize((new_width, new_height), Image.LANCZOS)
                    
                    # Zapis
                    resized_img.save(dst_path)
                    print(f"Przetworzono: {file} -> {new_width}x{new_height}")
                    count += 1
            except Exception as e:
                print(f"Błąd przy pliku {file}: {e}")

        messagebox.showinfo("Gotowe", f"Zakończono przetwarzanie.\nPrzeskalowano plików: {count}\nZapisano w: {dst}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ResizerApp(root)
    root.mainloop()