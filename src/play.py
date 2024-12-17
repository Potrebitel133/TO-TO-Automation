"""This module is responsible for playing the game."""

import logging
import re
import time
import traceback
import urllib.parse
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup, NavigableString, ResultSet, Tag
from requests import Response, Session

from UI.main import PlayPause, UserInputData

from .combination import Status, get_status, load_combination
from .exception import (
    BetConfirmationFailed,
    BetPriceHigher,
    CombinationFailed,
    GameLoadFailed,
    LoginFailed,
    StopTheCode,
    UnknownError,
)
from .login import login_to_page, remove_pickle
from .utils import get_error, get_soup, is_login_error


def make_request_to_game(
    session: Session, url: str
) -> tuple[BeautifulSoup, str | None]:
    """Make a request to the game and return the soup object and the base url

    Args:
        session (Session): The session object with the logged in status
        url (str): The url of the game

    Raises:
        LoginFailed: If the login is expired
        GameLoadFailed: If the game is not loaded successfully

    Returns:
        tuple[BeautifulSoup, str | None]: Tuple of soup object and the base url
    """
    response: Response = session.get(url)

    response.raise_for_status()
    soup: BeautifulSoup = get_soup(response.content)

    if error := get_error(soup):
        if is_login_error(soup):
            raise LoginFailed("Login Expired")
        logging.error("Unable to load the game %s", error)
        raise GameLoadFailed(error)
    return soup, response.request.url


def get_all_6_section(soup: BeautifulSoup) -> list[dict]:
    """Get all the 6 sections from the soup

    Args:
        soup (BeautifulSoup): The soup object to search for the sections

    Returns:
        list[dict]: List of dictionary with the section name and values
    """
    re_str: str = r"area area-\d+"  # \d+ matches one or more digits
    sections: ResultSet = soup.find_all("div", class_=re.compile(re_str))
    return [get_values_of_section(section) for section in sections]


def get_values_of_section(section: Tag) -> dict[str, str | list]:
    """Get the values of the section

    Args:
        section (Tag): The section to get the values from it

    Raises:
        Exception: If the input tag is not found

    Returns:
        dict[str, str | list]: Dictionary with the section name and values
    """
    values: list[str] = []
    inputs = section.find_all("input")
    if not inputs:
        raise ValueError("Input tag is not found in the section")
    name: str = ""

    for input_tag in inputs:
        name: str = input_tag.get("name")
        values.append(input_tag.get("value"))

    values_group: list[list[str]] = [
        values[i : i + 3] for i in range(0, len(values), 3)
    ]
    return {
        "name": name,
        "values": values_group,
    }


def get_form_url(base_request_url: str, soup: BeautifulSoup) -> str:
    """Get the form url from the soup

    Args:
        base_request_url (str): The base request url to join with the form url
        soup (BeautifulSoup): The soup object to search for the form url in it

    Raises:
        ValueError: If the form element is not found
        ValueError: If the form action attribute is missing

    Returns:
        str: The full url of the form action
    """
    form_action: Tag | NavigableString | None = soup.find("form")

    if form_action is None or isinstance(form_action, NavigableString):
        raise ValueError("No form element found in the soup.")

    form_tail_url: str | None = form_action.get("action")  # # pyright: ignore

    if form_tail_url is None:
        raise ValueError("Form action attribute is missing.")

    full_url = urllib.parse.urljoin(base_request_url, form_tail_url)

    return full_url


def load_game(session: Session, url: str) -> tuple[list[dict], str]:
    """Load the game and return the game values and the form url

    Args:
        session (Session): Logged in session
        url (str): The url of the game

    Returns:
        tuple[list[dict], str]: Tuple of game values and the form url to submit the form
    """
    soup, base_request_url = make_request_to_game(session, url)
    game_values: list[dict] = get_all_6_section(soup)
    form_url: str = get_form_url(base_request_url, soup)  # pyright: ignore

    return game_values, form_url


def play_game(combination: str, section: dict) -> dict[str, list]:
    """Play the game with the combination and the section

    Args:
        combination (str): The combination to play the game
        section (dict): The section to play the game with the combination

    Returns:
        dict[str, list]: Dictionary with the section name and the values of the combination
    """
    index_mapping: dict[str, int] = {"1": 0, "2": 2, "X": 1, "x": 1}
    combination_to_list: list[str] = [
        i.strip() for i in combination.split(",") if i.strip()
    ]
    if len(combination_to_list) != len(section["values"]):
        raise ValueError(
            f"The game in website has {len(section['values'])} \
                but got for sheet {len(combination_to_list)}"
        )
    result: list[str] = []
    for mark, values in zip(combination_to_list, section["values"]):
        result.append(values[index_mapping[mark]])

    return {section["name"]: result}


