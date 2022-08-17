import argparse
import json

import requests
from environs import Env
from slugify import slugify

from moltin_handlers import (add_img,
                             add_product_price,
                             create_entry,
                             create_flow_field,
                             create_product,
                             generate_moltin_token,
                             relate_img_product)


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


def main():
    env = Env()
    env.read_env()
    args = get_args()

    moltin_client_id = env.str("MOLTIN_CLIENT_ID")
    moltin_secret_key = env.str("MOLTIN_SECRET_KEY")

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
        flow_id, field_name, field_slug, field_type, field_description = args.create_field
        create_flow_field(moltin_token,
                          flow_id,
                          field_name,
                          field_slug,
                          field_type,
                          field_description,
                          True, True)


if __name__ == "__main__":
    main()
