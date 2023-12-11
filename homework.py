import logging
import os
import time

from http import HTTPStatus
import requests
import telegram

from dotenv import load_dotenv

load_dotenv()


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='program.log',
    filemode='w',
    level=logging.DEBUG)


PRACTICUM_TOKEN = os.getenv('PRAKTIKUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


class TheAnswerIsNot200Error(Exception):
    """Ответ сервера не равен 200."""

    pass


class RequestExceptionError(Exception):
    """Ошибка запроса."""

    pass


def check_tokens():
    """Проверка наличия токенов."""
    LOST_TOKEN = 'Данный токен не передан в работу'
    tokens_bool = True
    if PRACTICUM_TOKEN is None:
        tokens_bool = False
        logging.critical(
            f'{LOST_TOKEN} PRACTICUM_TOKEN'
        )
    if TELEGRAM_TOKEN is None:
        tokens_bool = False
        logging.critical(
            f'{LOST_TOKEN} PRACTICUM_TOKEN'
        )

    if TELEGRAM_CHAT_ID is None:
        tokens_bool = False
        logging.critical(
            f'{LOST_TOKEN} PRACTICUM_TOKEN'
        )
    return tokens_bool


def send_message(bot, message):
    """Отправка сообщения в Телеграм."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(
            f'Сообщение в Telegram отправлено: {message}')
        return True
    except telegram.TelegramError as telegram_error:
        logging.error(
            f'Сообщение в Telegram не отправлено: {telegram_error}'
        )
        return False


def get_api_answer(timestamp):
    """Функция для получения api ответов."""
    timestamp = timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        homework_statuses = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params
        )
        if homework_statuses.status_code != HTTPStatus.OK:
            logging.error('эндпойнт API не доступен!')
            raise TheAnswerIsNot200Error('эндпойнт API не доступен!')
    except requests.RequestException as request_error:
        logging.error(
            f'Код ответа API (RequestException): {request_error}'
        )
        raise RequestExceptionError(
            f'Код ответа API (RequestException): {request_error}'
        )
    return homework_statuses.json()


def check_response(response):
    """Функция для проверки."""
    if not isinstance(response, dict):
        logging.error(
            'сбой получен не словарь'
        )
        raise TypeError('response', 'dict')
    homeworks = response.get('homeworks')
    if 'homeworks' not in response:
        logging.error(
            'сбой отсутствует значение homeworks'
        )
    if not isinstance(homeworks, list):
        logging.error(
            'сбой получен не список'
        )
        raise TypeError('homeworks', 'list')
    if not homeworks:
        raise IndexError('список домашних работ пуст!')
    return homeworks


def parse_status(homework):
    """Функция для вывода информации о конкретной работе."""
    if 'homework_name' not in homework:
        logging.error(
            'сбой отсутсвие значения статуса работы'
        )
        raise Exception('сбой отсутсвие значения статуса работы')
    if homework['status'] not in HOMEWORK_VERDICTS:
        logging.error(
            'сбой неожиданное значение статуса работы'
        )
        raise Exception('сбой неожиданное значение статуса работы')
    homework_name = homework['homework_name']
    verdict = HOMEWORK_VERDICTS[homework['status']]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical('Программа принудительно остановлена.')
        return
    while True:
        try:
            bot = telegram.Bot(token=TELEGRAM_TOKEN)
            timestamp = int(time.time())
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            try:
                homeworks[0]
            except Exception:
                logging.critical('Нет новых работ')
                raise Exception('нет новых работ')
            homework = homeworks[0]
            message = parse_status(homework)
            timestamp = response.get('current_date')
            logging.debug(f'Отправлено сообщение: {message}')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.critical(message)
        finally:
            send_message(bot, message)
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
