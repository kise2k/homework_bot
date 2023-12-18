import logging
import os
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from exceptions import (TheAnswerIsNot200Error,
                        EmptyResponseFromApi)

load_dotenv()

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


def check_tokens():
    """Проверка наличия токенов."""
    tokens_bool = True
    TOKENS = (
        ('PRAKTIKUM_TOKEN', PRACTICUM_TOKEN),
        ('TELEGRAM_TOKEN', TELEGRAM_TOKEN),
        ('TELEGRAM_CHAT_ID', TELEGRAM_CHAT_ID),
    )
    for name, token in TOKENS:
        if not token:
            logging.critical(
                f'Потерян токен:{name}'
            )
            tokens_bool = False
    if not tokens_bool:
        raise ValueError(f'Потерян токен:{name}')


def send_message(bot, message):
    """Отправка сообщения в Телеграм."""
    logging.info(f'Попытка отправить сообщение в Telegram: {message}')
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
    params = {'from_date': timestamp}
    parametrs = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': params,
    }
    logging.info('запрос {url} c {headers} и {params}'.format(**parametrs))
    try:
        homework_statuses = requests.get(**parametrs)
        if homework_statuses.status_code != HTTPStatus.OK:
            raise TheAnswerIsNot200Error(
                'код ошибки: {status_code} \
                причина ошибки: {reason} \
                текст ошибки: {text}'.format(**parametrs)
            )
    except requests.RequestException:
        raise ConnectionError(
            'ошибка параметров {url}, {headers}, {params}'.format(**parametrs)
        )
    return homework_statuses.json()


def check_response(response):
    """Функция для проверки."""
    if not isinstance(response, dict):
        raise TypeError(f'тип {response} не соответствует типу dict')
    homeworks = response.get('homeworks')
    if 'homeworks' not in response:
        raise EmptyResponseFromApi('сбой отсутствует значение homeworks')
    if not isinstance(homeworks, list):
        raise TypeError(f'тип {homeworks} не соответствует типу list')
    return homeworks


def parse_status(homework):
    """Функция для вывода информации о конкретной работе."""
    if 'homework_name' not in homework:
        raise ValueError(
            'сбой значение имени работы нет в работах'
        )
    if 'status' not in homework:
        raise ValueError('сбой значение статуса отсутствует')
    status = homework['status']
    if status not in HOMEWORK_VERDICTS:
        raise ValueError(
            'сбой неожиданное значение статуса работы'
        )
    homework_name = homework['homework_name']
    verdict = HOMEWORK_VERDICTS[homework['status']]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = 0
    last_message = ''
    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if homeworks:
                homework = homeworks[0]
                message = parse_status(homework)
            else:
                message = 'Нет новых статусов!'
            if message != last_message:
                if send_message(bot, message):
                    last_message = message
                    timestamp = response.get('current_date', timestamp)
            else:
                logging.info(message)
        except EmptyResponseFromApi as error:
            logging.error(f'Пустой ответ от API {error}')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.exception(message)
            if message != last_message:
                send_message(bot, message)
                last_message = message
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    file_handler = logging.FileHandler(
        __file__ + '.log',
        mode='w',
        encoding='UTF-8'
    )
    stream_handler = logging.StreamHandler()
    handlers = [file_handler, stream_handler]
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s \
          - %(message)s - Line %(lineno)d',
        level=logging.INFO,
        handlers=handlers,
    )
    main()
