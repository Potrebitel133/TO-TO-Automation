"""
This module contains utility functions that are used in the main module.
"""

from bs4 import BeautifulSoup, NavigableString, Tag

bs4_find_type = Tag | NavigableString | None


def get_error(soup: BeautifulSoup) -> str | None:
    """Get the error message from the soup

    Args:
        soup (BeautifulSoup): Soup object to search for the error

    Returns:
        str | None: Error message if found else None
    """
    error: bs4_find_type = soup.find(class_="error")
    if isinstance(error, Tag):
        return error.string
    return None


def get_soup(response: str | bytes) -> BeautifulSoup:
    """Get the soup object from the response

    Args:
        response (str | bytes): Response from the request example response.text or response.content

    Returns:
        BeautifulSoup: Soup object from the response using html.parser
    """
    return BeautifulSoup(response, "html.parser")


# create a decorator to handle the login error
def is_login_error(soup: BeautifulSoup) -> bool:
    """Check if the login error is present in the soup

    Args:
        soup (BeautifulSoup): Soup object to search for the login error

    Returns:
        bool: True if login error is present else False
    """
    login_form: bs4_find_type = soup.find(id="login-form")
    return isinstance(login_form, Tag)
