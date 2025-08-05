def centerwindow(window, offsetx=0, offsety=0):
    window.update_idletasks()
    width = window.winfo_width()
    height = window.winfo_height()
    screen_w = window.winfo_screenwidth()
    screen_h = window.winfo_screenheight()
    x = (screen_w - width) // 2 + offsetx
    y = (screen_h - height) // 2 + offsety
    window.geometry(f"{width}x{height}+{x}+{y}")