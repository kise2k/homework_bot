"""Кастомные классы обработки ошибок"""


class TheAnswerIsNot200Error(Exception):
    """Ответ сервера не равен 200."""

    pass


class RequestExceptionError(Exception):
    """Ошибка запроса."""

    pass


class EmptyResponseFromApi(Exception):
    """Пустой ответ от API."""

    pass
