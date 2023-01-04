# define Python user-defined exceptions
from discord.ext.commands import CommandError


class ConfigAccessError(Exception):
    """
    Exception raised for errors in the input.
    """

    def __init__(self, message: str):
        self.message = message


class PrimaryKeyError(Exception):
    """
    Raised if the primary key fails on insert
    """

    def __init__(self, message: str):
        self.message = message


class DesignatedChannelError(Exception):
    """
    Raised if a channel is set to a designated channel type the doesnt exist
    """

    def __init__(self, message: str):
        self.message = message


class ParserError(Exception):
    """
    Raised if user inputs bad data
    """

    def __init__(self, message: str):
        self.message = message


class ConversionError(CommandError):

    def __init__(self, message):
        self.message = message


class NoSemesterError(CommandError):
    """
    Raised if a user creates a class when there is no current semester.
    """

    pass
