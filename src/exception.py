"""This module contains the exceptions for the project"""


class LoginFailed(Exception):
    """Unable to login to website"""


class GameLoadFailed(Exception):
    """Unable to load the game page"""


class CombinationFailed(Exception):
    """Unable to fill the Combination"""


class BetPriceHigher(Exception):
    """The Bet price is higher than except"""


class UnknownError(Exception):
    """Unknown Error"""


class BetConfirmationFailed(Exception):
    """Unable to confirm the bet"""


class StopTheCode(Exception):
    """Stop the code to when client update in UI"""
