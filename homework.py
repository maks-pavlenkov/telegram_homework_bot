import logging
import sys
from telegram import Bot
from dotenv import load_dotenv
import os
import time
import requests
from logging import StreamHandler, Formatter
from http import HTTPStatus

load_dotenv()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = StreamHandler(stream=sys.stdout)
handler.setFormatter(Formatter(fmt='%(asctime)s - %(name)s - '
                                   '%(levelname)s - %(message)s'))
logger.addHandler(handler)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

tokens = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Checking that all the tokens are correct."""
    if PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        message = 'Все обязательные переменные окружения настроены'
        logger.info(message)
        return True
    else:
        message = 'Настроены не все переменные окружения'
        logger.critical(message)
        return False


def get_api_answer(current_timestamp):
    """Getting API answer and checking it for availability."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, params, headers=HEADERS)
        if response.status_code != HTTPStatus.OK:
            message = 'Ответ от API Практикума не 200'
            logger.critical(message)
            raise Exception(message)
        return response.json()
    except requests.exceptions.RequestException as err:
        logger.critical(err)
        raise Exception(err)


def check_response(response):
    """Checking the answer for correctness."""
    try:
        homeworks = response['homeworks']
    except (AttributeError, KeyError) as err:
        message = f'Ошибка доступа по ключу\n Ошибка {err}'
        logger.error(message)
        raise Exception(message)
    if not homeworks:
        message = 'Словарь пустой'
        logger.error(message)
        raise Exception(message)
    if not isinstance(response, dict):
        message = 'В ответе не словарь'
        logger.error(message)
        raise Exception(message)
    if not isinstance(response['homeworks'], list):
        message = 'В ответе в ключе homeworks не список'
        logger.error(message)
        raise Exception(message)
    return response['homeworks']


def parse_status(homework):
    """Getting ready an answer message."""
    if 'homework_name' not in homework:
        message = 'Атрибут homework не найден в переменной'
        logger.error(message)
    if 'status' not in homework:
        message = 'Атрибут status не найден в переменной'
        logger.error(message)
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in HOMEWORK_STATUSES:
        message = 'Неизвестный статус домашней работы'
        logger.error(message)
        raise Exception(message)
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def send_message(bot, message):
    """Sending a message."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception as err:
        logger.critical(err)
        raise Exception(err)
    else:
        message = 'Сообщение успешно отправлено'
        logger.info(message)


def main():
    """Main logic."""
    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    if not check_tokens(tokens):
        return
    response = get_api_answer(current_timestamp)
    homework = check_response(response)
    latest_status = ''
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            if homework and homework[0]['status'] != latest_status:
                message = parse_status(homework[0])
                send_message(bot, message)
                latest_status = homework[0]['status']
                message = 'Проверка обновлений ДЗ завершена'
                logger.info(message)
            else:
                message = 'Обновлений не было'
                logger.info(message)
            current_timestamp = response.get('current_date', current_timestamp)
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.critical(message)
            time.sleep(RETRY_TIME)
            raise Exception(error)


if __name__ == '__main__':
    main()
