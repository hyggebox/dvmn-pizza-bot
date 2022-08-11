import logging
import os
import pathlib
from enum import Enum, auto
from time import sleep

from environs import Env
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import (CallbackContext,
                          CallbackQueryHandler,
                          CommandHandler,
                          ConversationHandler,
                          Filters,
                          MessageHandler,
                          Updater)

from bot_helpers import download_photo, get_main_menu_markup, show_cart, fetch_coordinates, get_distance, get_nearest_pizzeria
from moltin_handlers import (generate_moltin_token,
                             get_product_data,
                             add_product_to_cart,
                             delete_product_from_cart,
                             create_customer,
                             find_product_price)
from upload_data_to_ep import create_entry


logger = logging.getLogger('TGBotLogger')


class TelegramLogsHandler(logging.Handler):

    def __init__(self, tg_bot, chat_id):
        super().__init__()
        self.chat_id = chat_id
        self.tg_bot = tg_bot

    def emit(self, record):
        log_entry = self.format(record)
        self.tg_bot.send_message(chat_id=self.chat_id, text=log_entry)


class State(Enum):
    SHOW_MENU = auto()
    HANDLE_MENU = auto()
    HANDLE_DESCRIPTION = auto()
    HANDLE_CART = auto()
    WAITING_EMAIL = auto()
    WAITING_LOCATION = auto()
    HANDLE_DELIVERY_METHOD = auto()

def start(update: Update, context: CallbackContext):
    user = update.effective_user
    update.message.reply_markdown_v2(
        text=f'Привет, {user.mention_markdown_v2()}\! Хотите заказать пиццу?',
        reply_markup=get_main_menu_markup(context.bot_data['moltin_token'])
    )
    return State.HANDLE_MENU


def show_menu(update: Update, context: CallbackContext):
    user_query = update.callback_query
    context.bot.delete_message(chat_id=user_query.message.chat_id,
                               message_id=user_query.message.message_id)
    context.bot.send_message(
        chat_id=user_query.message.chat_id,
        text='Пожалуйста, выберите товар:',
        reply_markup=get_main_menu_markup(context.bot_data['moltin_token'])
    )
    return State.HANDLE_MENU


def handle_menu(update: Update, context: CallbackContext):
    user_query = update.callback_query
    moltin_token = context.bot_data['moltin_token']

    if user_query['data'] == 'cart':
        show_cart(update, context, moltin_token)
        return State.HANDLE_CART

    context.user_data['product_id'] = user_query.data
    context.bot.delete_message(chat_id=user_query.message.chat_id,
                               message_id=user_query.message.message_id)

    product_data = get_product_data(moltin_token, user_query)
    product_img_id = product_data['relationships']['main_image']['data']['id']
    download_photo(moltin_token, product_img_id)

    for filename in os.listdir('images'):
        if product_img_id != os.path.splitext(filename)[0]:
            continue
        with open(f'images/{filename}', 'rb') as image:
            reply_markup = InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton('Добавить в корзину', callback_data=user_query.data)],
                    [InlineKeyboardButton('🛒 КОРЗИНА', callback_data='cart')],
                    [InlineKeyboardButton('Назад', callback_data='back')]
                ]
            )

            product_attrs = product_data['attributes']
            product_price = find_product_price(moltin_token, product_attrs["sku"])
            caption_text = f'«{product_attrs["name"]}»\n\n' \
                   f'Цена: {product_price} руб.\n\n' \
                   f'{product_attrs["description"]}'[:1024]

            context.bot.send_photo(chat_id=user_query.message.chat_id,
                                   photo=image,
                                   caption=caption_text,
                                   reply_markup=reply_markup)
            return State.HANDLE_DESCRIPTION


