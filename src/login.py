"""This module is responsible for creating a session and logging in to the page"""

import logging
import pickle
from pathlib import Path

from bs4 import BeautifulSoup
from requests import Response
from requests.sessions import Session

from .exception import LoginFailed
from .utils import get_error, get_soup


def session_to_pickle(session: Session | None = None) -> Session | None:
    """Save the session to a pickle file

    Args:
        session (Session): Session object to save
    """
    cwd = Path.cwd()
    session_file = cwd / "session.pickle"
    if session is None:
        if session_file.exists() is False:
            logging.error("No session file found")
            return None
        with open(session_file, "rb") as file:
            session = pickle.load(file)
            logging.info("Session loaded from pickle file")
            return session
    with open(session_file, "wb") as file:
        pickle.dump(session, file)
        logging.info("Session saved to pickle file")
        return session


def remove_pickle():
    """Remove the pickle file"""
    cwd = Path.cwd()
    session_file = cwd / "session.pickle"
    session_file.unlink(missing_ok=True)


def create_session() -> Session:
    """Create a session and return it"""

    session: Session = Session()
    headers: dict[str, str] = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",  # pylint: disable=line-too-long
        "Accept-Language": "en-US,en;q=0.9,ta;q=0.8",
        "Cache-Control": "max-age=0",
        "Connection": "keep-alive",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",  # pylint: disable=line-too-long
        "sec-ch-ua": '"Chromium";v="130", "Google Chrome";v="130", "Not?A_Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Linux"',
    }
    session.headers.update(headers)

    response: Response = session.get(
        "https://toto.bg/",
    )
    response.raise_for_status()
    logging.info("Session created")
    return session


def login_to_page(user_name: str, password: str) -> Session:
    """Login to the page and return the session

    Args:
        user_name (str): User name to login
        password (str): Password to login

    Raises:
        LoginFailed: If login fails

    Returns:
        Session: Session object with logged in status
    """
    session: Session | None = session_to_pickle()
    if session is not None:
        return session

    session = create_session()

    params: dict[str, str] = {
        "lang": "1",
        "pid": "loginonline",
    }

    data: dict[str, str] = {
        "username": user_name,
        "password": password,
        "g-recaptcha-response": "",
    }

    response: Response = session.post(
        "https://toto.bg/index.php", params=params, data=data
    )
    response.raise_for_status()
    soup: BeautifulSoup = get_soup(response.text)
    if error := get_error(soup):
        logging.error("unable to login to the page %s", error)
        raise LoginFailed(error)
    logging.info("Successfully logged in")

    return session_to_pickle(session)  # # pyright: ignore