def submit_filled_form(
    session: Session, form_url: str, data: dict[str, list]
) -> tuple[BeautifulSoup, str]:
    """Submit the filled form and return the soup object and the base url

    Args:
        session (Session): Logged in session
        form_url (str): The url of the form to submit the data
        data (dict[str, list]): The data to submit the form with the section name and values

    Returns:
        tuple[BeautifulSoup, str]: Tuple of soup object and the base url of the request
    """
    response: Response = session.post(form_url, data=data)
    response.raise_for_status()
    soup: BeautifulSoup = get_soup(response.content)

    return soup, response.request.url  # pyright: ignore


def validate_filled_combination(
    soup: BeautifulSoup, max_bet_price: float = 1.2
) -> None:
    """Validate the filled combination and check if the bet price is higher

    Args:
        soup (BeautifulSoup): The soup object to validate the filled combination
        max_bet_price (float, optional): The maximum bet price allowed. Defaults to 1.2.

    Raises:
        CombinationFailed: If the combination is failed
        UnknownError: If the unknown error is raised in the filled combination
        BetPriceHigher: If the bet price is higher than the max bet price
    """
    button: Tag | None = soup.select_one("button#submit-bet")
    error_msg: str = "Unable to find the submit button"
    if not button:
        if error := get_error(soup):
            error_msg = error
            logging.info("Error in full combination %s", error)

        raise CombinationFailed(error_msg)

    bold_text: Tag | None = soup.select_one(".form-group b")
    if not bold_text:
        raise UnknownError("Unable to find the bold text")

    pattern: str = r"\d+\.\d+|\d+"
    # Search for the first match
    text: str = bold_text.get_text(strip=True)
    match: re.Match | None = re.search(pattern, text)

    # Extract and convert the matched value
    if match:
        current_price: int | float = (
            float(match.group()) if "." in match.group() else int(match.group())
        )
        logging.info("Current price %s", current_price)
        if current_price > max_bet_price:
            raise BetPriceHigher(
                f"Bet price is higher than {max_bet_price} | {current_price}"
            )


def extract_form_data(soup: BeautifulSoup) -> tuple[dict[str, str], str]:
    """Extract the form data from the soup object

    Args:
        soup (BeautifulSoup): The soup object to extract the form data

    Raises:
        ValueError: If the form is not found to conform the data

    Returns:
        tuple[dict[str, str], str]: Tuple of form data and the form url
    """
    form_data: dict = {}
    # Find the form with name="talon-bet"
    form = soup.find("form", attrs={"name": "talon-bet"})

    if not form or not isinstance(form, Tag):
        raise ValueError("Form is not found to conform ")

    form_url: str = form.get("action", "")  # # pyright: ignore

    inputs: ResultSet = form.find_all("input")
    for input_tag in inputs:
        # Get input name and value
        input_name: str | None = input_tag.get("name")
        input_value: str = input_tag.get("value", "")
        if input_name:
            form_data[input_name] = input_value

    return (form_data, form_url)


def process_combination(  # pylint: disable=too-many-locals
    session: Session,
    user_inputs: UserInputData,
    combination: pd.DataFrame,
):
    """Process the combination and play the game with the combination

    Args:
        game_url (str): The url of the game to play
        combination (pd.DataFrame): The combination to play the game with the status
        password (str): The password to verify the bet in the game
        combination_path (Path): The path of the combination file to update the status
    """
    current_processed_combination: int = 0
    grouped_combination = combination[combination["Status"] == Status.PENDING.value]
    grouped_combination = grouped_combination["Combination"].tolist()
    grouped_combination = [
        grouped_combination[i : i + 6] for i in range(0, len(grouped_combination), 6)
    ]
    for group in grouped_combination:
        game_data, form_url = load_game(session, user_inputs.game_url)
        process_form_data: dict = {}

        if len(game_data) != 6:
            raise ValueError(
                f"Group and game data length is not equal instead of 6 we got {len(game_data)}",
            )
        for comb, section in zip(group, game_data):
            # print(group, section)
            process_form_data.update(play_game(comb, section))
            logging.info("Combination %s", comb)

        print(process_form_data)
        # we need to submit the form
        soup, verify_base_url = submit_filled_form(session, form_url, process_form_data)
        validate_filled_combination(soup)
        verify_data, verify_tail_url = extract_form_data(soup)
        verify_url: str = urllib.parse.urljoin(verify_base_url, verify_tail_url)
        verify_data["talon_password"] = user_inputs.password
        logging.info("next step is to verify the bet")
        accept_verify(session, verify_url, verify_data)
        logging.info("Successfully verified the bet")
        # update df status to completed
        combination.loc[combination["Combination"].isin(group), "Status"] = (
            Status.COMPLETED.value
        )
        current_processed_combination += len(group)
        # update the file
        from .combination import Locking  # pylint: disable=import-outside-toplevel

        with Locking.lock:
            combination.to_excel(user_inputs.filename, index=False)
            # get_status
            completed, total = get_status(combination)
            user_inputs.app_object.update_progress(total, completed)
            user_inputs.app_object.sidebar_frame.timer.combination_process = (
                current_processed_combination
            )
            delay_time = user_inputs.app_object.sidebar_frame.get_delay_value()

        logging.info(
            "Successfully completed the bet of a group and sleeping for %s seconds",
            delay_time,
        )
        while to_pause(user_inputs):
            time.sleep(5)

        is_stop(user_inputs)

        time.sleep(delay_time)
    logging.info("Successfully completed the bet of all the groups")


