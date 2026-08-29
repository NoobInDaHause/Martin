class FormattingException(Exception):
    pass


class PagifyException(FormattingException):
    pass


class FormatListException(FormattingException):
    pass


class FormatTimeException(FormattingException):
    pass


class DataManagerException(Exception):
    pass
