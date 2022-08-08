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

from bot_helpers import download_photo, get_main_menu_markup, show_cart
from moltin_handlers import (generate_moltin_token,
                             get_product_data,
                             add_product_to_cart,
                             delete_product_from_cart,
                             create_customer,
                             find_product_price)


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
                                 text='Пришлите, пожалуйста, ваш email')
        return State.WAITING_EMAIL

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


def finish(update: Update, context: CallbackContext):
    update.message.reply_text('Будем рады видеть вас снова 😊')
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
            ]
        },
        fallbacks=[CommandHandler('finish', finish)]
    )
    dispatcher.bot_data['moltin_client_id'] = moltin_client_id
    dispatcher.bot_data['moltin_secret_key'] = moltin_secret_key

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
