# Телеграм-бот для заказа пиццы онлайн

Телеграм-бот пиццерии с помощью которого можно заказать и оплатить пиццу. 
Бот интегрируется с CMS Moltin (ElasticPath). 

_>> Проект не закончен_


## Требования

- Для запуска вам понадобится Python 3.6 или выше.
- Токен телеграм-бота (создайте бота через диалог с ботом 
[@BotFather](https://telegram.me/BotFather) и получите токен)
- Токен платежной системы в Telegram (для получения токена необходимо 
настроить для бота оплачу (Payments) через [@BotFather](https://telegram.me/BotFather))
- Бот работает с CMS [Moltin (ElasticPath)](https://www.elasticpath.com/)
- API-ключ Яндекс-геокодера, полученный в [кабинете разработчика](https://developer.tech.yandex.ru/services/)


## Переменные окружения

<table>
<tr>
<td>Переменная</td>
<td>Тип данных</td>
<td>Значение</td>
</tr>
<tr>
<td>TG_BOT_TOKEN</td>
<td>str</td>
<td>Токен Телеграм-бота</td>
</tr>
<tr>
<td>TG_ADMIN_CHAT_ID</td>
<td>int</td>
<td>ID администратора в Телеграм (этому пользователю будут приходить логи бота)</td>
</tr>
<tr>
<td>TG_BOT_MERCHANT_TOKEN</td>
<td>str</td>
<td>Токен платёжной системы, настроенной для бота</td>
</tr>
<tr>
<td>MOLTIN_STORE_ID</td>
<td>str</td>
<td>ID магазина в Moltin (ElasticPath)</td>
</tr>
<tr>
<td>MOLTIN_CLIENT_ID</td>
<td>str</td>
<td>ID клиента в Moltin (ElasticPath)</td>
</tr>
<tr>
<td>MOLTIN_SECRET_KEY</td>
<td>str</td>
<td>Secret key в Moltin (ElasticPath)</td>
</tr>
<tr>
<td>YANDEX_API_KEY</td>
<td>str</td>
<td>Ключ API Яндекс-геокодера</td>
</tr>
</table>


## Установка

- Загрузите код из репозитория
- Создайте файл `.env` в корневой папке и пропишите переменные окружения 
в формате: `ПЕРЕМЕННАЯ=значение`

- Установите зависимости командой:
```shell
pip install -r requirements.txt
```


### Запуск бота

Запустите бота командой:
```commandline
python bot.py
```

## Пример реализации бота

Демо реализации бота: [@HyggeboxPizzaBot](https://telegram.me/HyggeboxPizzaBot)  