def accept_verify(session: Session, url: str, data: dict[str, str]) -> Response:
    """Accept the verify and confirm the bet in the game

    Args:
        session (Session): Logged in session
        url (str): The url to accept the verify and confirm the bet
        data (dict[str, str]): The data to accept the verify and confirm the bet with the password

    Raises:
        BetConfirmationFailed: If the bet confirmation is failed in the game

    Returns:
        Response: The response of the accept verify
    """
    response: Response = session.post(url, data=data)
    response.raise_for_status()
    soup: BeautifulSoup = get_soup(response.content)
    if error := get_error(soup):
        logging.error("Unable to accept the verify %s", error)
        raise BetConfirmationFailed(error)
    # confirm_talon_container
    confirm_talon_container: Tag | None = soup.select_one(".confirm_talon_container")
    if not confirm_talon_container:
        raise BetConfirmationFailed("Unable to find the confirm talon container")
    # append to the confirm talon container
    file_path: Path = Path.cwd() / "confirm_talon_container.html"
    # append the confirm talon container to the file
    try:
        with open(file_path, "a", encoding="utf-8") as file:
            file.write("<br>" * 2)
            file.write(str(confirm_talon_container))
    except Exception as e:  # pylint: disable=broad-except
        logging.error("Unable to write the confirm talon container to the file %s", e)
    return response


def check_login(session: Session, game_url: str) -> bool:
    """Check if the login is successful

    Args:
        session (Session): Logged in session
        game_url (str): The url of the game to check the login

    Returns:
        bool: True if the login is successful else False
    """
    response: Response = session.get(game_url)
    response.raise_for_status()
    soup: BeautifulSoup = get_soup(response.content)
    return not is_login_error(soup)


def create_login_session(username: str, password: str, game_url: str) -> Session:
    """Create a login session and return the session object

    Args:
        username (str): Login username
        password (str): Login password
        game_url (str): The url of the game to login

    Raises:
        LoginFailed: If the login is failed

    Returns:
        Session: The session object with the logged in status
    """
    for attempt in range(3):
        session: Session = login_to_page(username, password)
        if check_login(session, game_url):
            return session

        remove_pickle()
        logging.error("Unable to login to the page so retrying attempt %s", attempt)

    raise LoginFailed("Unable to login to the page")


def play_game_main(user_inputs: UserInputData):
    """Play the game with the user inputs

    Args:
        user_inputs (UserInputData): The user inputs to play the game
    """
    combination_path: Path = Path(user_inputs.filename)
    combination: pd.DataFrame = load_combination(combination_path)
    session: Session = create_login_session(
        user_inputs.user_name, user_inputs.password, user_inputs.game_url
    )
    process_combination(session, user_inputs, combination)


def to_pause(user_inputs: UserInputData) -> bool:
    """This function used to check need to pause the code or not
    Args:
        user_inputs (UserInputData): The User inputs to play the game

    Returns:
        bool: if comment to pause return True else False
    """
    status = user_inputs.app_object.sidebar_frame.play_or_pause
    is_pause = status == PlayPause.PAUSE
    if is_pause:
        user_inputs.app_object.sidebar_frame.pause_play_btn.configure(text="play")
    return is_pause


def is_stop(user_inputs: UserInputData):
    """This function used to stop the code by raise Error
    Args:
       user_inputs (UserInputData): The User inputs to play the game

    Raises:
        StopTheCode: This raise to stop the code
    """
    if user_inputs.app_object.sidebar_frame.is_stop:
        raise StopTheCode("Stop the code")


def main(user_inputs: UserInputData):
    """Main function to play the game

    Args:
        user_inputs (UserInputData): The user inputs to play the game
    """
    try:
        print(user_inputs)
        logging.info("Starting the game")
        user_inputs.app_object.sidebar_frame.timer.start()
        play_game_main(user_inputs)
        user_inputs.app_object.complete_progress()
        logging.info("Successfully completed the game")
    except StopTheCode:
        user_inputs.app_object.add_error_label("code is stop")
    except Exception as e:  # pylint: disable=broad-except
        traceback.print_exc()
        logging.error("Traceback %s", traceback.format_exc())
        logging.error(e)
        user_inputs.app_object.save_error_log()
        user_inputs.app_object.add_error_label(str(e))

    finally:
        user_inputs.app_object.sidebar_frame.timer.stop()
        user_inputs.app_object.reset()
