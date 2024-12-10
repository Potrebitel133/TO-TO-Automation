import tempfile
from pathlib import Path
from typing import Callable, Union

import customtkinter as ctk
import portalocker


class FloatSpinbox(ctk.CTkFrame):
    def __init__(
        self,
        *args,
        width: int = 100,
        height: int = 32,
        step_size: Union[int, float] = 1,
        start: Union[int, float] = 0,
        end: Union[int, float] = 100,
        command: Callable = None,
        **kwargs,
    ):
        super().__init__(*args, width=width, height=height, **kwargs)

        self.step_size = step_size
        self.command = command
        self.start = start
        self.end = end

        self.configure(fg_color=("gray78", "gray78"))  # set frame color

        self.grid_columnconfigure((0, 2), weight=0)  # buttons don't expand
        self.grid_columnconfigure(1, weight=1)  # entry expands

        self.subtract_button = ctk.CTkButton(
            self,
            text="-",
            width=height - 6,
            height=height - 6,
            command=self.subtract_button_callback,
        )
        self.subtract_button.grid(row=0, column=0, padx=(3, 0), pady=3)

        validate_cmd = self.register(self.validate_numeric)
        self.entry = ctk.CTkEntry(
            self,
            width=width - (2 * height),
            height=height - 6,
            border_width=0,
            validate="key",
            validatecommand=(validate_cmd, "%P"),
        )
        self.entry.grid(row=0, column=1, columnspan=1, padx=3, pady=3, sticky="ew")

        self.add_button = ctk.CTkButton(
            self,
            text="+",
            width=height - 6,
            height=height - 6,
            command=self.add_button_callback,
        )
        self.add_button.grid(row=0, column=2, padx=(0, 3), pady=3)

        # default value
        self.entry.insert(0, str(start))

    def validate_numeric(self, new_value):
        if new_value == "":
            return True
        try:
            int(new_value)
            return True
        except ValueError:
            return False

    def add_button_callback(self):
        if self.command is not None:
            self.command()
        try:
            if isinstance(self.step_size, int):
                value = int(self.entry.get()) + self.step_size
                if value > self.end:
                    value = self.start
            else:
                value = int(self.entry.get()) + self.step_size

            if value > self.end:
                value = self.start
            self.entry.delete(0, "end")
            self.entry.insert(0, value)
        except ValueError:
            return

    def subtract_button_callback(self):
        if self.command is not None:
            self.command()
        try:
            if isinstance(self.step_size, int):
                value = int(self.entry.get()) - self.step_size
            else:
                value = int(self.entry.get()) - self.step_size
            if value < self.start:
                value = self.end
            self.entry.delete(0, "end")
            self.entry.insert(0, value)
        except ValueError:
            return

    def get(self) -> Union[float, None]:
        try:
            return int(self.entry.get())
        except ValueError:
            return None

    def set(self, value: float):
        self.entry.delete(0, "end")
        self.entry.insert(0, str(int(value)))


def get_lock_file_path() -> Path:
    """Generate the lock file path in the system temporary directory."""
    temp_dir = Path(tempfile.gettempdir())
    return temp_dir / "robot_automation_UI_LOCK"


def is_already_running() -> bool:
    """Check if the application is already running using a temporary lock file."""
    global lock_file
    lock_file_path = get_lock_file_path()

    try:
        # Open the lock file in write mode
        lock_file = lock_file_path.open("w")
        portalocker.lock(lock_file, portalocker.LOCK_EX | portalocker.LOCK_NB)
    except portalocker.LockException:
        return True
    return False


def release_lock():
    """Release the lock and clean up the temporary lock file."""
    try:
        if lock_file:
            portalocker.unlock(lock_file)
            lock_file.close()
        # Remove the lock file from the temporary directory
        lock_file_path = get_lock_file_path()
        if lock_file_path.exists():
            lock_file_path.unlink(missing_ok=True)
    except Exception as e:
        print(f"Error releasing lock: {e}")
