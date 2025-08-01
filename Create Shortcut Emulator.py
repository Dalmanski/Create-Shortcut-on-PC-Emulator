import os
import sys
import json
import tkinter as tk
from tkinter import messagebox, filedialog, ttk
from win32com.client import Dispatch
import winshell
from google_play_scraper import search
import requests
from PIL import Image, ImageTk
from io import BytesIO
from help import open_help_popup

SETTINGS_FILE = os.path.join(
    os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else __file__),
    "settings.json"
)

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_settings(data):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(data, f, indent=2)

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
        self.title("🎮 Create Shortcut on PC Emulator")
        self.geometry("600x500")
        self.configure(bg="#1e1e1e")
        self.resizable(False, False)

        self.settings = load_settings()
        self.search_results = []
        self.image_refs = []
        self.selected_item = None

        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self.style.configure("TLabel", background="#1e1e1e", foreground="#ffffff")
        self.style.configure("TButton", background="#292929", foreground="#ffffff", padding=6, relief="flat")
        self.style.map("TButton", background=[("active", "#444444")])
        self.style.configure("TEntry", fieldbackground="#2d2d2d", foreground="#ffffff")
        self.style.configure("TCombobox", arrowcolor="#ffffff")
        
        self.style.map("TCombobox", 
            fieldbackground=[("readonly", "#2d2d2d")],
            selectbackground=[("readonly", "#2d2d2d")],
            background=[("readonly", "#1e1e1e")],
            foreground=[("readonly", "white")]
        )

        if "ldplayer_path" not in self.settings or not os.path.exists(self.settings["ldplayer_path"]):
            if messagebox.askyesno("LDPlayer", "LDPlayer not found. Do you have it installed?"):
                self.settings["ldplayer_path"] = self.ask_ldplayer_path()
                save_settings(self.settings)
            else:
                self.settings["ldplayer_path"] = None

        search_frame = tk.Frame(self, bg="#1e1e1e")
        search_frame.pack(pady=15, fill=tk.X, padx=20)
        ttk.Label(search_frame, text="🔍 Search Google Play:").pack(anchor="w")
        self.search_var = tk.StringVar()
        entry = ttk.Entry(search_frame, textvariable=self.search_var)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        entry.bind("<Return>", self.perform_search)
        ttk.Button(search_frame, text="Search", command=self.perform_search).pack(side=tk.LEFT, padx=10)

        help_button = tk.Button(
            self,
            text="❓",
            command=open_help_popup,
            bg="#2d2d2d",
            fg="white",
            activebackground="#3a3a3a",
            activeforeground="white",
            relief="flat",
            font=("Segoe UI", 10),
            cursor="hand2"
        )
        help_button.place(relx=1.0, rely=1.0, x=-10, y=-10, anchor="se")
        help_button.bind("<Button-1>", lambda e: open_help_popup())

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
        ttk.Label(pkg_frame, textvariable=self.pkg_label_var, foreground="#cccccc").pack(side=tk.LEFT, padx=10)

        plat_frame = tk.Frame(self, bg="#1e1e1e")
        plat_frame.pack(pady=5, padx=20, fill="x")
        ttk.Label(plat_frame, text="🖥 Platform:").pack(side=tk.LEFT)
        self.platform_var = tk.StringVar(value="Google Play Games Beta")
        self.platform_dropdown = ttk.Combobox(plat_frame, textvariable=self.platform_var,
                                              values=["Google Play Games Beta", "LDPlayer 9"],
                                              state="readonly")
        self.platform_dropdown.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)

        ttk.Button(self, text="🎯 Create Shortcut", command=self.create).pack(pady=10)

    def ask_ldplayer_path(self):
        while True:
            messagebox.showinfo("LDPlayer", "Select 'dnconsole.exe' from LDPlayer folder.")
            path = filedialog.askopenfilename(filetypes=[("Executable", "*.exe")])
            if not path:
                if not messagebox.askretrycancel("Required", "You must select a file."):
                    self.quit()
            elif os.path.basename(path).lower() != "dnconsole.exe":
                messagebox.showerror("Invalid", "Not 'dnconsole.exe'.")
            else:
                return path

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
            results = search(query)[:10]
            self.loading_label.place_forget()

            if not results:
                self.empty_label.place(relx=0.5, rely=0.5, anchor="center")
                return

            self.scrollable_frame.grid_columnconfigure(0, weight=1)
            self.scrollable_frame.grid_columnconfigure(1, weight=1)

            for index, app in enumerate(results):
                name = app['title']
                pkg = app['appId']
                icon_url = app['icon']

                try:
                    image_data = requests.get(icon_url).content
                    img = Image.open(BytesIO(image_data)).resize((48, 48), Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(img)
                    self.image_refs.append(photo)
                except Exception as e:
                    print(f"Failed to load icon for {name}: {e}")
                    photo = None

                item = tk.Frame(self.scrollable_frame, bg="#2d2d2d", padx=6, pady=4)
                row = index // 2
                col = index % 2
                item.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")

                item.bind("<Button-1>", lambda e, p=pkg, f=item: self.select_package(p, f))

                if photo:
                    icon_label = tk.Label(item, image=photo, bg="#2d2d2d")
                    icon_label.image = photo
                    icon_label.pack(side="left")
                    icon_label.bind("<Button-1>", lambda e, p=pkg, f=item: self.select_package(p, f))
                else:
                    icon_label = tk.Label(item, text="🕹️", fg="white", bg="#2d2d2d", font=("Segoe UI", 18))
                    icon_label.pack(side="left", padx=(0, 4))
                    icon_label.bind("<Button-1>", lambda e, p=pkg, f=item: self.select_package(p, f))

                name_label = tk.Label(
                    item,
                    text=name,
                    fg="#ffffff",
                    bg="#2d2d2d",
                    anchor="w",
                    font=("Segoe UI", 10),
                    wraplength=160,
                    justify="left"
                )
                name_label.pack(side="left", padx=10, fill="x", expand=True)
                name_label.bind("<Button-1>", lambda e, p=pkg, f=item: self.select_package(p, f))

                self.search_results.append((name, pkg))

        except Exception as e:
            self.loading_label.place_forget()
            messagebox.showerror("Error", str(e))

    def clear_results(self):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.image_refs.clear()
        self.search_results.clear()

    def select_package(self, pkg, item_frame=None):
        self.pkg_label_var.set(pkg)
        
        if self.selected_item:
            try:
                if not self.selected_item.winfo_exists():
                    self.selected_item = None
                else:
                    self.selected_item.configure(bg="#2d2d2d")
                    for child in self.selected_item.winfo_children():
                        child.configure(bg="#2d2d2d")
            except tk.TclError:
                self.selected_item = None

        if item_frame:
            item_frame.configure(bg="#3a3a3a")
            for child in item_frame.winfo_children():
                child.configure(bg="#3a3a3a")
            self.selected_item = item_frame

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
            target = self.settings.get("ldplayer_path", "")
            arguments = f'launchex --index 0 --packagename {pkg}'
            if not os.path.exists(target):
                messagebox.showerror("LDPlayer", "LDPlayer path invalid.")
                return
        icon_url = ""
        try:
            icon_url = search(pkg)[0]['icon']
        except:
            pass
        icon_path = download_icon(icon_url, pkg.split(".")[-1]) if icon_url else None
        try:
            create_shortcut(name, target, arguments, icon_path)
            messagebox.showinfo("Success", f"Shortcut created for: {name}")
        except Exception as e:
            messagebox.showerror("Error", f"Shortcut creation failed:\n{e}")

if __name__ == "__main__":
    PlayStoreShortcutApp().mainloop()