def handle_description(update: Update, context: CallbackContext):
    user_query = update.callback_query
    moltin_token = context.bot_data['moltin_token']

    if user_query['data'] == 'back':
        return State.SHOW_MENU
    if user_query['data'] == 'cart':
        show_cart(update, context, moltin_token)
        return State.HANDLE_CART

    cart_response = add_product_to_cart(token=moltin_token,
                                        cart_id=update.effective_user.id,
                                        product_id=user_query['data'])
    if 'errors' in cart_response:
        update.callback_query.answer(
            text='Произошла ошибка. Попробуйте снова'
        )
        return State.HANDLE_DESCRIPTION
    update.callback_query.answer(
        text=f'Пицца добавлена в корзину',
        show_alert=True
    )


def handle_cart(update: Update, context: CallbackContext):
    user_query = update.callback_query
    moltin_token = context.bot_data['moltin_token']

    if user_query['data'] == 'get_menu':
        return State.SHOW_MENU

    elif user_query['data'] == 'check_out':
        context.bot.send_message(chat_id=user_query.message.chat_id,
                                 text='Укажите адрес или координаты')
        return State.WAITING_LOCATION
        # return State.WAITING_EMAIL

    delete_product_from_cart(token=moltin_token,
                             cart_id=update.effective_user.id,
                             product_id=user_query['data'])
    show_cart(update, context, moltin_token)
    return State.HANDLE_CART


def handle_user_details(update: Update, context: CallbackContext):
    users_email = update.message.text
    update.message.reply_text(
        f'Благодарим за заказ! Мы свяжемся с вами по email {users_email}'
    )
    create_customer(token=context.bot_data['moltin_token'],
                    customer_id=update.effective_user.id,
                    name=update.effective_user.first_name,
                    email=users_email)


def handle_location(update: Update, context: CallbackContext):
    moltin_token = context.bot_data['moltin_token']
    if update.edited_message:
        if update.edited_message.location:
            users_location = update.edited_message.location
            current_pos = (users_location.latitude,
                           users_location.longitude)
        else:
            current_pos = None
    elif update.message:
        if update.message.location:
            users_location = update.message.location
            current_pos = (users_location.latitude,
                           users_location.longitude)
        elif update.message.text:
            users_address = update.message.text
            current_pos = fetch_coordinates(
                context.bot_data['yandex_api_key'],
                users_address)
        else:
            current_pos = None

    if not current_pos:
        update.message.reply_text(
            "К сожалению, не могу найти координаты. "
            "Уточните месторасположение"
        )
    else:
        reply_markup = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("Доставка", callback_data="delivery")],
                [InlineKeyboardButton("Самовывоз", callback_data="self_pickup")],
                [InlineKeyboardButton("🛒 КОРЗИНА", callback_data="cart")]
            ]
        )

        nearest_pizzeria = get_nearest_pizzeria(moltin_token, current_pos)
        distance_to_nearest_pizzeria = nearest_pizzeria['distance_to_user']
        context.user_data['nearest_pizzeria'] = nearest_pizzeria
        context.user_data['customer_coors'] = current_pos
        if distance_to_nearest_pizzeria <= 0.5:
            update.message.reply_text(text=f"Может, заберёте пиццу из нашей пиццерии "
                                      f"неподалёку? Она всего в "
                                      f"{int(distance_to_nearest_pizzeria * 100)} м от вас! "
                                      f"Вот её адрес: {nearest_pizzeria['address']}.\n\n"
                                      f"А можем и бесплатно доставить, нас не сложно с:",
                                      reply_markup=reply_markup)
        elif distance_to_nearest_pizzeria <= 5:
            update.message.reply_text(text=f"Адрес ближайшей пиццерии: {nearest_pizzeria['address']}.\n\n"
                                      f"Похоже, придётся ехать до вас на самокате."
                                      f"Доставка будет стоить 100 руб. Доставка"
                                      f"или самовывоз?",
                                      reply_markup=reply_markup)
        elif distance_to_nearest_pizzeria <= 20:
            update.message.reply_text(text=f"Доставка пиццы до вас будет стоить 300 руб. "
                                      f"Оформляем заказ?",
                                      reply_markup=reply_markup)
        else:
            update.message.reply_text(f"Простите, но так далеко мы пиццу не доставим."
                                      f"Ближайшая пиццерия аж в {round(distance_to_nearest_pizzeria)} "
                                      f"км от вас!")
        return State.HANDLE_DELIVERY_METHOD


