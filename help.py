import tkinter as tk
import webbrowser
import json
from jaypy import centerwindow
import os
import sys

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def get_version_from_settings():
    try:
        settings_path = resource_path("settings.json")
        with open(settings_path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
            return data.get("version", "Unknown")
    except Exception:
        return "Unknown"

def open_help_popup(parent=None):
    version = get_version_from_settings()
    help_window = tk.Toplevel(parent)
    help_window.title("About")
    help_window.geometry("550x350")
    help_window.configure(bg="#121212")
    centerwindow(help_window, offsety=-40)

    container = tk.Frame(help_window, bg="#1e1e1e", bd=2, relief="flat")
    container.place(relx=0.5, rely=0.5, anchor="center", width=500, height=320)

    canvas = tk.Canvas(container, bg="#1e1e1e", highlightthickness=0)
    scrollbar = tk.Scrollbar(container, orient="vertical", command=canvas.yview)
    scroll_frame = tk.Frame(canvas, bg="#1e1e1e")

    scroll_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    title = tk.Label(
        scroll_frame,
        text="Create Shortcut on PC Emulator",
        font=("Segoe UI", 16, "bold"),
        bg="#1e1e1e",
        fg="#00d5ff",
        pady=10
    )
    title.pack(anchor="center")

    version_label = tk.Label(
        scroll_frame,
        text=f"Version {version}",
        font=("Segoe UI", 10, "italic"),
        bg="#1e1e1e",
        fg="#aaaaaa",
        pady=5
    )
    version_label.pack(anchor="center")

    about_text = (
        "This feature allows you to create desktop shortcuts for games or apps\n"
        "launched through Google Play Games or the LDPlayer emulator. With a single click, "
        "you can directly launch your favorite game without manually opening the emulator.\n"
        "\n"
        "Update (Note: Not final. I will revise this later):\n"
        "Date: August 01, 2025\n"
        "• Redesigned the game list into 2 columns and 5 rows with icons\n"
        "• Added a Help button to view this information\n"
        "\n"
        "Date: August 05, 2025\n"
        "• Added settings to set the file location for platforms (Google Play Games Beta and LDPlayer 9)\n"
        "• Settings will pop up if the platform file location is not found\n"
        "• Previously, only the US Play Store was searchable. Now, you can choose the preferred language and country to search\n"
        "• The window now opens in the center\n"
        "• Icon added to the top-left corner of the window\n"
        "• You can now copy the package name by clicking on the label\n"
        "• I added my custom py library \"jaypy\" to make the repetition code lesser. It's still WIP so it's not in online libraries yet\n"
        "• Make code refactored\n"
        "• Version of this software and my link on Youtube, Github are now added on help\n"
        "\n"
        "Date: October 30, 2025\n"
        "• Fixed on Settings not save on changing language and country\n"
        "• Prevent Settings Pop-up from duplicating when click on settings icon\n"
        "• Fixed on not detected LDPlayer file location from settings\n"
        "• Added loading indicator on game select for faster loading\n"
        "• Added package name input (manual input link by copy link on play store and paste on the input to get the package name) if the package name of the selected game is \"None\"\n"
        "\n"
        "Date: November 02, 2025\n"
        "• Some Games cannot successfully create shortcut due to wrong file encode input. Now, it fixed by using regex, but idk if it's solved on all of them\n"
        "• Added function to search Play Store URL on Game Search\n"
        "\n"
        "Date: November 29, 2025\n"
        "• You can now change the index of the LDPlayer. The index indicates which instance of LDPlayer to use when multiple instances are running\n"
        "• Added mouse scroll up and down vertical function on help window\n"
        "• Found abnormality of producing game icons, so need to delete all of them from the \"gamelist_icons\" folder then reproduce the icon again when searching. Use temporary storage instead of \"gamelist_icons\" in the future updates\n"
        "\n"
        "Date: November 30, 2025\n"
        "• If the package name is NA, it will get the full link and get the package name there\n"
        "• Added Play Store Link text label, when it click, it will pop up on the website\n"
        "\n"
        "Date: December 01, 2025\n"
        "• Add pop up \"Game Not Found\" when the game is not found instead it said \"'NoneType' object is not subscriptable\"\n"
        "• Change the system of storing the game icon, it is now on the temp folder\n"
        "• Add settings of where it stores the game folder when the game shortcut is created\n"
        "\n"
        "Created by Jayrald John C. Dalman."
    )

    body = tk.Label(
        scroll_frame,
        text=about_text,
        font=("Segoe UI", 10),
        bg="#1e1e1e",
        fg="#f0f0f0",
        justify="left",
        wraplength=460,
        padx=15,
        pady=5
    )
    body.pack(anchor="center")

    def open_link(url):
        webbrowser.open(url)

    link_frame = tk.Frame(scroll_frame, bg="#1e1e1e")
    link_frame.pack(anchor="center", pady=10)

    yt_button = tk.Button(
        link_frame,
        text="YouTube",
        font=("Segoe UI", 10, "underline"),
        fg="#00d5ff",
        bg="#1e1e1e",
        bd=0,
        cursor="hand2",
        activeforeground="#00ffff",
        command=lambda: open_link("https://www.youtube.com/@dalmanskigd")
    )
    yt_button.pack(side="left", padx=10)

    gh_button = tk.Button(
        link_frame,
        text="GitHub",
        font=("Segoe UI", 10, "underline"),
        fg="#00d5ff",
        bg="#1e1e1e",
        bd=0,
        cursor="hand2",
        activeforeground="#00ffff",
        command=lambda: open_link("https://github.com/Dalmanski/Create-Shortcut-on-PC-Emulator")
    )
    gh_button.pack(side="left", padx=10)

    def _on_mousewheel(event):
        if getattr(event, "num", None) == 4:
            canvas.yview_scroll(-1, "units")
            return
        if getattr(event, "num", None) == 5:
            canvas.yview_scroll(1, "units")
            return
        delta = 0
        try:
            delta = int(event.delta)
        except Exception:
            try:
                delta = event.delta
            except Exception:
                delta = 0
        if delta:
            if abs(delta) >= 120:
                steps = int(-1 * (delta / 120))
            else:
                steps = -1 if delta > 0 else 1
            canvas.yview_scroll(steps, "units")

    def _bind_mousewheel(event):
        help_window.bind_all("<MouseWheel>", _on_mousewheel)
        help_window.bind_all("<Button-4>", _on_mousewheel)
        help_window.bind_all("<Button-5>", _on_mousewheel)

    def _unbind_mousewheel(event):
        try:
            help_window.unbind_all("<MouseWheel>")
        except Exception:
            pass
        try:
            help_window.unbind_all("<Button-4>")
        except Exception:
            pass
        try:
            help_window.unbind_all("<Button-5>")
        except Exception:
            pass

    canvas.bind("<Enter>", _bind_mousewheel)
    canvas.bind("<Leave>", _unbind_mousewheel)
    help_window.mainloop()

if __name__ == "__main__":
    open_help_popup()
