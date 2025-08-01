import tkinter as tk

def open_help_popup(parent=None):
    help_window = tk.Toplevel(parent)
    help_window.title("About")
    help_window.geometry("550x350")
    help_window.configure(bg="#121212")

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
        pady=15
    )
    title.pack(anchor="center")

    about_text = (
        "This feature allows you to create desktop shortcuts for games or apps\n"
        "launched through Google Play Games or LDPlayer emulator. With a single click,\n"
        "you can directly launch your favorite game without opening the emulator manually.\n"
        "\n"
        "Update (Not final. I will revise this later):\n"
        "Date: August 01, 2025\n"
        "• Redesign game list like 2 columns and 5 rows with icon pictures\n"
        "• Added Help button to see this\n"
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

    help_window.mainloop()

if __name__ == "__main__":
    open_help_popup()