def handle_delivery_method(update: Update, context: CallbackContext):
    user_query = update.callback_query
    moltin_token = context.bot_data['moltin_token']
    nearest_pizzeria = context.user_data['nearest_pizzeria']

    if user_query['data'] == 'delivery':
        context.bot.send_message(chat_id=user_query.message.chat_id,
                                 text="Мы уже везём вам пиццу!")

        users_lat = context.user_data['customer_coors'][0]
        users_lon = context.user_data['customer_coors'][1]
        create_entry(
            moltin_token,
            "customer-address",
            [("customer-id", user_query.message.chat_id),
             ("lat", users_lat),
             ("lon", users_lon)]
        )
        carrier_id = int(nearest_pizzeria["carrier_id"])
        context.bot.send_location(chat_id=carrier_id,
                                  latitude=users_lat,
                                  longitude=users_lon)

    if user_query['data'] == 'self_pickup':
        context.bot.send_message(chat_id=user_query.message.chat_id,
                                 text=f"Заберите свою пиццу по адресу: "
                                  f"{nearest_pizzeria['address']}")
        return ConversationHandler.END


def finish(update: Update, context: CallbackContext):
    update.message.reply_text("Будем рады видеть вас снова 😊")
    return ConversationHandler.END


def regenerate_token(context: CallbackContext):
    moltin_token, _ = generate_moltin_token(
        context.bot_data['moltin_client_id'],
        context.bot_data['moltin_secret_key']
    )
    context.bot_data['moltin_token'] = moltin_token


def main():
    env = Env()
    env.read_env()

    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO)

    tg_bot_token = env.str('TG_BOT_TOKEN')
    moltin_client_id = env.str('MOLTIN_CLIENT_ID')
    moltin_secret_key = env.str('MOLTIN_SECRET_KEY')
    tg_admin_chat_id = env.str('TG_ADMIN_CHAT_ID')
    yandex_api_key = env.str('YANDEX_API_KEY')

    bot = Bot(token=tg_bot_token)
    logger.setLevel(level=logging.INFO)
    logger.addHandler(TelegramLogsHandler(bot, tg_admin_chat_id))
    logger.info('Бот запущен')

    pathlib.Path('images/').mkdir(exist_ok=True)

    updater = Updater(tg_bot_token)
    dispatcher = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            State.SHOW_MENU: [
                CallbackQueryHandler(show_menu),
            ],
            State.HANDLE_MENU: [
                CommandHandler('start', start),
                CallbackQueryHandler(handle_menu),
            ],
            State.HANDLE_DESCRIPTION: [
                CallbackQueryHandler(handle_description),
            ],
            State.HANDLE_CART: [
                CallbackQueryHandler(handle_cart),
            ],
            State.WAITING_EMAIL: [
                MessageHandler(
                    Filters.regex(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
                    handle_user_details
                )
            ],
            State.WAITING_LOCATION: [
                MessageHandler(Filters.location, handle_location),
                MessageHandler(Filters.text, handle_location)
            ],
            State.HANDLE_DELIVERY_METHOD: [
                CallbackQueryHandler(handle_delivery_method)
            ]
        },
        fallbacks=[CommandHandler('finish', finish)]
    )
    dispatcher.bot_data['moltin_client_id'] = moltin_client_id
    dispatcher.bot_data['moltin_secret_key'] = moltin_secret_key
    dispatcher.bot_data['yandex_api_key'] = yandex_api_key

    moltin_token, exp_period = generate_moltin_token(moltin_client_id, moltin_secret_key)
    dispatcher.bot_data['moltin_token'] = moltin_token
    updater.job_queue.run_repeating(regenerate_token, interval=exp_period)

    dispatcher.add_handler(conv_handler)

    while True:
        try:
            updater.start_polling()
            updater.idle()
        except Exception as err:
            logger.exception(f"⚠ Ошибка бота:\n\n {err}")
            sleep(60)


if __name__ == '__main__':
    main()
