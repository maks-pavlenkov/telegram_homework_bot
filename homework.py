import json
import time
from http import HTTPStatus
import logging
import requests
from telegram import Bot
from tokens import PRACTICUM_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_TOKEN
from constants import RETRY_TIME, ENDPOINT, HEADERS, HOMEWORK_STATUSES, HOST


logger = logging.getLogger(__name__)


def check_tokens():
    """Checking that all the tokens are correct."""
    if PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        logger.info('Все обязательные переменные окружения настроены')
        return True
    logger.critical('Настроены не все переменные окружения')
    return False


def get_api_answer(current_timestamp):
    """Getting API answer and checking it for availability."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(HOST + ENDPOINT, params, headers=HEADERS)
        if response.status_code != HTTPStatus.OK:
            message = f'Ответ от API Практикума {response.status_code} != 200'
            logger.critical(message)
            raise Exception(message)
        return response.json()
    except requests.exceptions.RequestException as err:
        logger.critical(err)
        raise Exception(err)
    except json.decoder.JSONDecodeError as err:
        logger.error(err)
        raise json.decoder.JSONDecodeError(err)


def check_response(response):
    """Checking the answer for correctness."""
    try:
        homeworks = response['homeworks']
    except (AttributeError, KeyError) as err:
        message = f'Ошибка доступа по ключу\n Ошибка {err}'
        logger.error(message)
        raise Exception(message)
    if not homeworks:
        message = f'Словарь homeworks пустой - {homeworks}'
        logger.error(message)
        raise Exception(message)
    if not isinstance(response, dict):
        message = f'В ответе API {type(response)} != dict'
        logger.error(message)
        raise Exception(message)
    if not isinstance(response['homeworks'], list):
        message = f'В ответе в ключе homeworks {response["homeworks"]} != list'
        logger.error(message)
        raise Exception(message)
    return response['homeworks']


def parse_status(homework):
    """Getting ready an answer message."""
    if 'homework_name' not in homework:
        logger.error(f'Атрибут homework_name не найден'
                     f' в переменной homework - {homework}')
    if 'status' not in homework:
        logger.error(f'Атрибут status не найден в переменной - {homework}')
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in HOMEWORK_STATUSES:
        message = f'Статуса {homework_status} нет в списке {HOMEWORK_STATUSES}'
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
    logger.info(f'Сообщение со статусом {message} успешно отправлено')


def main():
    """Main logic."""
    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    if not check_tokens():
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
                logger.info('Проверка обновлений ДЗ завершена')
            else:
                logger.info('Обновлений не было')
            current_timestamp = response.get('current_date', current_timestamp)
            time.sleep(RETRY_TIME)

        except Exception as error:
            logger.critical(f'Сбой в работе программы: {error}')
            time.sleep(RETRY_TIME)
            raise Exception(error)


if __name__ == '__main__':
    main()
