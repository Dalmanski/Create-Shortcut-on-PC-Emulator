import os
import sys
import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from jaypy import centerwindow

SETTINGS_FILE = os.path.join(
    os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else __file__),
    "settings.json"
)

_settings_window = None

def detect_paths():
    gpg_path = os.path.expandvars(r"%ProgramFiles%\Google\Play Games")
    ldplayer_path = os.path.expandvars(r"%ProgramFiles%\LDPlayer9\dnconsole.exe")
    return {
        "gpg_path": gpg_path if os.path.exists(gpg_path) else "",
        "ldplayer_path": ldplayer_path if os.path.exists(ldplayer_path) else ""
    }

def load_settings():
    default_paths = detect_paths()
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8-sig") as f:
                settings = json.load(f)
        except Exception:
            settings = {}
    else:
        settings = {}
    return {
        "lang": settings.get("lang", "en"),
        "country": settings.get("country", "PH"),
        "GooglePlayGames_path": settings.get("GooglePlayGames_path", default_paths["gpg_path"]),
        "LDPlayer9_path": settings.get("LDPlayer9_path", default_paths["ldplayer_path"]),
        "GooglePlayGames_needed": settings.get("GooglePlayGames_needed", True),
        "LDPlayer9_needed": settings.get("LDPlayer9_needed", True),
        "shortcuts_folder": settings.get("shortcuts_folder", desktop),
        "LDPlayer9_index": settings.get("LDPlayer9_index", 0)
    }

def save_settings(lang, country, gpg_path, ld_path, gpg_needed, ld_needed, shortcuts_folder, ld_index=0, show_message=True):
    data = {
        "lang": lang,
        "country": country,
        "GooglePlayGames_path": gpg_path,
        "LDPlayer9_path": ld_path,
        "GooglePlayGames_needed": gpg_needed,
        "LDPlayer9_needed": ld_needed,
        "shortcuts_folder": shortcuts_folder,
        "LDPlayer9_index": ld_index
    }
    tmp = SETTINGS_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8-sig") as f:
        json.dump(data, f, indent=4)
        f.flush()
        try:
            os.fsync(f.fileno())
        except Exception:
            pass
    try:
        os.replace(tmp, SETTINGS_FILE)
    except Exception:
        with open(SETTINGS_FILE, "w", encoding="utf-8-sig") as f:
            json.dump(data, f, indent=4)
    if show_message:
        try:
            messagebox.showinfo("Saved", "Settings saved successfully!")
        except Exception:
            pass

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
            try:
                messagebox.showerror("Invalid File", "Invalid file, please select dnconsole.exe")
            except Exception:
                pass
            return
        label_var.set(file_path)

