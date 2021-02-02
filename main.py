import os
import threading
import time
from urllib.parse import urlparse
import bs4
import requests
import schedule
import telebot
from flask import Flask, request

secret = 'ef54dfcbd52e49988755a23a04d47ac9'
url = 'https://pc-price-checker.herokuapp.com/' + secret
TOKEN = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)
bot.remove_webhook()
bot.set_webhook(url=url)

MY_CHAT_ID = os.environ.get('MY_CHAT_ID')
MAX_PRICE = os.environ.get('MAX_PRICE')

components = ['https://catalog.onliner.by/videocard/palit/ne63070s19p21041',
              'https://catalog.onliner.by/videocard/gigabyte/gvn3070aorusm8gd',
              'https://catalog.onliner.by/videocard/gigabyte/gvn3070visionoc8',
              'https://catalog.onliner.by/videocard/msi/rtx3070gamingxtr',
              'https://catalog.onliner.by/videocard/gigabyte/gvn3070gamingoc8']

app = Flask(__name__)


@app.route('/' + secret, methods=['POST'])
def webhook():
    update = telebot.types.Update.de_json(request.stream.read().decode('utf-8'))
    bot.process_new_updates([update])
    return 'ok', 200


@bot.message_handler(commands=['start', 'help'])
def on_start(message: telebot.types.Message):
    if str(message.chat.id) == str(MY_CHAT_ID):
        bot.send_message(MY_CHAT_ID, "Привет, хозяин)\n"
                                     "Цены чекаются каждый час")


def monitor_price():
    for link in components:
        bs = bs4.BeautifulSoup(requests.get(link).text, 'lxml')
        low_price = bs.find('span', itemprop="lowPrice")
        # Ищем минимальную цену
        if low_price is not None:
            low_price = low_price.get_text()
            # Сделать рассылку если цена приемлимая
            if float(low_price) <= float(MAX_PRICE):
                send_user_message(bs, link, is_profitable=True)


def show_prices():
    for link in components:
        bs = bs4.BeautifulSoup(requests.get(link).text, 'lxml')
        send_user_message(bs, link, is_profitable=False)


def send_user_message(bs, link, is_profitable):
    image_name = get_component_image(bs)
    text = get_components_info_text(bs, link, is_profitable)
    with open(image_name, 'rb') as image:
        bot.send_photo(MY_CHAT_ID,
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
    schedule.every().day.at('07:00').do(show_prices)
    thread = threading.Thread(target=start_checking, name="price_checking_thread")
    thread.start()
    app.run(host="0.0.0.0", port=os.environ.get('PORT', 5000))
