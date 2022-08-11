import os
import pathlib
from urllib.parse import urlsplit, unquote

from geopy import distance
import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from moltin_handlers import get_cart_items, get_all_products


def get_extension(url):
    split_url = urlsplit(unquote(url))
    file_extension = os.path.splitext(split_url.path)[1]
    return file_extension


def download_photo(token, img_id):
    endpoint = f'https://api.moltin.com/v2/files/{img_id}'
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
    }
    response = requests.get(endpoint, headers=headers)
    response.raise_for_status()

    img_url = response.json()['data']['link']['href']
    ext = get_extension(img_url)
    product_img = pathlib.Path(f'images/{img_id}{ext}')
    if not product_img.exists():
        img_response = requests.get(img_url)
        img_response.raise_for_status()
        with open(product_img, 'wb') as file:
            file.write(img_response.content)


def get_main_menu_markup(token):
    buttons = [[InlineKeyboardButton(product['attributes']['name'],
                                     callback_data=product['id'])]
               for product in get_all_products(token)]
    buttons.append([InlineKeyboardButton('🛒 КОРЗИНА', callback_data='cart')])
    return InlineKeyboardMarkup(buttons)


def show_cart(update, context, headers):
    user_query = update.callback_query
    context.bot.delete_message(chat_id=user_query.message.chat_id,
                               message_id=user_query.message.message_id)
    cart_items = get_cart_items(headers, update.effective_user.id)
    text = ''
    buttons = []
    for item in cart_items['data']:
        text += (f'🍕 {item["name"]}\n'
                 f'{item["meta"]["display_price"]["with_tax"]["unit"]["formatted"]} руб/шт.\n'
                 f'{item["quantity"]} шт. на '
                 f'{item["meta"]["display_price"]["with_tax"]["value"]["formatted"]} руб.\n\n')
        buttons.append(
            [InlineKeyboardButton(f'{item["name"]} ✖️',
                                  callback_data=item['id'])]
        )
    text += f'ИТОГО: {cart_items["meta"]["display_price"]["with_tax"]["formatted"]}'
    buttons.append([InlineKeyboardButton('📄 В МЕНЮ', callback_data='get_menu')])
    buttons.append([InlineKeyboardButton('💳 ОПЛАТА', callback_data='check_out')])
    context.bot.send_message(chat_id=update.effective_user.id,
                             text=text,
                             reply_markup=InlineKeyboardMarkup(buttons))


def fetch_coordinates(apikey, address):
    base_url = "https://geocode-maps.yandex.ru/1.x"
    response = requests.get(base_url, params={
        "geocode": address,
        "apikey": apikey,
        "format": "json",
    })
    response.raise_for_status()
    found_places = response.json()["response"]["GeoObjectCollection"]["featureMember"]

    if not found_places:
        return None

    most_relevant = found_places[0]
    lon, lat = most_relevant["GeoObject"]["Point"]["pos"].split(" ")
    return lat, lon


def get_distance(from_coors, to_coors):
    distance_in_km = distance.distance(from_coors, to_coors).km
    return round(distance_in_km, 2)


def get_pizzerias_details(token):
    flow_slug = "pizzeria"
    endpoint = f"https://api.moltin.com/v2/flows/{flow_slug}/entries"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(endpoint, headers=headers)
    response.raise_for_status()
    return response.json()["data"]


def get_distances(distances):
    return distances["distance_to_user"]


def get_nearest_pizzeria(token, users_coors):
    all_pizzerias = get_pizzerias_details(token)
    distances_to_user = []
    for pizzeria in all_pizzerias:
        pizzeria_coors = (pizzeria["lat"], pizzeria["lon"])
        pizzeria_data = {"address": pizzeria["address"],
                         "carrier_id": pizzeria["carrier-id"],
                         "distance_to_user": get_distance(pizzeria_coors, users_coors)}
        distances_to_user.append(pizzeria_data)
    return min(distances_to_user, key=get_distances)


def send_message_after_delivery_time(context):
    context.bot.send_message(context.job.context,
                             text="Приятного аппетита!\n\n"
                                  "*сообщение что делать если пицца не пришла*")