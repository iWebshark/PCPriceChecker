import telebot
import bs4
import requests
import schedule
import time
import threading
from urllib.parse import urlparse
import os
from flask import Flask, request

secret = 'ef54dfcbd52e49988755a23a04d47ac9'
url = 'https://pc-price-checker.herokuapp.com/' + secret
TOKEN = '1471126006:AAGPy4aQAaRqOnceNUYvE87wcHwOO2b2KDU'
bot = telebot.TeleBot(TOKEN)
bot.remove_webhook()
bot.set_webhook(url=url)

components = {'GPU': ('https://catalog.onliner.by/videocard/gigabyte/gvn3070gamingoc8', '2200'),
              'CPU': ('https://catalog.onliner.by/cpu/amd/rzn55600x', '850'),
              'MB': ('https://catalog.onliner.by/motherboard/gigabyte/b550aoruselite', '450')}

app = Flask(__name__)


@app.route('/' + secret, methods=['POST'])
def webhook():
    update = telebot.types.Update.de_json(request.stream.read().decode('utf-8'))
    bot.process_new_updates([update])
    return 'ok', 200


@bot.message_handler(commands=['start', 'help'])
def on_start(message: telebot.types.Message):
    with open('users.txt', 'r+') as users_file:
        if str(message.chat.id) not in users_file.read():
            answer = f'Ку здарова, {message.chat.username}\n' \
                     f'Записал тебя'
            users_file.write(f'{message.chat.id}\n')
        else:
            answer = f'И снова здравствуйте, {message.chat.username}'
    bot.send_message(message.chat.id, answer)


def monitor_price():
    for key, data in components.items():
        bs = bs4.BeautifulSoup(requests.get(data[0]).text, 'lxml')
        low_price = bs.find('span', itemprop="lowPrice")
        # Ищем минимальную цену
        if low_price is not None:
            low_price = low_price.get_text()
            # Сделать рассылку если цена приемлимая
            if float(low_price) <= float(data[1]):
                send_user_message(bs, data, is_profitable=True)


def show_prices():
    for key, data in components.items():
        bs = bs4.BeautifulSoup(requests.get(data[0]).text, 'lxml')
        send_user_message(bs, data, is_profitable=False)


def send_user_message(bs, data, is_profitable):
    image_name = get_component_image(bs)
    text = get_components_info_text(bs, data[0], is_profitable)
    with open('users.txt', 'r+') as users:
        with open(image_name, 'rb') as image:
            for user in users:
                bot.send_photo(user,
                               image,
                               text,
                               parse_mode='html')


def get_components_info_text(bs, link, is_profitable):
    name = bs.find("h1", class_="catalog-masthead__title").get_text().strip()
    low_price = bs.find('span', itemprop="lowPrice")

    if low_price is None:
        low_price = "Нет в наличии"
    else:
        low_price = low_price.get_text()

    if is_profitable:
        return f'<b>Скорее беги заказывать!</b>\n\n' \
               f'{name}\n\n' \
               f'🔥<b>{low_price} р.</b>🔥\n\n' \
               f'{link}'
    else:
        return f'{name}\n\n' \
               f'<b>{low_price} р.</b>'


def get_component_image(bs):
    img_src = bs.findAll('img', class_='product-gallery__thumb-img')[0]['src']
    r = requests.get(img_src, allow_redirects=True)

    a = urlparse(img_src)
    filename = os.path.basename(a.path)
    open(filename, 'wb').write(r.content)
    return filename


def start_checking():
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == '__main__':
    schedule.every().hour.do(monitor_price)
    schedule.every().day.at('08:00').do(show_prices)
    thread = threading.Thread(target=start_checking, name="price_checking_thread")
    thread.start()
    app.run(host="0.0.0.0", port=os.environ.get('PORT', 5000))
