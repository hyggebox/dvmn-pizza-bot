import requests


def add_img(token, img_url):
    ''' Returns image id '''
    endpoint = "https://api.moltin.com/v2/files"
    headers = {"Authorization": f"Bearer {token}"}
    files = {
        "file_location": (None, img_url),
    }
    response = requests.post(endpoint, headers=headers, files=files)
    response.raise_for_status()
    return response.json()["data"]["id"]


def add_product_price(token, product_sku, price):
    price_book_id = "902947fd-5c0e-4a86-83b1-d347be42426a"
    endpoint = f"https://api.moltin.com/pcm/pricebooks/{price_book_id}/prices"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    body = {
        "data": {
            "type": "product-price",
            "attributes": {
                "sku": product_sku,
                "currencies": {
                    "RUB": {
                        "amount": price,
                        "includes_tax": True,
                    }
                }
            }
        },
    }
    response = requests.post(endpoint, headers=headers, json=body)
    response.raise_for_status()


def add_product_to_cart(token, cart_id, product_id):
    endpoint = f"https://api.moltin.com/v2/carts/{cart_id}/items"
    headers = {"Authorization": f"Bearer {token}"}
    data = {
      "data": {
          "id": product_id,
          "type": "cart_item",
          "quantity": 1
        }
      }
    response = requests.post(endpoint, headers=headers, json=data)
    response.raise_for_status()
    return response.json()


def create_catalog(token):
    endpoint = "https://api.moltin.com/pcm/catalogs"
    headers = {"Authorization": f"Bearer {token}"}
    pizzeria_hierarchy_id = "6141ab1d-fe67-4eff-88d3-d5f1fca6f51c"
    pizzeria_price_book = "902947fd-5c0e-4a86-83b1-d347be42426a"
    body = {
        "data": {
        "type": "catalog",
        "attributes": {
            "name": "Pizzas catalog",
            "hierarchy_ids": [
                pizzeria_hierarchy_id
            ],
            "pricebook_id": pizzeria_price_book,
            "description": "Pizzeria catalog"
            }
        }
    }
    response = requests.post(endpoint, headers=headers, json=body)
    response.raise_for_status()
    return response.json()["data"]["id"]


def create_entry(token, flow_slug, fields):
    endpoint = f"https://api.moltin.com/v2/flows/{flow_slug}/entries"
    headers = {"Authorization": f"Bearer {token}"}

    entry_fields = {"type": "entry"}
    for field, value in fields:
        entry_fields[field] = value

    body = {
        "data": entry_fields
     }
    response = requests.post(endpoint, headers=headers, json=body)
    response.raise_for_status()


def create_flow(token, name, slug, description, is_enabled):
    endpoint = "https://api.moltin.com/v2/flows"
    headers = {"Authorization": f"Bearer {token}"}
    body = {
        "data": {
            "type": "flow",
            "name": name,
            "slug": slug,
            "description": description,
            "enabled": is_enabled
        }
     }
    response = requests.post(endpoint, headers=headers, json=body)
    response.raise_for_status()
    created_flow_id = response.json()["data"]["id"]
    return created_flow_id


def create_flow_field(token, flow_slug, name, slug, field_type, description,
                      is_required, is_enabled):
    if flow_slug == "pizzeria":
        flow_id = "53d653bd-e23a-4505-a7f5-6318555e7878"
    elif flow_slug == "customer-address":
        flow_id = "064439c6-7a30-44d7-8ea0-5b3e50b0b4f5"
    else:
        raise ValueError(f"No flow with slug '{flow_slug}'")

    endpoint = "https://api.moltin.com/v2/fields"
    headers = {"Authorization": f"Bearer {token}"}
    body = {
      "data": {
        "type": "field",
        "name": name,
        "slug": slug,
        "field_type": field_type,
        "description": description,
        "required": is_required,
        "enabled": is_enabled,
        "relationships": {
            "flow": {
                "data": {
                    "type": "flow",
                    "id": flow_id
                }
            }
        }
      }
    }
    response = requests.post(endpoint, headers=headers, json=body)
    response.raise_for_status()
    field_id = response.json()["data"]["id"]
    return field_id


def create_product(token, product_name, sku, slug, description):
    '''Returns product id'''
    endpoint = "https://api.moltin.com/pcm/products"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    body = {
        "data": {
            "type": "product",
            "attributes": {
                "name": product_name,
                "sku": sku,
                "slug": slug,
                "description": description,
                "commodity_type": "physical",
                "status": "live",
            },
        }
    }
    response = requests.post(endpoint, headers=headers, json=body)
    response.raise_for_status()
    return response.json()["data"]["id"]


def delete_product_from_cart(token, cart_id, product_id):
    endpoint = f"https://api.moltin.com/v2/carts/{cart_id}/items/{product_id}"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.delete(endpoint, headers=headers)
    response.raise_for_status()


def find_product_price(token, product_sku):
    prices = get_prices(token)
    for price in prices:
        if price["attributes"]["sku"] != product_sku:
            continue
        return price["attributes"]["currencies"]["RUB"]["amount"]


def generate_moltin_token(client_id, secret_key):
    endpoint = "https://api.moltin.com/oauth/access_token"
    data = {
        "client_id": client_id,
        "client_secret": secret_key,
        "grant_type": "client_credentials",
    }
    response = requests.post(endpoint, data=data)
    response.raise_for_status()
    return response.json()["access_token"], response.json()["expires_in"]


def get_all_products(token):
    endpoint = "https://api.moltin.com/pcm/products"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "EP-Channel": "web store"
    }
    response = requests.get(endpoint, headers=headers)
    response.raise_for_status()
    return response.json()["data"]


def get_cart_items(token, cart_id):
    endpoint = f"https://api.moltin.com/v2/carts/{cart_id}/items"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    response = requests.get(endpoint, headers=headers)
    response.raise_for_status()
    return response.json()


def get_pricebook(token):
    price_book_id = "902947fd-5c0e-4a86-83b1-d347be42426a"
    price_params = {"include": "prices"}
    prices_response = requests.get(
        f"https://api.moltin.com/pcm/pricebooks/{price_book_id}",
        headers={"Authorization": f"Bearer {token}"},
        params=price_params
    )
    prices_response.raise_for_status()
    return prices_response.json()


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


def get_product_data(token, user_query):
    endpoint = "https://api.moltin.com/pcm/products/{}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    response = requests.get(endpoint.format(user_query.data), headers=headers)
    response.raise_for_status()
    return response.json()["data"]


def relate_img_product(token, product_id, img_id):
    endpoint = f"https://api.moltin.com/pcm/products/{product_id}/relationships/main_image"
    headers = {"Authorization": f"Bearer {token}"}
    body = {
        "data": {
            "type": "file",
            "id": img_id,
        }
    }
    response = requests.post(endpoint, headers=headers, json=body)
    response.raise_for_status()
