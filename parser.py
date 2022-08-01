import re
import requests
from bs4 import BeautifulSoup
import urllib3
import schedule
import time
from const import login, password, list_cities


def authorization():
    """Здесь происходит процесс авторизаций, функция вызывается однократно."""
    urllib3.disable_warnings()

    session = requests.Session()

    login_url = 'https://justiva.ru/login'
    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml',
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36',
    }

    response = session.get(login_url, headers=headers, verify=False)
    soup = BeautifulSoup(response.text, 'lxml')
    _token = soup.select_one('meta[name="csrf-token"]')['content']

    headers['cookie'] = '; '.join([x.name + '=' + x.value for x in response.cookies])
    headers['content-type'] = 'application/x-www-form-urlencoded'
    payload = {
        '_token': _token,
        'email': login,
        'password': password,
        'remember': 'true',
    }

    response = session.post(login_url, data=payload, headers=headers, verify=False)

    print('Статус авторизации: ', response.status_code)

    url = 'https://justiva.ru/account/stock-leads/'

    response = session.get(url, verify=True)

    soup = BeautifulSoup(response.text, 'lxml')
    _token = soup.select_one('meta[name="csrf-token"]')['content']

    headers['cookie'] = '; '.join([x.name + '=' + x.value for x in response.cookies])
    headers['content-type'] = 'application/json'
    headers['x-csrf-token'] = soup.select_one('meta[name="csrf-token"]')['content']

    return session, headers


def buying_slots(session, headers):
    """Функция, отвечающая за покупку слотов, и парсинг полученной информаций."""
    start = time.time()

    with open('lastkey.txt', 'r') as f:
        last_id = f.read()

    last_id = int(last_id)
    url = 'https://justiva.ru/account/stock-leads/'
    response = session.get(url, verify=False)
    soup = BeautifulSoup(response.text, 'lxml')

    city = soup.find('div', class_='lead_city')
    ident_with_href = soup.select_one('div.lead_time > a')

    cities = (city.text.strip())
    identifier = re.sub('https://justiva.ru/question/', '', ident_with_href['href'])

    # Если спарсенный идентификатор больше последнего записанного, и искомый город есть в нашем списке, то идём дальше
    if int(identifier) > last_id and cities in list_cities:
        # Здесь скрипт покупает слот посредством отправки пост запроса

        login_url = 'https://justiva.ru/account/buy-client/{0}'.format(str(identifier))

        response = session.post(login_url, headers=headers, verify=False)
        end = time.time()

        print('\nСтатус слота: ', response.text)
        print('Время выполнения: ', end - start)
        print(login_url)

        return identifier


def parsing_info(identifier, session):
    """Функция вызывается строго после покупки заявки, и парсит инфу с купленной заявки."""
    url = 'https://justiva.ru/account/stock-leads/'
    response = session.get(url, verify=False)
    soup = BeautifulSoup(response.text, 'lxml')

    title = soup.find('div', class_='lead_question_title').text.strip()
    question = soup.find('div', class_='lead_question_content').text.strip()
    time = soup.find('div', class_='lead_time').text.strip()
    city = soup.find('div', class_='lead_city').text.strip()
    name = soup.select_one('div > div.lead__name').text.strip()
    mail = soup.select_one('div > div.lead__email').text.strip()
    phone = soup.select_one('div > div.lead__phone').text.strip()

    log_info = {
        'Заголовок': title,
        'Вопрос': question,
        'Время': time,
        'Город': city,
        'Имя пользователя': name,
        'Емайл': mail,
        'Телефон': phone,
    }

    with open('logs.txt', 'a') as f:
        f.write(str(log_info))

    with open('lastkey.txt', 'w') as f:
        f.write(str(identifier))

    return log_info


# Получение данных сессий
session_data, headers_data = authorization()


def main():
    identifier_slot = buying_slots(session_data, headers_data)
    if identifier_slot:
        parsing_info(identifier_slot, session_data)


schedule.every(1).to(1).seconds.do(main)

while True:
    schedule.run_pending()
    time.sleep(1)
