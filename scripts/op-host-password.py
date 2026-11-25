#!/usr/bin/env python3
"""Store a host's account password on its `Host - <Name>` item in the 1Password
Infra vault, via Connect. Creates the item if missing, else updates its
`password` field. Never prints the value.

Env: OP_CONNECT_HOST, OP_CONNECT_TOKEN_WRITE, OP_CONNECT_VAULT (id),
     HOST_PASSWORD (the value). `--inspect` lists host items' shape instead
     (titles, categories, tags, field labels; no values).

    scripts/op-host-password.py "Host - Backups"
"""

import json
import os
import sys
import urllib.error
import urllib.request

TAGS = ["host", "ansible"]


def build_item(title, password):
    """A new Server item holding only the password."""
    return {
        "title": title,
        "category": "SERVER",
        "tags": list(TAGS),
        "fields": [
            {"id": "password", "type": "CONCEALED", "label": "password", "value": password}
        ],
    }


def set_password(item, password):
    """Return item with its password field set (added if absent) and the tags ensured."""
    for field in item.get("fields", []):
        if field.get("id") == "password" or field.get("label") == "password":
            field["value"] = password
            break
    else:
        item.setdefault("fields", []).append(
            {"id": "password", "type": "CONCEALED", "label": "password", "value": password}
        )
    item["tags"] = sorted(set(item.get("tags") or []) | set(TAGS))
    return item


class Connect:
    def __init__(self, host, token, vault):
        self.base = f"{host.rstrip('/')}/v1/vaults/{vault}/items"
        self.token = token

    def call(self, method, path="", body=None, query=""):
        req = urllib.request.Request(
            self.base + path + query,
            data=None if body is None else json.dumps(body).encode(),
            headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"},
            method=method,
        )
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())


def store(client, title, password):
    found = client.call("GET", query=f'?filter=title eq "{title}"'.replace(" ", "%20"))
    if len(found) > 1:
        raise SystemExit(f"error: {len(found)} items titled {title!r}")
    if not found:
        item = client.call("POST", body=build_item(title, password))
        return "created", item["id"]
    full = client.call("GET", f"/{found[0]['id']}")
    client.call("PUT", f"/{found[0]['id']}", body=set_password(full, password))
    return "updated", found[0]["id"]


def main():
    try:
        client = Connect(os.environ["OP_CONNECT_HOST"], os.environ["OP_CONNECT_TOKEN_WRITE"], os.environ["OP_CONNECT_VAULT"])
        if sys.argv[1:] == ["--inspect"]:
            for summary in client.call("GET"):
                if summary["title"].startswith(("Host - ", "Server - ")):
                    full = client.call("GET", f"/{summary['id']}")
                    labels = [f.get("label") for f in full.get("fields", []) if f.get("value")]
                    print(summary["title"], full["category"], full.get("tags"), labels)
            return
        title = sys.argv[1]
        action, item_id = store(client, title, os.environ["HOST_PASSWORD"])
        print(f"{action} {title!r} ({item_id})")
    except (KeyError, IndexError) as err:
        raise SystemExit(f"error: missing input {err}")
    except urllib.error.HTTPError as err:
        raise SystemExit(f"error: Connect returned {err.code}")


if __name__ == "__main__":
    main()
