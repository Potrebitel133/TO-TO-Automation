import logging
import os
import random
import threading
import time
import tkinter
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from tkinter import filedialog

import customtkinter
from CTkMessagebox import CTkMessagebox
from PIL import Image

from src.combination import validate_data_frame

from .utils import FloatSpinbox

customtkinter.set_appearance_mode("System")
customtkinter.set_default_color_theme("blue")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    encoding="utf-8",
)


class PlayPause(str, Enum):
    PLAY = "PLAY"
    PAUSE = "PAUSE"


class TextHandler(logging.Handler):
    def __init__(self, text):
        logging.Handler.__init__(self)
        self.text = text

    def emit(self, record):
        msg = self.format(record)
        self.text.configure(state="normal")
        self.text.insert(tkinter.END, msg + "\n")
        # Limit the number of lines to 100
        num_lines = int(self.text.index("end-1c").split(".")[0])
        if num_lines > 500:
            self.text.delete("1.0", f"{num_lines-100}.0")
        self.text.configure(state="disabled")
        # Autoscroll to the bottom
        self.text.yview(tkinter.END)
        # add color to log message last line


class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        self.__basic_setup()
        # configure grid layout (4x4)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure((2, 3), weight=0)
        self.grid_rowconfigure(0, weight=1)
        self.stop = True
        self.filename = None
        self.debug_mode_val = False

        self.sidebar_frame = SideBarFrame(self, width=140, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")

        self.progressbar_1 = customtkinter.CTkProgressBar(self)
        self.progressbar_1.grid(
            row=0, column=1, padx=(20, 0), pady=(20, 0), sticky="ew"
        )
        self.progressbar_1.grid_forget()

        # create file upload button
        # user_input goes here
        self.user_input = UserInput(self)
        self.user_input.grid(row=0, column=1, padx=(20, 0), pady=(20, 0), sticky="nsew")

        # create textbox
        self.textbox = customtkinter.CTkTextbox(self, width=250)
        self.textbox.grid(row=0, column=1, padx=(20, 0), pady=(20, 0), sticky="nsew")
        self.textbox.insert("0.0", "No logs yet.\n")

        # create logging handler
        self.text_handler = TextHandler(self.textbox)
        self.text_handler.setLevel(logging.INFO)
        logging.getLogger().addHandler(self.text_handler)
        logging.getLogger().setLevel(logging.INFO)
        self.textbox.grid_forget()

    def __basic_setup(self):
        self.current_dir: Path = Path(__file__).resolve().parent.parent
        self.assert_dir = self.current_dir / "assets"
        # configure window
        self.title("Robot Automation")
        self.geometry("1445x800")
        icon_file: Path = self.assert_dir / "site.ico"
        if icon_file.exists():
            try:
                self.iconbitmap(icon_file)
            except Exception as _:
                pass

    def set_progress(self):
        # self.file_upload.grid_forget()
        self.user_input.grid_forget()

        # add progress bar

        # update progress bar total
        self.progressbar_1.set(0)

        self.progressbar_1.grid(
            # set below the textbox
            row=0,
            column=1,
            padx=(20, 0),
            pady=(20, 0),
            sticky="ew",
        )
        # add progress label
        self.progress_label = customtkinter.CTkLabel(
            self,
            text="Processing...",
            font=customtkinter.CTkFont(size=20, weight="bold"),
        )
        self.progress_label.grid(
            row=1, column=1, padx=(20, 0), pady=(20, 0), sticky="ew"
        )

    def complete_progress(self):
        CTkMessagebox(
            title="completed",
            message="Processing Completed",
            icon="check",
            option_1="ok",
        )

    def update_progress(self, total, processed):
        try:
            convert_processed_range_0_1 = int(processed) / int(total)
        except ZeroDivisionError:
            convert_processed_range_0_1 = 0
        except ValueError:
            convert_processed_range_0_1 = 0
        except Exception as e:
            convert_processed_range_0_1 = 0
            logging.error("Error: %s", e)
        print(convert_processed_range_0_1)
        self.progressbar_1.set(convert_processed_range_0_1)
        self.progress_label.configure(text=f"Processing... {processed}/{total}")
        print(f"Processing... {processed}/{total}")

    def start_process(self, user_ip, total, processed):
        from src.play import main

        threading.Thread(target=main, args=(user_ip,), daemon=True).start()
        self.stop = False
        self.set_progress()
        self.update_progress(total, processed)

    def add_error_label(self, message):
        # add this message to upload button text
        # self.file_upload.configure(text=message)
        # Show some error message
        CTkMessagebox(title="Error", message=message, icon="cancel")

    def save_error_log(self):
        # this fucton save log from textbox to file
        current_dir_cwd = Path.cwd()
        log_path = current_dir_cwd / f"error_log-{time.time()}.txt"
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(self.textbox.get("1.0", "end"))

    def reset(self):
        self.progressbar_1.grid_forget()
        self.progress_label.grid_forget()
        self.user_input.grid(row=0, column=1, padx=(20, 0), pady=(20, 0), sticky="nsew")
        # self.file_upload.configure(text="Upload File")
        self.progress_label.configure(text="Processing...")
        self.textbox.grid_forget()
        self.filename = None
        self.credentials = None
        self.user_input.load_from_file()
        self.stop = True
        self.sidebar_frame.reset_buttons()


class SideBarFrame(customtkinter.CTkFrame):
    def __init__(self, master, *args, **kwargs):
        super().__init__(master=master, *args, **kwargs)
        self.setup_init()
        self.play_or_pause = PlayPause.PLAY
        self.is_stop = False

    def setup_init(self):
        self.grid_rowconfigure(10, weight=1)
        self.logo_label = customtkinter.CTkLabel(
            self,
            text="Home",
            font=customtkinter.CTkFont(size=20, weight="bold"),
        )
        self.logo_label.grid(row=0, column=0, padx=30, pady=(20, 10))
        # create CTkSwitch
        self.debug_mode = customtkinter.CTkSwitch(
            self,
            text="Debug Logs",
            command=self.toggle_debug_mode,
            offvalue=False,
            onvalue=True,
        )
        self.debug_mode.grid(row=1, column=0, padx=20, pady=(10, 0))

        # label for delay
        self.delay_label = customtkinter.CTkLabel(
            self,
            text="Delay in seconds Range:",
            anchor="w",
            font=customtkinter.CTkFont(size=10, weight="bold"),
        )
        self.delay_label.grid(row=2, column=0, padx=20, pady=(10, 0))
        self.delay_val_min = FloatSpinbox(self, step_size=1, start=20, end=999)
        self.delay_val_min.grid(row=3, column=0, padx=20, pady=(10, 0))
        self.delay_val_max = FloatSpinbox(self, step_size=1, start=20, end=999)
        self.delay_val_max.set(37)
        self.delay_val_max.grid(row=4, column=0, padx=20, pady=(10, 0))

        self.timer_label = customtkinter.CTkLabel(
            self,
            text="Last Run Time",
            font=customtkinter.CTkFont(size=20, weight="bold"),
        )
        self.timer_label.grid(row=8, column=0, padx=30, pady=(20, 10))
        self.timer = Timer(self)
        self.timer.grid(row=9, column=0, padx=30, pady=(20, 10))

        self.appearance_mode_label = customtkinter.CTkLabel(
            self, text="Appearance Mode:", anchor="w"
        )

        self.appearance_mode_label.grid(row=11, column=0, padx=20, pady=(10, 0))
        self.appearance_mode_optionemenu = customtkinter.CTkOptionMenu(
            self,
            values=["Light", "Dark", "System"],
            command=self.change_appearance_mode_event,
        )
        self.appearance_mode_optionemenu.grid(row=12, column=0, padx=20, pady=(10, 10))
        self.scaling_label = customtkinter.CTkLabel(
            self, text="UI Scaling:", anchor="w"
        )
        self.scaling_label.grid(row=13, column=0, padx=20, pady=(10, 0))
        self.scaling_optionemenu = customtkinter.CTkOptionMenu(
            self,
            values=["80%", "90%", "100%", "110%", "120%"],
            command=self.change_scaling_event,
        )
        self.scaling_optionemenu.grid(row=14, column=0, padx=20, pady=(10, 20))
        self.appearance_mode_optionemenu.set("System")
        self.scaling_optionemenu.set("100%")

    def create_pause_play_stop_btn(self):
        self.play_or_pause = PlayPause.PLAY
        self.is_stop = False
        self.pause_play_btn = customtkinter.CTkButton(
            self, text="pause", command=self.on_click_play_pause, fg_color="green"
        )
        self.pause_play_btn.grid(
            row=6,
            column=0,
            padx=20,
            pady=(30, 20),
        )
        self.stop_btn = customtkinter.CTkButton(
            self, text="Stop", fg_color="red", command=self.on_click_stop
        )
        self.stop_btn.grid(row=7, column=0, padx=20, pady=(10, 20))

    def on_click_play_pause(self):
        if self.play_or_pause == PlayPause.PLAY:
            self.play_or_pause = PlayPause.PAUSE
            self.pause_play_btn.configure(fg_color="#FFA500", text="pausing")
            self.stop_btn.configure(state="disabled")

        else:
            self.play_or_pause = PlayPause.PLAY
            self.pause_play_btn.configure(fg_color="green", text="pause")
            self.stop_btn.configure(state="normal")

    def on_click_stop(self):
        self.stop_btn.configure(
            text="stopping...", fg_color="#c45e27", state="disabled"
        )
        self.pause_play_btn.configure(state="disabled")
        self.is_stop = True

    def reset_buttons(self):
        self.debug_mode.deselect()
        self.stop_btn.destroy()
        self.pause_play_btn.destroy()

    def toggle_debug_mode(self):
        self.debug_mode_val = self.debug_mode.get()
        if not self.debug_mode_val:
            self.master.textbox.grid_forget()  # type: ignore
            return

        if self.debug_mode_val:
            self.master.textbox.grid(  # type: ignore
                row=0, column=1, padx=(20, 0), pady=(20, 0), sticky="nsew"
            )

    def get_delay_value(self) -> float:
        min_val: float = 20.0
        max_val: float = 37.0
        min_val_get = self.delay_val_min.get()
        max_val_get = self.delay_val_max.get()
        if min_val_get:
            min_val = min_val_get
        if max_val_get:
            max_val = max_val_get

        # genreate random number between min and max
        return random.uniform(min_val, max_val)

    def change_appearance_mode_event(self, new_appearance_mode: str):
        customtkinter.set_appearance_mode(new_appearance_mode)

    def change_scaling_event(self, new_scaling: str):
        new_scaling_float = int(new_scaling.replace("%", "")) / 100
        customtkinter.set_widget_scaling(new_scaling_float)


@dataclass
class UserInputData:
    user_name: str
    password: str
    game_url: str
    filename: Path
    app_object: App


class UserInput(customtkinter.CTkFrame):
    def __init__(self, master: App, *args, **kwargs):
        self.master: App = master  # type: ignore
        super().__init__(master=master, *args, **kwargs)
        self.filename = None
        # inputs are
        # 1. user name
        # 2. password
        # 3. game url
        # 4. file upload
        # 5. submit button

        # grid layout for user input 5x2
        for i in range(5):
            self.grid_rowconfigure(i, weight=1)
        for i in range(4):
            self.grid_columnconfigure(i, weight=1)

        # create user name label and entry
        self.user_name_label = customtkinter.CTkLabel(self, text="User Name:")
        self.user_name_label.grid(row=0, column=0, padx=10, pady=10)
        self.user_name_entry = customtkinter.CTkEntry(self, width=500)
        self.user_name_entry.grid(row=0, column=1, padx=10, pady=10, columnspan=3)

        # create password label and entry
        self.password_label = customtkinter.CTkLabel(self, text="Password:")
        self.password_label.grid(row=1, column=0, padx=10, pady=10)
        self.password_entry = customtkinter.CTkEntry(self, width=500)
        self.password_entry.grid(row=1, column=1, padx=10, pady=10, columnspan=3)

        # create game url label and entry
        self.game_url_label = customtkinter.CTkLabel(self, text="Game URL:")
        self.game_url_label.grid(row=2, column=0, padx=10, pady=10)
        self.game_url_entry = customtkinter.CTkEntry(self, width=500)
        self.game_url_entry.grid(row=2, column=1, padx=10, pady=10, columnspan=3)

        # create file upload button
        img_path = self.master.assert_dir / "photo.png"
        img = Image.open(img_path)
        img = customtkinter.CTkImage(img, img, size=(20, 20))
        self.file_upload = customtkinter.CTkButton(
            self,
            text="Upload File",
            corner_radius=0,
            command=self.submit,
            image=img,
            fg_color="#3d98d4",
            hover=True,
            hover_color="#5c91b8",
            border_color="black",
            border_spacing=1,
            border_width=2,
            text_color="black",
        )
        # self.file_upload.grid(row=3, column=0, columnspan=2, padx=10, pady=10)
        self.file_upload.grid(
            row=3, column=0, columnspan=4, padx=(20, 0), pady=(20, 0), sticky="nsew"
        )

        # create submit button
        # merge the two columns
        # self.submit_button = customtkinter.CTkButton(self, text="Submit",command=self.submit)
        # self.submit_button.grid(row=4, column=0, columnspan=2, padx=10, pady=10,)

        self.load_from_file()

    def clear_entries(self):
        self.user_name_entry.delete(0, tkinter.END)
        self.password_entry.delete(0, tkinter.END)
        self.game_url_entry.delete(0, tkinter.END)

    def load_from_file(self):
        current_dir_cwd = os.getcwd()
        credentials_path = Path(current_dir_cwd) / "credentials.txt"
        if not credentials_path.exists():
            return
        with open(credentials_path, "r") as f:
            lines = f.readlines()
            if len(lines) == 3:
                self.clear_entries()
                self.user_name_entry.insert(0, lines[0].strip())
                self.password_entry.insert(0, lines[1].strip())
                self.game_url_entry.insert(0, lines[2].strip())

    def validate_input(self):
        inputs = {}
        inputs["user_name"] = self.user_name_entry.get()
        inputs["password"] = self.password_entry.get()
        inputs["game_url"] = self.game_url_entry.get()
        error_message = ""
        for key, value in inputs.items():
            if not value or value.strip() == "":
                error_message += f"{key} cannot be empty\n"
        if error_message:
            CTkMessagebox(title="Error", message=error_message, icon="cancel")
            return False
        return True

    def select_file(self):
        # select image only 1 image as max
        self.filename = filedialog.askopenfilename(
            initialdir="./",
            title="select xlsx file",
            filetypes=(("csv files", "*.xlsx"),),  # Corrected to be a tuple of tuples
        )
        if isinstance(self.filename, str) is False:
            return

        self.filename = Path(self.filename)
        if not self.filename.exists() or not self.filename.is_file():
            self.master.add_error_label("Upload File \n Error: File not found")
            return
        info, is_valid = validate_data_frame(self.filename)

        if not is_valid:
            self.master.add_error_label(
                "Upload File \n Error: Combination column not found"
            )
            return
        user_ip = self.create_user_input_data()
        return user_ip, info[1], info[0]

    def create_user_input_data(self) -> UserInputData:
        return UserInputData(
            user_name=self.user_name_entry.get(),
            password=self.password_entry.get(),
            game_url=self.game_url_entry.get(),
            filename=self.filename,  # type: ignore
            app_object=self.master,
        )

    def save_to_file(self):
        current_dir_cwd = os.getcwd()
        credentials_path = Path(current_dir_cwd) / "credentials.txt"
        with open(credentials_path, "w") as f:
            f.write(self.user_name_entry.get() + "\n")
            f.write(self.password_entry.get() + "\n")
            f.write(self.game_url_entry.get() + "\n")

    def submit(self):
        if not self.validate_input():
            return
        self.save_to_file()
        select_file_response = self.select_file()
        if not select_file_response:
            return
        user_ip, total, processed = select_file_response
        self.master.sidebar_frame.create_pause_play_stop_btn()
        self.master.start_process(user_ip, total, processed)
        # call main function
        # main()
        # check_csv_file_has_query_column()


class Timer(customtkinter.CTkFrame):
    def __init__(self, master, *args, **kwargs):
        super().__init__(master=master, *args, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.is_paused = False
        self.is_stop = False
        self.combination_process = 0
        self.timer_label = customtkinter.CTkLabel(
            self,
            text="00:00:00",
            font=customtkinter.CTkFont(size=20, weight="bold"),
        )
        self.timer_label.grid(row=0, column=0, padx=30, pady=(20, 10))
        self.combination_process_label = customtkinter.CTkLabel(
            self,
            text=f"Combination Process : {self.combination_process}",
            font=customtkinter.CTkFont(size=10, weight="bold"),
        )
        self.combination_process_label.grid(row=1, column=0, padx=30, pady=(20, 10))
        self.start_time = 0

    def update_timer(self):
        if self.is_stop:
            return
        if self.is_paused is False:
            self.start_time += 1  # increment by 1 second
        hours, remainder = divmod(self.start_time, 3600)
        minutes, seconds = divmod(remainder, 60)
        self.timer_label.configure(
            text=f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"
        )
        self.combination_process_label.configure(
            text=f"Combination Process : {self.combination_process}"
        )
        self.after(1000, self.update_timer)  # run every 1 second

    # method are
    # 1. start
    # 2. pause
    # 3. stop
    # 4. reset
    def start(self):
        self._reset()
        self.start_time = 0
        self.combination_process = 0
        self.update_timer()

    def pause(self):
        self.is_paused = not self.is_paused

    def stop(self):
        self.is_stop = True

    def _reset(self):
        self.timer_label.configure(text="00:00:00")
        self.is_stop = False
        self.is_paused = False


if __name__ == "__main__":
    app = App()
    app.mainloop()
