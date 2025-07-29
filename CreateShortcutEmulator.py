import os
import sys
import json
import tkinter as tk
from tkinter import messagebox, filedialog, ttk
from win32com.client import Dispatch
import winshell
from google_play_scraper import search
import requests
from PIL import Image
from io import BytesIO

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
        self.title("🎮 Play Store Game Shortcut Maker")
        self.geometry("600x620")
        self.resizable(False, False)
        self.configure(bg="#1e1e1e")

        self.settings = load_settings()

        # Styling
        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self.style.configure("TLabel", background="#1e1e1e", foreground="#ffffff", font=("Segoe UI", 10))
        self.style.configure("TButton", background="#292929", foreground="#ffffff", font=("Segoe UI", 10), padding=6)
        self.style.map("TButton", background=[("active", "#444444")])
        self.style.configure("TRadiobutton", background="#1e1e1e", foreground="#ffffff", font=("Segoe UI", 10))
        self.style.configure("TEntry", fieldbackground="#2d2d2d", foreground="#ffffff")

        # Fix radiobutton hover text
        self.style.map("Custom.TRadiobutton",
            background=[("active", "#ffffff"), ("!active", "#1e1e1e")],
            foreground=[("active", "#000000"), ("!active", "#ffffff")]
        )

        # Prompt for LDPlayer if not set
        if "ldplayer_path" not in self.settings or not os.path.exists(self.settings["ldplayer_path"]):
            use_ld = messagebox.askyesno("LDPlayer Detection", "LDPlayer not detected.\nDo you have LDPlayer 9 installed?")
            if use_ld:
                self.settings["ldplayer_path"] = self.ask_ldplayer_path()
                save_settings(self.settings)
            else:
                self.settings["ldplayer_path"] = None

        # Search bar
        search_frame = tk.Frame(self, bg="#1e1e1e")
        search_frame.pack(pady=15)
        ttk.Label(search_frame, text="🔍 Search Google Play:").pack(anchor="w")
        entry_frame = tk.Frame(search_frame, bg="#1e1e1e")
        entry_frame.pack(pady=5)
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(entry_frame, textvariable=self.search_var, width=45)
        self.search_entry.pack(side=tk.LEFT, padx=(0, 5))
        search_btn = ttk.Button(entry_frame, text="Search", command=self.perform_search)
        search_btn.pack(side=tk.LEFT)
        self.search_entry.bind("<Return>", self.perform_search)

        # Listbox for search results
        self.listbox = tk.Listbox(self, height=10, width=75, bg="#2d2d2d", fg="white", font=("Segoe UI", 10), selectbackground="#444444")
        self.listbox.pack(pady=(10, 15))
        self.listbox.bind("<<ListboxSelect>>", self.on_select)

        # Empty list message
        self.empty_label = ttk.Label(self, text="Please search the game", foreground="#888888", font=("Segoe UI", 10))
        self.empty_label.place(in_=self.listbox, relx=0.5, rely=0.5, anchor="center")

        # Package name field
        pkg_frame = tk.Frame(self, bg="#1e1e1e")
        pkg_frame.pack(pady=(0, 10))
        ttk.Label(pkg_frame, text="📦 Selected Package Name:").pack(anchor="w")
        self.pkg_entry = ttk.Entry(pkg_frame, width=55)
        self.pkg_entry.pack(pady=(3, 0))

        # Platform radio buttons
        platform_frame = tk.Frame(self, bg="#1e1e1e")
        platform_frame.pack(pady=(5, 15))
        ttk.Label(platform_frame, text="🖥️ Platform:").pack(anchor="w")
        self.platform_var = tk.StringVar(value="gp")
        radio_row = tk.Frame(platform_frame, bg="#1e1e1e")
        radio_row.pack()
        ttk.Radiobutton(radio_row, text="Google Play Games Beta", variable=self.platform_var, value="gp", style="Custom.TRadiobutton").pack(side=tk.LEFT, padx=15)
        ttk.Radiobutton(radio_row, text="LDPlayer 9", variable=self.platform_var, value="ld", style="Custom.TRadiobutton").pack(side=tk.LEFT, padx=15)

        # Create button
        ttk.Button(self, text="🎯 Create Shortcut", command=self.create).pack(pady=10)

        self.search_results = []

    def ask_ldplayer_path(self):
        while True:
            messagebox.showinfo("LDPlayer Path", "Please select 'dnconsole.exe' from your LDPlayer installation folder.")
            path = filedialog.askopenfilename(title="Select dnconsole.exe", filetypes=[("Executable", "*.exe")])
            if not path:
                retry = messagebox.askretrycancel("File Required", "You must select a file to continue.")
                if not retry:
                    self.quit()
            elif os.path.basename(path).lower() != "dnconsole.exe":
                messagebox.showerror("Invalid File", "Selected file is not 'dnconsole.exe'. Please try again.")
            else:
                return path

    def perform_search(self, event=None):
        query = self.search_var.get().strip()
        self.listbox.delete(0, tk.END)
        self.search_results.clear()
        self.empty_label.place_forget()

        if not query:
            self.empty_label.place(in_=self.listbox, relx=0.5, rely=0.5, anchor="center")
            return

        try:
            results = search(query)
            results = results[:10]
            if not results:
                self.empty_label.place(in_=self.listbox, relx=0.5, rely=0.5, anchor="center")
                return

            for app in results:
                name = app['title']
                pkg = app['appId']
                self.search_results.append((name, pkg))
                self.listbox.insert(tk.END, f"{name} ({pkg})")
        except Exception as e:
            messagebox.showerror("Search Error", f"Failed to fetch results:\n{e}")
            self.empty_label.place(in_=self.listbox, relx=0.5, rely=0.5, anchor="center")

    def on_select(self, event):
        index = self.listbox.curselection()
        if index:
            _, pkg = self.search_results[index[0]]
            self.pkg_entry.delete(0, tk.END)
            self.pkg_entry.insert(0, pkg)

    def create(self):
        index = self.listbox.curselection()
        if not index:
            messagebox.showerror("Error", "Please select a game from the search results.")
            return

        name, pkg = self.search_results[index[0]]

        if self.platform_var.get() == "gp":
            target = "C:\\Windows\\System32\\cmd.exe"
            arguments = f'/c start "" "googleplaygames://launch/?id={pkg}"'
        else:
            target = self.settings.get("ldplayer_path", "")
            arguments = f'launchex --index 0 --packagename {pkg}'
            if not os.path.exists(target):
                messagebox.showerror("Error", "LDPlayer 9 not found at expected path.")
                return

        icon_url = ""
        try:
            icon_url = search(pkg, lang="en", country="us")[0]['icon']
        except Exception as e:
            print("Failed to get icon URL:", e)

        icon_path = download_icon(icon_url, pkg.split('.')[-1]) if icon_url else None

        try:
            path = create_shortcut(name, target, arguments, icon_path)
            messagebox.showinfo("Success", f"Shortcut created:\n{name}.lnk")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create shortcut:\n{e}")

if __name__ == "__main__":
    PlayStoreShortcutApp().mainloop()
