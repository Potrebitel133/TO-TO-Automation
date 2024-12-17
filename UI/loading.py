"""
This module handles the loading screen and animation for the application.
"""

import time
from pathlib import Path
from tkinter import SUNKEN, Frame, Label, Tk

from PIL import Image, ImageTk

from .main import App

w = Tk()

# Centering the window on screen
WIDTH_OF_WINDOW = 427
HEIGHT_OF_WINDOW = 250
screen_width = w.winfo_screenwidth()
screen_height = w.winfo_screenheight()
x_coordinate = (screen_width / 2) - (WIDTH_OF_WINDOW / 2)
y_coordinate = (screen_height / 2) - (HEIGHT_OF_WINDOW / 2)
w.geometry(
    f"{WIDTH_OF_WINDOW}x{HEIGHT_OF_WINDOW}+{int(x_coordinate)}+{int(y_coordinate)}"
)

w.overrideredirect(True)  # for hiding titlebar


def new_win():
    """Function to start the main application window."""
    app = App()
    app.mainloop()


# GUI elements setup
Frame(w, width=427, height=250, bg="#272727").place(x=0, y=0)
label1 = Label(w, text="Welcome", fg="white", bg="#272727")
label1.configure(font=("Calibri", 24, "bold"))
label1.place(x=80, y=90)

LOADING_TXT = "Loading..."
label2 = Label(w, text=LOADING_TXT, fg="white", bg="#272727")
label2.configure(font=("Calibri", 11))
label2.place(x=10, y=215)
base_dir: Path = Path(__file__).resolve().parent.parent
image_path_c1 = base_dir / "assets" / "c1.png"
image_path_c2 = base_dir / "assets" / "c2.png"
image_a = ImageTk.PhotoImage(Image.open(image_path_c2))
image_b = ImageTk.PhotoImage(Image.open(image_path_c1))


def load_animation(loop=4):
    """Function to manage loading animation."""
    for _ in range(loop):
        for img, x_coord in zip(
            [image_a, image_b, image_b, image_b], [180, 200, 220, 240]
        ):
            Label(w, image=img, border=0, relief=SUNKEN).place(x=x_coord, y=145)  # type: ignore
            w.update_idletasks()
            time.sleep(0.5)


def launch_main():
    """Main loop for managing animation while download is in progress."""
    load_animation(1)
    w.destroy()  # Destroy the loading window
    new_win()  # Launch the main application window
    w.mainloop()
