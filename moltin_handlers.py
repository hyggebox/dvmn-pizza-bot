import requests


def generate_moltin_token(client_id, secret_key):
    endpoint = 'https://api.moltin.com/oauth/access_token'
    data = {
        'client_id': client_id,
        'client_secret': secret_key,
        'grant_type': 'client_credentials',
    }
    response = requests.post(endpoint, data=data)
    response.raise_for_status()
    return response.json()['access_token'], response.json()['expires_in']


def get_all_products(token):
    endpoint = 'https://api.moltin.com/pcm/products'
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'EP-Channel': 'web store'
    }
    response = requests.get(endpoint, headers=headers)
    response.raise_for_status()
    return response.json()['data']


def get_product_data(token, user_query):
    endpoint = 'https://api.moltin.com/pcm/products/{}'
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
    }
    response = requests.get(endpoint.format(user_query.data), headers=headers)
    response.raise_for_status()
    return response.json()['data']


def add_product_to_cart(token, cart_id, product_id):
    endpoint = f'https://api.moltin.com/v2/carts/{cart_id}/items'
    headers = {'Authorization': f'Bearer {token}'}
    data = {
      'data': {
          'id': product_id,
          'type': 'cart_item',
          'quantity': 1
        }
      }
    response = requests.post(endpoint, headers=headers, json=data)
    response.raise_for_status()
    return response.json()


def delete_product_from_cart(token, cart_id, product_id):
    endpoint = f'https://api.moltin.com/v2/carts/{cart_id}/items/{product_id}'
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.delete(endpoint, headers=headers)
    response.raise_for_status()


def get_cart_items(token, cart_id):
    endpoint = f'https://api.moltin.com/v2/carts/{cart_id}/items'
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
    }
    response = requests.get(endpoint, headers=headers)
    response.raise_for_status()
    return response.json()


def create_customer(token, customer_id, name, email):
    endpoint = 'https://api.moltin.com/v2/customers'
    headers = {'Authorization': f'Bearer {token}'}
    data = {
        'data': {
            'type': 'customer',
            'name': f'{customer_id} -- {name}',
            'email': email,
            'password': str(customer_id)
        }
    }
    response = requests.post(endpoint, headers=headers, json=data)
    response.raise_for_status()


def get_prices(token):
    price_book_id = "902947fd-5c0e-4a86-83b1-d347be42426a"
    endpoint = f"https://api.moltin.com/pcm/pricebooks/{price_book_id}/prices"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "page[limit]": 50,
    }
    response = requests.get(endpoint, headers=headers, params=params)
    response.raise_for_status()
    return response.json()["data"]


def find_product_price(token, product_sku):
    prices = get_prices(token)
    for price in prices:
        if price["attributes"]["sku"] != product_sku:
            continue
        return price["attributes"]["currencies"]["RUB"]["amount"]
