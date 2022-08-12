import argparse
import json

import requests
from environs import Env
from slugify import slugify

from moltin_handlers import generate_moltin_token


def get_args():
    parser = argparse.ArgumentParser(
        description="Скрипт загружает данные в систему moltin"
    )
    parser.add_argument("-cf", "--create_field",
                        nargs=5,
                        help="Creates a field in a chosen flow. "
                             "Demands 5 arguments: FLOW_ID, NAME, SLUG, "
                             "FIELD_TYPE, DESCRIPTION")
    parser.add_argument("-lp", "--load_products",
                        action="store_true",
                        help="Load products to Moltin from menu.json file")
    parser.add_argument("-la", "--load_addresses",
                        action="store_true",
                        help="Load pizzerias addresses to Moltin from "
                             "address.json file")
    return parser.parse_args()


def read_json(filename):
    with open(filename, "r", encoding="utf-8") as file:
        file_data = json.loads(file.read())
    return file_data


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


def load_products(token, menu):
    params = {"page[limit]": 100}
    products_response = requests.get(
        "https://api.moltin.com/pcm/products",
        headers={"Authorization": f"Bearer {token}"},
        params=params
    )
    products_response.raise_for_status()
    existing_products = products_response.json()["data"]
    product_skus = [product["attributes"]["sku"] for product in existing_products]

    for product in menu:
        product_name = product["name"]
        product_id = str(product["id"])
        if product_id in product_skus:
            continue
        slug = slugify(f"{product_id} {product_name}", to_lower=True)
        product_description = product["description"]
        product_price = product["price"]
        img_url = product["product_image"]["url"]

        created_product_id = create_product(token, product_name, product_id,
                                            slug, product_description)
        add_product_price(token, product_id, product_price)
        img_id = add_img(token, img_url)
        relate_img_product(token, created_product_id, img_id)


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
    print(response.json())
    response.raise_for_status()


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


def main():
    env = Env()
    env.read_env()

    args = get_args()

    tg_bot_token = env.str("TG_BOT_TOKEN")
    moltin_client_id = env.str("MOLTIN_CLIENT_ID")
    moltin_secret_key = env.str("MOLTIN_SECRET_KEY")
    tg_admin_chat_id = env.str("TG_ADMIN_CHAT_ID")

    addresses = read_json("addresses.json")
    menu = read_json("menu.json")
    moltin_token, exp_period = generate_moltin_token(moltin_client_id,
                                                     moltin_secret_key)

    if args.load_products:
        load_products(moltin_token, menu)

    if args.load_addresses:
        pizzeria_flow_slug = "pizzeria"
        for address in addresses:
            address_details = address["address"]["full"]
            alias = address["alias"]
            lat = address["coordinates"]["lat"]
            lon = address["coordinates"]["lon"]
            carrier_tg_id = 0
            fields = [
                ("address", address_details),
                ("alias", alias),
                ("lat", lat),
                ("lon", lon),
                ("carrier-id", carrier_tg_id)
            ]
            create_entry(moltin_token, pizzeria_flow_slug, fields)

    if args.create_field:
        flow_field_args = args.create_field
        create_flow_field(moltin_token,
                          flow_field_args[0],
                          flow_field_args[1],
                          flow_field_args[2],
                          flow_field_args[3],
                          flow_field_args[4],
                          True, True)


if __name__ == "__main__":
    main()