def open_settings_popup(parent=None):
    global _settings_window
    if _settings_window and _settings_window.winfo_exists():
        try:
            _settings_window.lift()
            _settings_window.focus_force()
        except Exception:
            pass
        return _settings_window

    settings = load_settings()
    win = tk.Toplevel(parent)
    _settings_window = win
    win.title("Settings")
    win.geometry("620x300")
    win.configure(bg="#1e1e1e")
    centerwindow(win, offsety=-40)

    container = tk.Frame(win, bg="#1e1e1e", padx=18, pady=14)
    container.pack(expand=True, fill="both")

    for i in range(7):
        container.grid_rowconfigure(i, pad=8)
    container.grid_columnconfigure(0, weight=0)
    container.grid_columnconfigure(1, weight=1)
    container.grid_columnconfigure(2, weight=0)

    tk.Label(container, text="Language:", fg="white", bg="#1e1e1e").grid(row=0, column=0, sticky="e", padx=8)
    lang_var = tk.StringVar(value=settings.get("lang", "en"))
    lang_menu = ttk.Combobox(container, textvariable=lang_var, values=["en", "tl", "ja", "ko", "zh", "es", "fr"], state="readonly")
    lang_menu.grid(row=0, column=1, sticky="w", padx=8)

    tk.Label(container, text="Country:", fg="white", bg="#1e1e1e").grid(row=1, column=0, sticky="e", padx=8)
    country_var = tk.StringVar(value=settings.get("country", "PH"))
    country_menu = ttk.Combobox(container, textvariable=country_var, values=["PH", "US", "JP", "KR", "CN", "IN", "DE"], state="readonly")
    country_menu.grid(row=1, column=1, sticky="w", padx=8)

    tk.Label(container, text="Google Play Games:", fg="white", bg="#1e1e1e").grid(row=2, column=0, sticky="e", padx=8)
    gpg_var = tk.StringVar(value=settings.get("GooglePlayGames_path", "File not found"))
    gpg_label = tk.Label(container, textvariable=gpg_var, fg="#00bfff", bg="#1e1e1e", cursor="hand2", anchor="w", wraplength=360)
    gpg_label.grid(row=2, column=1, sticky="w", padx=8)
    gpg_label.bind("<Button-1>", lambda e: open_folder_dialog(gpg_var))
    gpg_needed_var = tk.BooleanVar(value=settings.get("GooglePlayGames_needed", True))
    tk.Checkbutton(container, text="Needed", variable=gpg_needed_var, bg="#1e1e1e", fg="white", activebackground="#1e1e1e", selectcolor="#1e1e1e").grid(row=2, column=2, sticky="w")

    tk.Label(container, text="LDPlayer 9:", fg="white", bg="#1e1e1e").grid(row=3, column=0, sticky="e", padx=8)
    ld_var = tk.StringVar(value=settings.get("LDPlayer9_path", "File not found"))
    ld_label = tk.Label(container, textvariable=ld_var, fg="#00bfff", bg="#1e1e1e", cursor="hand2", anchor="w", wraplength=360)
    ld_label.grid(row=3, column=1, sticky="w", padx=8)
    ld_label.bind("<Button-1>", lambda e: open_file_dialog_for_ldplayer(ld_var))
    ld_needed_var = tk.BooleanVar(value=settings.get("LDPlayer9_needed", True))
    tk.Checkbutton(container, text="Needed", variable=ld_needed_var, bg="#1e1e1e", fg="white", activebackground="#1e1e1e", selectcolor="#1e1e1e").grid(row=3, column=2, sticky="w")

    tk.Label(container, text="Shortcuts Folder:", fg="white", bg="#1e1e1e").grid(row=4, column=0, sticky="e", padx=8)
    shortcuts_var = tk.StringVar(value=settings.get("shortcuts_folder", os.path.join(os.path.expanduser("~"), "Desktop")))
    shortcuts_label = tk.Label(container, textvariable=shortcuts_var, fg="#00bfff", bg="#1e1e1e", cursor="hand2", anchor="w", wraplength=360)
    shortcuts_label.grid(row=4, column=1, sticky="w", padx=8)
    def _browse_shortcuts_folder():
        folder = filedialog.askdirectory(title="Choose folder to save shortcuts and icons")
        if folder:
            shortcuts_var.set(folder)
    browse_btn = tk.Button(container, text="Browse", command=_browse_shortcuts_folder)
    browse_btn.grid(row=4, column=2, sticky="w", padx=6)

    ld_index_var = tk.StringVar(value=str(settings.get("LDPlayer9_index", 0)))
    tk.Label(container, text="LDPlayer Index:", fg="white", bg="#1e1e1e").grid(row=5, column=0, sticky="e", padx=8)
    ld_index_spin = tk.Spinbox(container, from_=0, to=9999, textvariable=ld_index_var, width=6, bd=0, relief="flat", highlightthickness=0)
    ld_index_spin.grid(row=5, column=1, sticky="w", padx=8)

    def _auto_save(*args):
        try:
            li = 0
            try:
                li = int(ld_index_var.get())
            except Exception:
                li = 0
            save_settings(
                lang_var.get(),
                country_var.get(),
                gpg_var.get(),
                ld_var.get(),
                gpg_needed_var.get(),
                ld_needed_var.get(),
                shortcuts_var.get(),
                ld_index=li,
                show_message=False
            )
        except Exception:
            pass

    lang_var.trace_add("write", _auto_save)
    country_var.trace_add("write", _auto_save)
    gpg_var.trace_add("write", _auto_save)
    ld_var.trace_add("write", _auto_save)
    shortcuts_var.trace_add("write", _auto_save)
    gpg_needed_var.trace_add("write", _auto_save)
    ld_needed_var.trace_add("write", _auto_save)
    ld_index_var.trace_add("write", _auto_save)

    def _on_close():
        global _settings_window
        try:
            _settings_window = None
        except Exception:
            pass
        try:
            win.destroy()
        except Exception:
            pass

    win.protocol("WM_DELETE_WINDOW", _on_close)
    return win
