import os
import sys
import json
import threading
import tkinter as tk
from tkinter import messagebox, ttk, filedialog
from win32com.client import Dispatch
import winshell
from google_play_scraper import search, app
import requests
from PIL import Image, ImageTk
from io import BytesIO
from help import open_help_popup
from settings import open_settings_popup, load_settings
from jaypy import centerwindow
import urllib.parse
import re
import shutil
import tempfile
import atexit

SETTINGS_FILE = os.path.join(
    os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else __file__),
    "settings.json"
)

def relaunch():
    os.execl(sys.executable, sys.executable, *sys.argv)

def _normalize_path(p):
    if not p:
        return ""
    p = p.strip().strip('"').strip("'")
    p = os.path.expandvars(p)
    p = os.path.expanduser(p)
    p = os.path.normpath(p)
    return p

def resolve_shortcut(path):
    try:
        if not path:
            return None
        p = _normalize_path(path)
        ext = os.path.splitext(p)[1].lower()
        if ext != ".lnk":
            return None
        if not os.path.exists(p):
            return None
        shell = Dispatch("WScript.Shell")
        sc = shell.CreateShortCut(p)
        tgt = sc.Targetpath
        if not tgt:
            return None
        return _normalize_path(tgt)
    except Exception:
        return None

def _split_exe_and_args(target):
    if not target:
        return ("", "")
    t = target.strip().strip('"').strip("'")
    resolved = resolve_shortcut(t)
    if resolved:
        t = resolved
    tokens = re.split(r'\s+', t, maxsplit=1)
    first = tokens[0] if tokens else ""
    first_norm = _normalize_path(first)
    if first_norm and os.path.exists(first_norm) and first_norm.lower().endswith(".exe"):
        args = tokens[1] if len(tokens) > 1 else ""
        return (first_norm, args)
    low = t.lower()
    if "launchex" in low:
        idx = low.find("launchex")
        exe_part = t[:idx].strip().strip('"').strip("'")
        args_part = t[idx:].strip()
        exe_norm = _normalize_path(exe_part)
        if exe_norm and os.path.exists(exe_norm):
            return (exe_norm, args_part)
    if os.path.isdir(first_norm):
        candidate = os.path.join(first_norm, "dnconsole.exe")
        if os.path.exists(candidate):
            rest = tokens[1] if len(tokens) > 1 else ""
            return (candidate, rest)
    return (_normalize_path(first), tokens[1] if len(tokens) > 1 else "")

def _sanitize_name(name):
    name = name.strip()
    name = re.sub(r'[<>:"/\\|?*\x00-\x1F]', '-', name)
    name = name[:150].strip()
    if not name:
        name = "Shortcut"
    return name

def _check_dnconsole_path(path):
    if not path:
        return False
    path = _normalize_path(path)
    resolved = resolve_shortcut(path)
    if resolved:
        path = resolved
    if os.path.exists(path) and os.path.basename(path).lower() == "dnconsole.exe":
        return True
    if os.path.isdir(path):
        candidate = os.path.join(path, "dnconsole.exe")
        if os.path.exists(candidate):
            return True
    alt = path.replace("/", "\\")
    if os.path.exists(alt) and os.path.basename(alt).lower() == "dnconsole.exe":
        return True
    alt2 = path.replace("\\", "/")
    if os.path.exists(alt2) and os.path.basename(alt2).lower() == "dnconsole.exe":
        return True
    return False

def extract_package_id(text):
    if not text:
        return ""
    txt = text.strip()
    if txt.startswith("http") or "play.google" in txt:
        try:
            parsed = urllib.parse.urlparse(txt if txt.startswith("http") else "https://" + txt)
            qs = urllib.parse.parse_qs(parsed.query)
            if "id" in qs and qs["id"]:
                return qs["id"][0]
            q = parsed.query
            idx = q.find("id=")
            if idx != -1:
                val = q[idx + 3:]
                for ch in ["&", "/", "?"]:
                    pos = val.find(ch)
                    if pos != -1:
                        val = val[:pos]
                return val
            path = parsed.path
            if path:
                parts = path.split("/")
                for part in parts[::-1]:
                    if "." in part and " " not in part:
                        return part
        except Exception:
            pass
    idx = txt.find("id=")
    if idx != -1:
        val = txt[idx + 3:]
        for ch in ["&", "/", "?"]:
            pos = val.find(ch)
            if pos != -1:
                val = val[:pos]
        return val
    if "." in txt and " " not in txt:
        return txt
    return txt

