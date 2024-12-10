"""
This module is responsible for reading the excel file and updating the status of the combination.
It also validates the file path and the data frame.

"""

import logging
import threading
from enum import Enum
from pathlib import Path

import pandas as pd


class Locking:  # pylint: disable=too-few-public-methods
    """Locking class to handle the thread lock"""

    lock = threading.Lock()


class Status(str, Enum):
    """Status Enum class to handle the status of the combination"""

    PENDING = "pending"
    COMPLETED = "completed"


def read_excel(file_path: Path) -> pd.DataFrame:
    """Read the excel file and return the data frame

    Args:
        file_path (Path): Path of the excel file

    Returns:
        pd.DataFrame: Data frame of the excel file
    """
    return pd.read_excel(file_path)


def validate_file_path(file_path: Path) -> bool:
    """Validate the file path

    Args:
        file_path (Path): Path of the file to validate

    Returns:
        bool: True if the file path is valid else False
    """
    return file_path.exists() and file_path.is_file() and file_path.suffix == ".xlsx"


def validate_data_frame(file_path: Path) -> tuple[tuple, bool]:
    """Validate the data frame and return the status of the combination

    Args:
        file_path (Path): Path of the file to validate

    Returns:
        tuple[tuple, bool]: Tuple of completed and total \
            count and boolean value if the combination column is present
    """
    with Locking.lock:
        try:
            df = read_excel(file_path)
            # if it has combination column or not case insensitive
            return get_status(df), "combination" in df.columns.str.lower()
        except Exception as e:  # pylint: disable=broad-except
            logging.error("Error while reading file %s %s", file_path, e)
            return (0, 0), False


def update_combination_status(df: pd.DataFrame) -> pd.DataFrame:
    """Update the status of the combination

    Args:
        df (pd.DataFrame): Data frame to update the status of the combination

    Returns:
        pd.DataFrame: Data frame with updated status of the combination
    """
    # reame columns if combination the set Combination
    df.columns = df.columns.str.capitalize()

    if "Status" not in df.columns:
        df["Status"] = Status.PENDING.value
    else:
        df["Status"] = df["Status"].apply(
            lambda x: Status.PENDING.value if x != Status.COMPLETED.value else x
        )
    return df


def get_status(df: pd.DataFrame) -> tuple[int, int]:
    """Get the status of the combination

    Args:
        df (pd.DataFrame): Data frame to get the status of the combination

    Returns:
        tuple[int, int]: Tuple of completed and total count
    """
    total = len(df)
    if "Status" not in df.columns:
        return 0, total
    completed = len(df[df["Status"] == Status.COMPLETED.value])
    return completed, total


def load_combination(file_path: Path) -> pd.DataFrame:
    """Load the combination from the excel file and update the status of the combination

    Args:
        file_path (Path): Path of the excel file to load the combination

    Raises:
        FileNotFoundError: If the file path is invalid

    Returns:
        pd.DataFrame: Data frame with updated status of the combination
    """
    if not validate_file_path(file_path):
        raise FileNotFoundError(f"Invalid file path {file_path}")
    df = read_excel(file_path)

    return update_combination_status(df)
