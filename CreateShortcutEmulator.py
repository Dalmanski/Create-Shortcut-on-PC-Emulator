import os
import sys
import json
import tkinter as tk
from tkinter import messagebox, filedialog
from win32com.client import Dispatch
import winshell
from google_play_scraper import search
import requests
from PIL import Image
from io import BytesIO

SETTINGS_FILE = os.path.join(os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else __file__), "settings.json")

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
        self.title("Live Play Store Game Search")
        self.geometry("500x500")
        self.resizable(False, False)

        self.settings = load_settings()

        if "ldplayer_path" not in self.settings or not os.path.exists(self.settings["ldplayer_path"]):
            use_ld = messagebox.askyesno("LDPlayer Detection", "LDPlayer not detected.\nDo you have LDPlayer 9 installed?")
            if use_ld:
                self.settings["ldplayer_path"] = self.ask_ldplayer_path()
                save_settings(self.settings)
            else:
                self.settings["ldplayer_path"] = None

        tk.Label(self, text="🔍 Search Google Play:").pack(pady=(10, 0))
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(self, textvariable=self.search_var, width=50)
        self.search_entry.pack(pady=(0, 5))
        self.search_entry.bind("<Return>", self.perform_search)

        self.listbox = tk.Listbox(self, height=10, width=70)
        self.listbox.pack()
        self.listbox.bind("<<ListboxSelect>>", self.on_select)

        tk.Label(self, text="📦 Selected Package Name:").pack(pady=(10, 2))
        self.pkg_entry = tk.Entry(self, width=50)
        self.pkg_entry.pack()

        tk.Label(self, text="🖥️ Platform:").pack(pady=(10, 2))
        self.platform_var = tk.StringVar(value="gp")
        radio_frame = tk.Frame(self)
        tk.Radiobutton(radio_frame, text="Google Play Games Beta", variable=self.platform_var, value="gp").pack(side=tk.LEFT, padx=10)
        tk.Radiobutton(radio_frame, text="LDPlayer 9", variable=self.platform_var, value="ld").pack(side=tk.LEFT, padx=10)
        radio_frame.pack()

        tk.Button(self, text="🎯 Create Shortcut", command=self.create).pack(pady=15)

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
        if not query:
            return

        self.listbox.delete(0, tk.END)
        self.search_results.clear()

        try:
            results = search(query)
            results = results[:10]
            for app in results:
                name = app['title']
                pkg = app['appId']
                self.search_results.append((name, pkg))
                self.listbox.insert(tk.END, f"{name} ({pkg})")
        except Exception as e:
            messagebox.showerror("Search Error", f"Failed to fetch results:\n{e}")

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
            shortcut_name = name
            target = "C:\\Windows\\System32\\cmd.exe"
            arguments = f'/c start "" "googleplaygames://launch/?id={pkg}"'
        else:
            shortcut_name = name
            settings = load_settings()
            target = settings.get("ldplayer_path", "")
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
            path = create_shortcut(shortcut_name, target, arguments, icon_path)
            messagebox.showinfo("Success", f"Shortcut created:\n{shortcut_name}.lnk")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create shortcut:\n{e}")


if __name__ == "__main__":
    PlayStoreShortcutApp().mainloop()