def _get_app_dir():
    return os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else __file__)

def _icons_temp_dir():
    d = os.path.join(tempfile.gettempdir(), "playstore_shortcut_icons")
    try:
        os.makedirs(d, exist_ok=True)
    except Exception:
        pass
    return d

def _local_icon_candidates_for_name(name, icons_folder=None):
    if not name:
        return []
    base = _sanitize_name(name)
    if icons_folder is None:
        icons_folder = _get_app_dir()
    candidates = []
    candidates.append(os.path.join(icons_folder, f"{base}.ico"))
    candidates.append(os.path.join(icons_folder, f"{base}.png"))
    candidates.append(os.path.join(icons_folder, f"{base}.jpg"))
    candidates.append(os.path.join(icons_folder, f"{base}.jpeg"))
    return candidates

def _find_local_icon(name):
    for p in _local_icon_candidates_for_name(name, _get_app_dir()):
        try:
            if os.path.exists(p) and os.path.getsize(p) > 0:
                return p
        except Exception:
            continue
    return None

def _ensure_ico_from_image(src_path, dest_ico_path):
    try:
        if os.path.exists(dest_ico_path) and os.path.getsize(dest_ico_path) > 0:
            return dest_ico_path
        with Image.open(src_path) as im:
            im = im.convert("RGBA")
            im = im.resize((64, 64), Image.Resampling.LANCZOS)
            im.save(dest_ico_path, format="ICO", sizes=[(64, 64)])
        return dest_ico_path
    except Exception:
        return None

def create_shortcut(name, target, arguments="", icon=None, folder=None):
    if not folder:
        desktop = winshell.desktop()
        path = os.path.join(desktop, f"{_sanitize_name(name)}.lnk")
    else:
        try:
            os.makedirs(folder, exist_ok=True)
        except Exception:
            pass
        path = os.path.join(folder, f"{_sanitize_name(name)}.lnk")
    shell = Dispatch('WScript.Shell')
    exe, extra_args = _split_exe_and_args(target)
    final_args = " ".join([a for a in [extra_args.strip(), arguments.strip()] if a]).strip()
    if not exe:
        exe = _normalize_path(target)
    shortcut = shell.CreateShortCut(path)
    shortcut.Targetpath = exe
    if final_args:
        shortcut.Arguments = final_args
    if icon and os.path.exists(icon) and os.path.getsize(icon) > 0:
        try:
            shortcut.IconLocation = icon
        except Exception:
            try:
                shortcut.IconLocation = f"{icon},0"
            except Exception:
                pass
    wd = ""
    try:
        if exe and os.path.exists(exe):
            wd = os.path.dirname(exe)
        else:
            wd = os.path.dirname(target) or os.path.expanduser("~")
    except Exception:
        wd = os.path.expanduser("~")
    if wd:
        shortcut.WorkingDirectory = wd
    shortcut.save()
    return path

class PlayStoreShortcutApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.settings = load_settings()
        try:
            self.iconbitmap("icon.ico")
        except Exception:
            pass
        self.title("Create Shortcut on PC Emulator")
        self.geometry("600x560")
        self.configure(bg="#1e1e1e")
        self.resizable(False, False)
        centerwindow(self, offsety=-40)
        self.search_results = []
        self.image_refs = {}
        self.icon_labels = {}
        self.downloaded_icon_files = {}
        self.selected_item = None
        self.selected_index = None
        self.pkg_labels = {}
        self.normal_bg = "#2d2d2d"
        self.selected_bg = "#3a3a3a"
        self.icons_temp_folder = _icons_temp_dir()
        self._setup_styles()
        self._create_widgets()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        atexit.register(self._cleanup_temp_icons)

    def _open_settings(self):
        win = open_settings_popup(self)
        if not win:
            return
        def _reload_settings(event=None):
            try:
                self.settings = load_settings()
            except Exception:
                pass
        win.bind("<Destroy>", _reload_settings)
        try:
            win.lift()
            win.focus_force()
        except Exception:
            pass

    def _setup_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TLabel", background="#1e1e1e", foreground="#ffffff")
        style.configure("TButton", background="#292929", foreground="#ffffff", padding=6, relief="flat")
        style.map("TButton", background=[("active", "#444444")])
        style.configure("TEntry", fieldbackground=self.normal_bg, foreground="#ffffff")
        style.configure("TCombobox", arrowcolor="#ffffff")
        style.map("TCombobox",
                  fieldbackground=[("readonly", self.normal_bg)],
                  selectbackground=[("readonly", self.normal_bg)],
                  background=[("readonly", "#1e1e1e")],
                  foreground=[("readonly", "white")])

    def _create_widgets(self):
        search_frame = tk.Frame(self, bg="#1e1e1e")
        search_frame.pack(pady=15, fill=tk.X, padx=20)
        ttk.Label(search_frame, text="🔍 Search Google Play (or paste Play Store URL):").pack(anchor="w")
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.search_entry.bind("<Return>", self.perform_search)
        self.search_btn = ttk.Button(search_frame, text="Search", command=self.perform_search)
        self.search_btn.pack(side=tk.LEFT, padx=10)
        btn_frame = tk.Frame(self, bg="#1e1e1e")
        btn_frame.place(relx=1.0, rely=1.0, x=-10, y=-10, anchor="se")
        self._create_tool_button(btn_frame, "⚙️", self._open_settings).pack(side=tk.RIGHT, padx=5)
        self._create_tool_button(btn_frame, "❓", open_help_popup).pack(side=tk.RIGHT)
        self.result_frame = tk.Frame(self, bg="#1e1e1e")
        self.result_frame.pack(padx=20, pady=10, fill=tk.BOTH, expand=True)
        self.canvas = tk.Canvas(self.result_frame, bg=self.normal_bg, height=240, highlightthickness=0)
        self.scrollbar = tk.Scrollbar(self.result_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=self.normal_bg)
        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        self.empty_label = ttk.Label(self.canvas, text="Please search the game", foreground="#888888")
        self.empty_label.place(relx=0.5, rely=0.5, anchor="center")
        self.loading_label = ttk.Label(self.canvas, text="🔄 Loading...", foreground="#aaaaaa")
        self.pkg_label_var = tk.StringVar(value="-")
        self.full_link_var = tk.StringVar(value="")

        pkg_frame = tk.Frame(self, bg="#1e1e1e")
        pkg_frame.pack(pady=6, padx=20, fill="x")

        full_link_label_title = ttk.Label(pkg_frame, text="🔗 Play Store Link:", background="#1e1e1e")
        full_link_label_title.grid(row=0, column=0, sticky="w")
        full_link_label = ttk.Label(pkg_frame, textvariable=self.full_link_var, foreground="#00bfff", cursor="hand2", background="#1e1e1e", wraplength=460)
        full_link_label.grid(row=0, column=1, columnspan=3, sticky="w", padx=(8, 8))
        def _open_full_link(event=None):
            link = self.full_link_var.get().strip()
            if link:
                try:
                    import webbrowser
                    webbrowser.open(link)
                except Exception:
                    pass
        full_link_label.bind("<Button-1>", _open_full_link)

        lbl_static = ttk.Label(pkg_frame, text="📦 Selected Package:")
        lbl_static.grid(row=1, column=0, sticky="w")
        pkg_label = ttk.Label(pkg_frame, textvariable=self.pkg_label_var, foreground="#cccccc", cursor="hand2", background="#1e1e1e")
        pkg_label.grid(row=1, column=1, sticky="w", padx=(8, 8))
        pkg_label.bind("<Button-1>", self.copy_selected_pkg_to_clipboard)
        self.pkg_entry = ttk.Entry(pkg_frame)
        self.pkg_entry.grid(row=1, column=2, sticky="ew", padx=(4, 4))
        self.pkg_entry.grid_remove()
        self.pkg_use_btn = ttk.Button(pkg_frame, text="Use", command=self._use_manual_pkg)
        self.pkg_use_btn.grid(row=1, column=3, sticky="e")
        self.pkg_use_btn.grid_remove()
        pkg_frame.grid_columnconfigure(1, weight=1)

        self.pkg_tip = tk.Label(pkg_frame, text="We can't find their package name, pls copy the link URL and paste here", fg="#ffdd88", bg="#1e1e1e", font=("Segoe UI", 8), wraplength=460, justify="left")
        self.pkg_tip.grid(row=2, column=0, columnspan=4, sticky="w", pady=(6, 0))
        self.pkg_tip.grid_remove()

        plat_frame = tk.Frame(self, bg="#1e1e1e")
        plat_frame.pack(pady=5, padx=20, fill="x")
        plat_frame.grid_columnconfigure(1, weight=1)
        ttk.Label(plat_frame, text="🖥 Platform:").grid(row=0, column=0, sticky="w")
        self.platform_var = tk.StringVar(value="Google Play Games Beta")
        self.platform_combo = ttk.Combobox(plat_frame, textvariable=self.platform_var,
                                           values=["Google Play Games Beta", "LDPlayer 9"],
                                           state="readonly")
        self.platform_combo.grid(row=0, column=1, sticky="ew", padx=(8, 6))
        self.ld_index_label = ttk.Label(plat_frame, text="Idx [Instance]:\n(Main = 0)")
        self.ld_index_var = tk.StringVar(value=str(self.settings.get("LDPlayer9_index", 0) if self.settings.get("LDPlayer9_index", None) is not None else "0"))
        def _validate_index(proposed):
            if proposed == "":
                return True
            return proposed.isdigit()
        vcmd = (self.register(lambda P: _validate_index(P)), '%P')
        self.ld_index_spin = tk.Spinbox(plat_frame, from_=0, to=9999, textvariable=self.ld_index_var, validate="key", validatecommand=vcmd, width=6, bd=0, relief="flat", highlightthickness=0)
        self.ld_index_label.grid(row=0, column=2, sticky="e", padx=(6, 2))
        self.ld_index_spin.grid(row=0, column=3, sticky="w")
        if self.platform_var.get() != "LDPlayer 9":
            self.ld_index_label.grid_remove()
            self.ld_index_spin.grid_remove()
        self.platform_var.trace_add("write", lambda *a: self._on_platform_changed())
        self.ld_index_var.trace_add("write", lambda *a: self._on_ld_index_changed())
        self.ld_index_spin.configure(bg=self.normal_bg, fg="white", insertbackground="white")
        ttk.Button(self, text="🎯 Create Shortcut", command=self.create).pack(pady=10)

    def _create_tool_button(self, parent, text, command):
        return tk.Button(parent, text=text, command=command, bg=self.normal_bg, fg="white",
                         activebackground=self.selected_bg, activeforeground="white",
                         relief="flat", font=("Segoe UI", 10), cursor="hand2")

    def _clear_temp_icons(self):
        try:
            folder = self.icons_temp_folder
            if not folder:
                return
            if os.path.exists(folder):
                for entry in os.listdir(folder):
                    path = os.path.join(folder, entry)
                    try:
                        if os.path.isfile(path) or os.path.islink(path):
                            os.remove(path)
                        elif os.path.isdir(path):
                            shutil.rmtree(path)
                    except Exception:
                        pass
        except Exception:
            pass

    def perform_search(self, event=None):
        query = self.search_var.get().strip()
        if not query:
            return
        self.clear_results()
        self._clear_temp_icons()
        self.pkg_label_var.set("-")
        self.full_link_var.set("")
        self.empty_label.place_forget()
        self.loading_label.place(relx=0.5, rely=0.5, anchor="center")
        self.update_idletasks()
        self.search_btn.config(state="disabled")
        t = threading.Thread(target=self._search_thread, args=(query,), daemon=True)
        t.start()

    def _search_thread(self, query):
        pkg_candidate = extract_package_id(query)
        results = []
        err = None
        try:
            if (query.startswith("http") or "play.google" in query or "id=" in query) and pkg_candidate:
                try:
                    info = app(pkg_candidate, lang=self.settings.get("lang", "en"), country=self.settings.get("country", "PH"))
                    title = info.get("title") or info.get("name") or info.get("appId") or pkg_candidate
                    icon = info.get("icon") or info.get("iconUrl") or ""
                    full_link = f"https://play.google.com/store/apps/details?id={pkg_candidate}"
                    results = [{"title": title, "appId": pkg_candidate, "icon": icon, "link": full_link}]
                except Exception:
                    results = []
                    sr_raw = search(query, lang=self.settings.get("lang", "en"), country=self.settings.get("country", "PH")) or []
                    sr = sr_raw[:10]
                    for r in sr:
                        title = r.get("title") or r.get("name") or ""
                        appid = r.get("appId") or ""
                        icon = r.get("icon") or r.get("iconUrl") or ""
                        link = f"https://play.google.com/store/apps/details?id={appid}" if appid else f"https://play.google.com/store/search?q={urllib.parse.quote(title)}&c=apps"
                        results.append({"title": title, "appId": appid, "icon": icon, "link": link})
            else:
                sr_raw = search(query, lang=self.settings.get("lang", "en"), country=self.settings.get("country", "PH")) or []
                sr = sr_raw[:10]
                for r in sr:
                    title = r.get("title") or r.get("name") or ""
                    appid = r.get("appId") or ""
                    icon = r.get("icon") or r.get("iconUrl") or ""
                    link = f"https://play.google.com/store/apps/details?id={appid}" if appid else f"https://play.google.com/store/search?q={urllib.parse.quote(title)}&c=apps"
                    results.append({"title": title, "appId": appid, "icon": icon, "link": link})
        except Exception as e:
            results = []
            err = e
        self.after(0, lambda: self._display_results(results, err))

    def _display_results(self, results, err=None):
        self.loading_label.place_forget()
        self.search_btn.config(state="normal")
        if err and not results:
            try:
                messagebox.showinfo("Search", "Game not found")
            except Exception:
                pass
            self.empty_label.place(relx=0.5, rely=0.5, anchor="center")
            return
        if err:
            messagebox.showerror("Error", str(err))
            return
        if not results:
            self.empty_label.place(relx=0.5, rely=0.5, anchor="center")
            return
        self.scrollable_frame.grid_columnconfigure(0, weight=1)
        self.scrollable_frame.grid_columnconfigure(1, weight=1)
        for idx, appinfo in enumerate(results):
            name = appinfo.get('title') or "Unknown"
            pkg = appinfo.get('appId') or ""
            icon_url = appinfo.get('icon', "") or ""
            full_link = appinfo.get('link') or (f"https://play.google.com/store/apps/details?id={pkg}" if pkg else f"https://play.google.com/store/search?q={urllib.parse.quote(name)}&c=apps")
            item = tk.Frame(self.scrollable_frame, bg=self.normal_bg, padx=6, pady=4)
            item.grid(row=idx // 2, column=idx % 2, padx=6, pady=6, sticky="nsew")
            item.bind("<Button-1>", lambda e, p=pkg, f=item, i=idx: self.select_package(p, f, i))
            icon_lbl = tk.Label(item, text="🕹️", fg="white", bg=self.normal_bg, font=("Segoe UI", 18))
            icon_lbl.pack(side="left")
            self.icon_labels[idx] = icon_lbl
            self._create_name_label(item, name, pkg, full_link, item, idx)
            self.search_results.append((name, pkg or "", icon_url, full_link))
            local_icon = _find_local_icon(name)
            if local_icon:
                try:
                    if local_icon.lower().endswith((".png", ".jpg", ".jpeg")):
                        ico_target = os.path.join(self.icons_temp_folder, f"{_sanitize_name(name)}.ico")
                        _ensure_ico_from_image(local_icon, ico_target)
                    pil_img = None
                    try:
                        pil_img = Image.open(local_icon).convert("RGBA")
                    except Exception:
                        ico_fallback = os.path.join(self.icons_temp_folder, f"{_sanitize_name(name)}.ico")
                        if os.path.exists(ico_fallback):
                            pil_img = Image.open(ico_fallback).convert("RGBA")
                    if pil_img:
                        img = pil_img.resize((48, 48), Image.Resampling.LANCZOS)
                        photo = ImageTk.PhotoImage(img)
                        icon_lbl.configure(image=photo, text="")
                        icon_lbl.image = photo
                        ico_path = _find_local_icon(name)
                        if ico_path and ico_path.lower().endswith(".ico"):
                            self.downloaded_icon_files[idx] = ico_path
                        else:
                            created_ico = os.path.join(self.icons_temp_folder, f"{_sanitize_name(name)}.ico")
                            if os.path.exists(created_ico):
                                self.downloaded_icon_files[idx] = created_ico
                except Exception:
                    pass
            else:
                if icon_url:
                    threading.Thread(target=self._download_icon_thread, args=(icon_url, idx, name), daemon=True).start()

    def _download_icon_thread(self, url, idx, name=None):
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            pil_img = Image.open(BytesIO(response.content)).convert("RGBA")
        except Exception:
            pil_img = None
        try:
            if pil_img and name:
                base = _sanitize_name(name)
                png_path = os.path.join(self.icons_temp_folder, f"{base}.png")
                ico_path = os.path.join(self.icons_temp_folder, f"{base}.ico")
                try:
                    pil_img.save(png_path, format="PNG")
                except Exception:
                    pass
                try:
                    pil_img.resize((64, 64), Image.Resampling.LANCZOS).save(ico_path, format="ICO", sizes=[(64, 64)])
                    self.downloaded_icon_files[idx] = ico_path
                except Exception:
                    try:
                        tmp = os.path.join(self.icons_temp_folder, f"{base}.ico")
                        pil_img.resize((64, 64), Image.Resampling.LANCZOS).save(tmp, format="ICO", sizes=[(64, 64)])
                        self.downloaded_icon_files[idx] = tmp
                    except Exception:
                        pass
        except Exception:
            pass
        self.after(0, lambda: self._set_icon_image(idx, pil_img))

    def _set_icon_image(self, idx, pil_img):
        if not pil_img:
            return
        try:
            img = pil_img.resize((48, 48), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            lbl = self.icon_labels.get(idx)
            if lbl:
                current = getattr(lbl, "image", None)
                if not current:
                    lbl.configure(image=photo, text="")
                    lbl.image = photo
            try:
                if idx < len(self.search_results):
                    name, pkg, icon_url, full_link = self.search_results[idx]
                    base = _sanitize_name(name)
                    ico_path = os.path.join(self.icons_temp_folder, f"{base}.ico")
                    if not os.path.exists(ico_path):
                        try:
                            pil_img.resize((64, 64), Image.Resampling.LANCZOS).save(ico_path, format="ICO", sizes=[(64, 64)])
                            self.downloaded_icon_files[idx] = ico_path
                        except Exception:
                            pass
            except Exception:
                pass
        except Exception:
            pass

    def _create_name_label(self, parent, text, pkg, full_link, frame, idx):
        title_lbl = tk.Label(parent, text=text, fg="#ffffff", bg=self.normal_bg,
                             font=("Segoe UI", 10), wraplength=160, justify="left", anchor="w")
        title_lbl.pack(anchor="w", fill="x")
        title_lbl.bind("<Button-1>", lambda e: self.select_package(pkg, frame, idx))
        pkg_display = pkg if pkg and pkg != "None" else "N/A"
        pkg_lbl = tk.Label(parent, text=pkg_display, fg="#aaaaaa", bg=self.normal_bg,
                           font=("Segoe UI", 8), wraplength=160, justify="left", anchor="w")
        pkg_lbl.pack(anchor="w")
        pkg_lbl.bind("<Button-1>", lambda e: self.select_package(pkg, frame, idx))
        self.pkg_labels[idx] = pkg_lbl

    def clear_results(self):
        for w in self.scrollable_frame.winfo_children():
            w.destroy()
        self.image_refs.clear()
        self.search_results.clear()
        self.pkg_labels.clear()
        self.icon_labels.clear()
        self.downloaded_icon_files.clear()
        self.selected_item = None
        self.selected_index = None
        self.full_link_var.set("")
        self._hide_pkg_entry()

    def select_package(self, pkg, item_frame=None, index=None):
        if pkg is None:
            pkg = ""
        if self.selected_item and self.selected_item.winfo_exists():
            self._set_bg_recursive(self.selected_item, "#2d2d2d")
        if item_frame:
            self._set_bg_recursive(item_frame, "#3a3a3a")
            self.selected_item = item_frame
        self.selected_index = index

        name = ""
        full_link = ""
        if index is not None and 0 <= index < len(self.search_results):
            name, pkg_at_index, icon_url, full_link = self.search_results[index]
            if not pkg_at_index:
                try:
                    sr = search(name, lang=self.settings.get("lang", "en"), country=self.settings.get("country", "PH"))[:8]
                    found = None
                    for r in sr:
                        aid = r.get("appId") or ""
                        if aid:
                            found = aid
                            break
                    if found:
                        pkg_at_index = found
                        full_link = f"https://play.google.com/store/apps/details?id={found}"
                        self.search_results[index] = (name, pkg_at_index, icon_url, full_link)
                        pkg = pkg_at_index
                except Exception:
                    pass

        self.pkg_label_var.set(pkg if pkg else "-")
        self.full_link_var.set(full_link or "")
        if not pkg or pkg == "None":
            self._show_pkg_entry()
            self.pkg_entry.delete(0, tk.END)
            suggested = full_link or (f"https://play.google.com/store/search?q={urllib.parse.quote(name)}&c=apps" if name else "")
            self.pkg_entry.insert(0, suggested)
            self.pkg_entry.focus_set()
        else:
            self._hide_pkg_entry()

    def _set_bg_recursive(self, widget, color):
        try:
            widget.configure(bg=color)
            for child in widget.winfo_children():
                child.configure(bg=color)
        except tk.TclError:
            pass

    def _show_pkg_entry(self):
        self.pkg_entry.grid()
        self.pkg_use_btn.grid()
        self.pkg_tip.grid()
        self.pkg_entry.focus_set()

    def _hide_pkg_entry(self):
        self.pkg_entry.grid_remove()
        self.pkg_use_btn.grid_remove()
        self.pkg_tip.grid_remove()

    def _use_manual_pkg(self):
        raw = self.pkg_entry.get().strip()
        pkgid = extract_package_id(raw)
        if not pkgid:
            try:
                messagebox.showerror("Invalid", "Unable to extract package name. Please paste a valid Play Store link or package id.")
            except Exception:
                pass
            return
        if self.selected_index is not None and 0 <= self.selected_index < len(self.search_results):
            name, _, icon_url, _ = self.search_results[self.selected_index]
            full_link = f"https://play.google.com/store/apps/details?id={pkgid}"
            self.search_results[self.selected_index] = (name, pkgid, icon_url, full_link)
            lbl = self.pkg_labels.get(self.selected_index)
            if lbl:
                lbl.config(text=pkgid)
            self.pkg_label_var.set(pkgid)
            self.full_link_var.set(full_link)
            self.select_package(pkgid, self.selected_item, self.selected_index)
            self._hide_pkg_entry()

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

    def _on_platform_changed(self):
        plat = self.platform_var.get()
        if plat == "LDPlayer 9":
            self.ld_index_label.grid()
            self.ld_index_spin.grid()
        else:
            self.ld_index_label.grid_remove()
            self.ld_index_spin.grid_remove()

    def _on_ld_index_changed(self):
        try:
            idx_raw = self.ld_index_var.get().strip()
            idx_int = int(idx_raw) if idx_raw != "" else 0
        except Exception:
            idx_int = 0
        try:
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8-sig") as f:
                    existing = json.load(f)
            except Exception:
                existing = {}
            existing["LDPlayer9_index"] = idx_int
            try:
                with open(SETTINGS_FILE, "w", encoding="utf-8-sig") as f:
                    json.dump(existing, f, indent=2)
            except Exception:
                pass
        except Exception:
            pass

    def create(self):
        pkg = self.pkg_label_var.get()
        if not pkg or pkg == "-":
            try:
                messagebox.showerror("Select", "Please select a package first.")
            except Exception:
                pass
            return
        name = next((n for n, p, _i, _l in self.search_results if p == pkg), None)
        if not name:
            try:
                messagebox.showerror("Error", "App name not found.")
            except Exception:
                pass
            return
        settings_now = load_settings()
        shortcuts_folder = settings_now.get("shortcuts_folder") or os.path.join(os.path.expanduser("~"), "Desktop")
        game_folder = os.path.join(_normalize_path(shortcuts_folder), _sanitize_name(name))
        try:
            os.makedirs(game_folder, exist_ok=True)
        except Exception:
            pass
        platform = self.platform_var.get()
        if platform == "Google Play Games Beta":
            target = "C:\\Windows\\System32\\cmd.exe"
            arguments = f'/c start "" "googleplaygames://launch/?id={pkg}"'
        else:
            settings_now = load_settings()
            target_candidate = settings_now.get("LDPlayer9_path", "")
            target_candidate = _normalize_path(target_candidate)
            if not _check_dnconsole_path(target_candidate):
                try:
                    answer = messagebox.askyesno("LDPlayer path invalid", f"LDPlayer path seems invalid or inaccessible:\n{target_candidate}\n\nOpen Settings? (Yes)  Browse for dnconsole.exe now? (No)")
                except Exception:
                    answer = False
                if answer:
                    self._open_settings()
                    return
                else:
                    file_path = filedialog.askopenfilename(title="Locate dnconsole.exe", filetypes=[("dnconsole.exe","dnconsole.exe"), ("All files","*.*")])
                    if file_path:
                        file_path = _normalize_path(file_path)
                        try:
                            with open(SETTINGS_FILE, "r", encoding="utf-8-sig") as f:
                                existing = json.load(f)
                        except Exception:
                            existing = {}
                        existing["LDPlayer9_path"] = file_path
                        try:
                            with open(SETTINGS_FILE, "w", encoding="utf-8-sig") as f:
                                json.dump(existing, f, indent=2)
                        except Exception:
                            pass
                        target_candidate = file_path
                    else:
                        return
            target = _normalize_path(target_candidate)
            try:
                idx_raw = self.ld_index_var.get().strip()
                idx_int = int(idx_raw) if idx_raw != "" else 0
            except Exception:
                idx_int = 0
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8-sig") as f:
                    existing = json.load(f)
            except Exception:
                existing = {}
            existing["LDPlayer9_index"] = idx_int
            try:
                with open(SETTINGS_FILE, "w", encoding="utf-8-sig") as f:
                    json.dump(existing, f, indent=2)
            except Exception:
                pass
            arguments = f'launchex --index {idx_int} --packagename {pkg}'
            if not _check_dnconsole_path(target):
                try:
                    messagebox.showerror("LDPlayer", f"LDPlayer path still invalid after your action.\nChecked: {target}")
                except Exception:
                    pass
                return
        icon_path = None
        if name:
            local_icon = _find_local_icon(name)
            if local_icon:
                if local_icon.lower().endswith((".png", ".jpg", ".jpeg")):
                    ico_created = os.path.join(self.icons_temp_folder, f"{_sanitize_name(name)}.ico")
                    _ensure_ico_from_image(local_icon, ico_created)
                    if os.path.exists(ico_created):
                        icon_path = ico_created
                elif local_icon.lower().endswith(".ico"):
                    icon_path = local_icon
        if not icon_path and self.selected_index is not None:
            icon_path = self.downloaded_icon_files.get(self.selected_index)
        if icon_path and (not os.path.exists(icon_path) or os.path.getsize(icon_path) == 0):
            icon_path = None
        final_icon_path = None
        if icon_path:
            try:
                dest_icon = os.path.join(game_folder, f"{_sanitize_name(name)}.ico")
                try:
                    shutil.copyfile(icon_path, dest_icon)
                except Exception:
                    try:
                        pil = Image.open(icon_path)
                        pil.convert("RGBA").resize((64, 64), Image.Resampling.LANCZOS).save(dest_icon, format="ICO", sizes=[(64,64)])
                    except Exception:
                        dest_icon = None
                if dest_icon and os.path.exists(dest_icon):
                    final_icon_path = dest_icon
            except Exception:
                final_icon_path = None
        try:
            create_shortcut(name, target, arguments, final_icon_path, folder=game_folder)
            try:
                desktop = winshell.desktop()
                create_shortcut(name, target, arguments, final_icon_path, folder=None)
            except Exception:
                pass
            try:
                messagebox.showinfo("Success", f"Shortcut created for: {name}\nSaved to: {game_folder}")
            except Exception:
                pass
        except Exception as e:
            try:
                messagebox.showerror("Error", f"Shortcut creation failed:\n{e}")
            except Exception:
                pass

    def _cleanup_temp_icons(self):
        try:
            folder = self.icons_temp_folder
            if folder and os.path.exists(folder):
                shutil.rmtree(folder, ignore_errors=True)
        except Exception:
            pass

    def _on_close(self):
        try:
            self._cleanup_temp_icons()
        except Exception:
            pass
        try:
            self.destroy()
        except Exception:
            pass
        try:
            sys.exit(0)
        except Exception:
            pass

if __name__ == "__main__":
    PlayStoreShortcutApp().mainloop()
