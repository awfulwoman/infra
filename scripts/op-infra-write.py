#!/usr/bin/env python3
"""Generate a password and store it in the 1Password Infra vault via Connect."""

import argparse
import json
import os
import secrets
import string
import sys
import urllib.request
import urllib.error

CONNECT_HOST = "https://connect.ewwww.eu"
VAULT_ID = "tsnrmqmuafgj2b5ajwykn7jwpi"


def generate_password(length: int = 32) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def store_item(token: str, title: str, password: str, username: str, category: str) -> str:
    fields = [
        {"id": "password", "type": "CONCEALED", "purpose": "PASSWORD", "label": "password", "value": password},
    ]
    if username:
        fields.append({"id": "username", "type": "STRING", "purpose": "USERNAME", "label": "username", "value": username})

    body = json.dumps({"title": title, "category": category, "fields": fields}).encode()
    req = urllib.request.Request(
        f"{CONNECT_HOST}/v1/vaults/{VAULT_ID}/items",
        data=body,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())["id"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("title", help="1Password item title")
    parser.add_argument("--username", default="", help="Username field (optional)")
    parser.add_argument("--category", default="LOGIN", help="Item category (default: LOGIN)")
    parser.add_argument("--length", type=int, default=32, help="Password length (default: 32)")
    args = parser.parse_args()

    token = os.environ.get("OP_CONNECT_TOKEN_WRITE")
    if not token:
        print("Error: OP_CONNECT_TOKEN_WRITE environment variable not set", file=sys.stderr)
        sys.exit(1)

    password = generate_password(args.length)

    try:
        item_id = store_item(token, args.title, password, args.username, args.category)
    except urllib.error.HTTPError as e:
        print(f"Error: Connect API returned {e.code}: {e.read().decode()}", file=sys.stderr)
        sys.exit(1)

    print(password)
    print(f"# stored in 1Password Infra vault as '{args.title}' (id: {item_id})", file=sys.stderr)


if __name__ == "__main__":
    main()
