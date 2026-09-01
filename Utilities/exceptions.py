from discord.ext import commands


class FormattingException(Exception):
    pass


class PagifyException(FormattingException):
    pass


class FormatTimeException(FormattingException):
    pass


class DataManagerException(Exception):
    pass


class UserIsBlacklisted(commands.CheckFailure):
    pass
