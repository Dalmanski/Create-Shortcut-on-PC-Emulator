import os
import sys
import json
import tkinter as tk
from tkinter import messagebox, ttk
from win32com.client import Dispatch
import winshell
from google_play_scraper import search
import requests
from PIL import Image, ImageTk
from io import BytesIO
from help import open_help_popup
from settings import open_settings_popup
from jaypy import centerwindow

SETTINGS_FILE = os.path.join(
    os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else __file__),
    "settings.json"
)

def load_settings():
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_settings(data):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def relaunch():
    os.execl(sys.executable, sys.executable, *sys.argv)

def validate_settings(settings):
    gpg_needed = settings.get("GooglePlayGames_needed")
    ld_needed = settings.get("LDPlayer9_needed")
    gpg_path = settings.get("GooglePlayGames_path")
    ld_path = settings.get("LDPlayer9_path")

    gpg_valid = not gpg_needed or (gpg_path and os.path.exists(gpg_path))
    ld_valid = not ld_needed or (ld_path and os.path.exists(ld_path) and ld_path.lower().endswith("dnconsole.exe"))

    return gpg_valid and ld_valid

def create_shortcut(name, target, arguments="", icon=None):
    desktop = winshell.desktop()
    path = os.path.join(desktop, f"{name}.lnk")
    shell = Dispatch('WScript.Shell')
    shortcut = shell.CreateShortCut(path)
    shortcut.Targetpath = target
    if arguments:
        shortcut.Arguments = arguments
    if icon:
        shortcut.IconLocation = icon
    shortcut.WorkingDirectory = os.path.dirname(target)
    shortcut.save()
    return path

def download_icon(url, name):
    try:
        response = requests.get(url)
        response.raise_for_status()
        image = Image.open(BytesIO(response.content)).convert("RGBA")
        icon_path = os.path.join(os.getenv("TEMP"), f"{name}.ico")
        image.save(icon_path, format='ICO', sizes=[(64, 64)])
        return icon_path
    except Exception as e:
        print("Icon download error:", e)
        return None

class PlayStoreShortcutApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.settings = load_settings()
        if not validate_settings(self.settings):
            self.withdraw()
            messagebox.showinfo("Settings Required", "Please configure paths to Google Play Games and LDPlayer 9.")
            open_settings_popup()
            relaunch()
            return

        self.iconbitmap("icon.ico")
        self.title("Create Shortcut on PC Emulator")
        self.geometry("600x500")
        self.configure(bg="#1e1e1e")
        self.resizable(False, False)
        centerwindow(self, offsety=-40)

        self.search_results, self.image_refs, self.selected_item = [], [], None
        self._setup_styles()
        self._create_widgets()

    def _setup_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TLabel", background="#1e1e1e", foreground="#ffffff")
        style.configure("TButton", background="#292929", foreground="#ffffff", padding=6, relief="flat")
        style.map("TButton", background=[("active", "#444444")])
        style.configure("TEntry", fieldbackground="#2d2d2d", foreground="#ffffff")
        style.configure("TCombobox", arrowcolor="#ffffff")
        style.map("TCombobox",
                  fieldbackground=[("readonly", "#2d2d2d")],
                  selectbackground=[("readonly", "#2d2d2d")],
                  background=[("readonly", "#1e1e1e")],
                  foreground=[("readonly", "white")])

    def _create_widgets(self):
        search_frame = tk.Frame(self, bg="#1e1e1e")
        search_frame.pack(pady=15, fill=tk.X, padx=20)
        ttk.Label(search_frame, text="🔍 Search Google Play:").pack(anchor="w")

        self.search_var = tk.StringVar()
        entry = ttk.Entry(search_frame, textvariable=self.search_var)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        entry.bind("<Return>", self.perform_search)
        ttk.Button(search_frame, text="Search", command=self.perform_search).pack(side=tk.LEFT, padx=10)

        btn_frame = tk.Frame(self, bg="#1e1e1e")
        btn_frame.place(relx=1.0, rely=1.0, x=-10, y=-10, anchor="se")

        self._create_tool_button(btn_frame, "⚙️", open_settings_popup).pack(side=tk.RIGHT, padx=5)
        self._create_tool_button(btn_frame, "❓", open_help_popup).pack(side=tk.RIGHT)

        self.result_frame = tk.Frame(self, bg="#1e1e1e")
        self.result_frame.pack(padx=20, pady=10, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(self.result_frame, bg="#2d2d2d", height=240, highlightthickness=0)
        self.scrollbar = tk.Scrollbar(self.result_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg="#2d2d2d")
        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.empty_label = ttk.Label(self.canvas, text="Please search the game", foreground="#888888")
        self.empty_label.place(relx=0.5, rely=0.5, anchor="center")
        self.loading_label = ttk.Label(self.canvas, text="🔄 Loading...", foreground="#aaaaaa")

        self.pkg_label_var = tk.StringVar(value="-")
        pkg_frame = tk.Frame(self, bg="#1e1e1e")
        pkg_frame.pack(pady=10, padx=20, fill="x")
        ttk.Label(pkg_frame, text="📦 Selected Package:").pack(side=tk.LEFT)
        pkg_label = ttk.Label(pkg_frame, textvariable=self.pkg_label_var, foreground="#cccccc", cursor="hand2")
        pkg_label.pack(side=tk.LEFT, padx=10)
        pkg_label.bind("<Button-1>", self.copy_selected_pkg_to_clipboard)

        plat_frame = tk.Frame(self, bg="#1e1e1e")
        plat_frame.pack(pady=5, padx=20, fill="x")
        ttk.Label(plat_frame, text="🖥 Platform:").pack(side=tk.LEFT)
        self.platform_var = tk.StringVar(value="Google Play Games Beta")
        ttk.Combobox(plat_frame, textvariable=self.platform_var,
                     values=["Google Play Games Beta", "LDPlayer 9"],
                     state="readonly").pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)

        ttk.Button(self, text="🎯 Create Shortcut", command=self.create).pack(pady=10)

    def _create_tool_button(self, parent, text, command):
        return tk.Button(parent, text=text, command=command, bg="#2d2d2d", fg="white",
                         activebackground="#3a3a3a", activeforeground="white",
                         relief="flat", font=("Segoe UI", 10), cursor="hand2")

    def perform_search(self, event=None):
        query = self.search_var.get().strip()
        self.clear_results()
        self.pkg_label_var.set("-")
        self.empty_label.place_forget()
        self.loading_label.place(relx=0.5, rely=0.6, anchor="center")
        self.update_idletasks()

        if not query:
            self.loading_label.place_forget()
            self.empty_label.place(relx=0.5, rely=0.5, anchor="center")
            return

        try:
            results = search(query, lang=self.settings.get("lang", "en"), country=self.settings.get("country", "PH"))[:10]
            self.loading_label.place_forget()

            if not results:
                self.empty_label.place(relx=0.5, rely=0.5, anchor="center")
                return

            self.scrollable_frame.grid_columnconfigure(0, weight=1)
            self.scrollable_frame.grid_columnconfigure(1, weight=1)

            for idx, app in enumerate(results):
                name, pkg, icon_url = app['title'], app['appId'], app['icon']
                photo = self._fetch_photo(icon_url, name)

                item = tk.Frame(self.scrollable_frame, bg="#2d2d2d", padx=6, pady=4)
                item.grid(row=idx // 2, column=idx % 2, padx=6, pady=6, sticky="nsew")
                item.bind("<Button-1>", lambda e, p=pkg, f=item: self.select_package(p, f))

                self._create_icon_label(item, photo, pkg, item)
                self._create_name_label(item, name, pkg, item)
                self.search_results.append((name, pkg))

        except Exception as e:
            self.loading_label.place_forget()
            messagebox.showerror("Error", str(e))

    def _fetch_photo(self, url, name):
        try:
            data = requests.get(url).content
            img = Image.open(BytesIO(data)).resize((48, 48), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            self.image_refs.append(photo)
            return photo
        except Exception as e:
            print(f"Failed to load icon for {name}: {e}")
            return None

    def _create_icon_label(self, parent, photo, pkg, frame):
        if photo:
            lbl = tk.Label(parent, image=photo, bg="#2d2d2d")
            lbl.image = photo
        else:
            lbl = tk.Label(parent, text="🕹️", fg="white", bg="#2d2d2d", font=("Segoe UI", 18))
        lbl.pack(side="left")
        lbl.bind("<Button-1>", lambda e: self.select_package(pkg, frame))

    def _create_name_label(self, parent, text, pkg, frame):
        lbl = tk.Label(parent, text=text, fg="#ffffff", bg="#2d2d2d", anchor="w",
                       font=("Segoe UI", 10), wraplength=160, justify="left")
        lbl.pack(side="left", padx=10, fill="x", expand=True)
        lbl.bind("<Button-1>", lambda e: self.select_package(pkg, frame))

    def clear_results(self):
        for w in self.scrollable_frame.winfo_children():
            w.destroy()
        self.image_refs.clear()
        self.search_results.clear()

    def select_package(self, pkg, item_frame=None):
        self.pkg_label_var.set(pkg)
        if self.selected_item and self.selected_item.winfo_exists():
            self._set_bg_recursive(self.selected_item, "#2d2d2d")
        if item_frame:
            self._set_bg_recursive(item_frame, "#3a3a3a")
            self.selected_item = item_frame

    def _set_bg_recursive(self, widget, color):
        try:
            widget.configure(bg=color)
            for child in widget.winfo_children():
                child.configure(bg=color)
        except tk.TclError:
            pass

    def copy_selected_pkg_to_clipboard(self, event=None):
        pkg = self.pkg_label_var.get()
        if pkg and pkg != "-":
            self.clipboard_clear()
            self.clipboard_append(pkg)
            self.update()
            x, y = event.widget.winfo_rootx(), event.widget.winfo_rooty()
            tooltip = tk.Toplevel(self)
            tooltip.overrideredirect(True)
            tooltip.geometry(f"+{x + 100}+{y}")
            tk.Label(tooltip, text="✅ Copied!", bg="black", fg="white", font=("Segoe UI", 9)).pack()
            self.after(1000, tooltip.destroy)

    def create(self):
        pkg = self.pkg_label_var.get()
        if not pkg or pkg == "-":
            messagebox.showerror("Select", "Please select a package first.")
            return

        name = next((n for n, p in self.search_results if p == pkg), None)
        if not name:
            messagebox.showerror("Error", "App name not found.")
            return

        platform = self.platform_var.get()
        if platform == "Google Play Games Beta":
            target = "C:\\Windows\\System32\\cmd.exe"
            arguments = f'/c start "" "googleplaygames://launch/?id={pkg}"'
        else:
            target = self.settings.get("LDPlayer9_path", "")
            arguments = f'launchex --index 0 --packagename {pkg}'
            if not os.path.exists(target):
                messagebox.showerror("LDPlayer", "LDPlayer path invalid.")
                return

        try:
            icon_url = search(pkg)[0]['icon']
        except:
            icon_url = ""
        icon_path = download_icon(icon_url, pkg.split(".")[-1]) if icon_url else None

        try:
            create_shortcut(name, target, arguments, icon_path)
            messagebox.showinfo("Success", f"Shortcut created for: {name}")
        except Exception as e:
            messagebox.showerror("Error", f"Shortcut creation failed:\n{e}")

if __name__ == "__main__":
    PlayStoreShortcutApp().mainloop()
