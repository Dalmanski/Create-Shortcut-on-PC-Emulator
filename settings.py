import os
import sys
import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

SETTINGS_FILE = os.path.join(
    os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else __file__),
    "settings.json"
)

def detect_paths():
    gpg_path = os.path.expandvars(r"%ProgramFiles%\Google\Play Games")
    ldplayer_path = os.path.expandvars(r"%ProgramFiles%\LDPlayer9\dnconsole.exe")
    return {
        "gpg_path": gpg_path if os.path.exists(gpg_path) else "",
        "ldplayer_path": ldplayer_path if os.path.exists(ldplayer_path) else ""
    }

def load_settings():
    default_paths = detect_paths()
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            settings = json.load(f)
    else:
        settings = {}

    return {
        "lang": settings.get("lang", "en"),
        "country": settings.get("country", "PH"),
        "GooglePlayGames_path": settings.get("GooglePlayGames_path", default_paths["gpg_path"]),
        "LDPlayer9_path": settings.get("LDPlayer9_path", default_paths["ldplayer_path"]),
        "GooglePlayGames_needed": settings.get("GooglePlayGames_needed", True),
        "LDPlayer9_needed": settings.get("LDPlayer9_needed", True),
    }

def save_settings(lang, country, gpg_path, ld_path, gpg_needed, ld_needed):
    data = {
        "lang": lang,
        "country": country,
        "GooglePlayGames_path": gpg_path,
        "LDPlayer9_path": ld_path,
        "GooglePlayGames_needed": gpg_needed,
        "LDPlayer9_needed": ld_needed
    }
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    messagebox.showinfo("Saved", "Settings saved successfully!")

def open_folder_dialog(label_var):
    folder_path = filedialog.askdirectory()
    if folder_path:
        label_var.set(folder_path)

def open_file_dialog_for_ldplayer(label_var):
    file_path = filedialog.askopenfilename(
        title="Select dnconsole.exe",
        filetypes=[("Executable", "dnconsole.exe"), ("All Files", "*.*")]
    )
    if file_path:
        if os.path.basename(file_path).lower() != "dnconsole.exe":
            messagebox.showerror("Invalid File", "Invalid file, please select dnconsole.exe")
            return
        label_var.set(file_path)

def center_window(window):
    window.update_idletasks()
    width = window.winfo_width()
    height = window.winfo_height()
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x = (screen_width - width) // 2
    y = ((screen_height - height) // 2) - 30
    window.geometry(f"+{x}+{y}")

def open_settings_popup(parent=None):
    settings = load_settings()

    win = tk.Toplevel(parent)
    win.title("Settings")
    win.geometry("600x320")
    win.configure(bg="#1e1e1e")
    center_window(win)

    container = tk.Frame(win, bg="#1e1e1e", padx=30, pady=20)
    container.pack(expand=True)

    for i in range(6):
        container.grid_rowconfigure(i, pad=10)
    container.grid_columnconfigure(0, weight=0)
    container.grid_columnconfigure(1, weight=1)
    container.grid_columnconfigure(2, weight=0)

    tk.Label(container, text="Language:", fg="white", bg="#1e1e1e").grid(row=0, column=0, sticky="e", padx=10)
    lang_var = tk.StringVar(value=settings.get("lang", "en"))
    lang_menu = ttk.Combobox(container, textvariable=lang_var, values=["en", "tl", "ja", "ko", "zh", "es", "fr"], state="readonly")
    lang_menu.grid(row=0, column=1, sticky="w", padx=10)

    tk.Label(container, text="Country:", fg="white", bg="#1e1e1e").grid(row=1, column=0, sticky="e", padx=10)
    country_var = tk.StringVar(value=settings.get("country", "PH"))
    country_menu = ttk.Combobox(container, textvariable=country_var, values=["PH", "US", "JP", "KR", "CN", "IN", "DE"], state="readonly")
    country_menu.grid(row=1, column=1, sticky="w", padx=10)

    tk.Label(container, text="Google Play Games:", fg="white", bg="#1e1e1e").grid(row=2, column=0, sticky="e", padx=10)
    gpg_var = tk.StringVar(value=settings.get("GooglePlayGames_path", "File not found"))
    gpg_label = tk.Label(container, textvariable=gpg_var, fg="#00bfff", bg="#1e1e1e", cursor="hand2", anchor="w", wraplength=360)
    gpg_label.grid(row=2, column=1, sticky="w", padx=10)
    gpg_label.bind("<Button-1>", lambda e: open_folder_dialog(gpg_var))

    gpg_needed_var = tk.BooleanVar(value=settings.get("GooglePlayGames_needed", True))
    tk.Checkbutton(container, text="Needed", variable=gpg_needed_var, bg="#1e1e1e", fg="white", activebackground="#1e1e1e", selectcolor="#1e1e1e").grid(row=2, column=2, sticky="w")

    tk.Label(container, text="LDPlayer 9:", fg="white", bg="#1e1e1e").grid(row=3, column=0, sticky="e", padx=10)
    ld_var = tk.StringVar(value=settings.get("LDPlayer9_path", "File not found"))
    ld_label = tk.Label(container, textvariable=ld_var, fg="#00bfff", bg="#1e1e1e", cursor="hand2", anchor="w", wraplength=360)
    ld_label.grid(row=3, column=1, sticky="w", padx=10)
    ld_label.bind("<Button-1>", lambda e: open_file_dialog_for_ldplayer(ld_var))

    ld_needed_var = tk.BooleanVar(value=settings.get("LDPlayer9_needed", True))
    tk.Checkbutton(container, text="Needed", variable=ld_needed_var, bg="#1e1e1e", fg="white", activebackground="#1e1e1e", selectcolor="#1e1e1e").grid(row=3, column=2, sticky="w")

    save_btn = tk.Button(container, text="Save Settings", command=lambda: save_settings(
        lang_var.get(),
        country_var.get(),
        gpg_var.get(),
        ld_var.get(),
        gpg_needed_var.get(),
        ld_needed_var.get()
    ))
    save_btn.grid(row=5, column=0, columnspan=3, pady=20)

    win.mainloop()

if __name__ == "__main__":
    open_settings_popup()
