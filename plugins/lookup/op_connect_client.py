"""Minimal 1Password Connect client. urllib only; no Ansible imports.

Reads one field from one item, by item title. Never returns an empty value:
every failure raises OpConnectError, naming the title and field, never a value.
"""

import json
import re
import urllib.error
import urllib.parse
import urllib.request

_VAULT_ID = re.compile(r"^[a-z0-9]{26}$")


class OpConnectError(Exception):
    pass


def _urllib_get(url, token):
    request = urllib.request.Request(
        url, headers={"Authorization": f"Bearer {token}", "Accept": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.load(response)
    except urllib.error.HTTPError as err:
        raise OpConnectError(f"HTTP {err.code} from Connect ({url.split('?')[0]})") from None
    except (urllib.error.URLError, OSError, ValueError) as err:
        raise OpConnectError(f"Connect unreachable or bad reply: {err}") from None


def _filter(attribute, value):
    expr = f'{attribute} eq "{value}"'
    return "filter=" + urllib.parse.quote(expr, safe="")


class OpConnectClient:
    def __init__(self, host, token, vault, http=_urllib_get):
        if not host or not token or not vault:
            raise OpConnectError("onepassword_connect host, token and vault must all be set")
        self.host = host.rstrip("/")
        self.token = token
        self.vault = vault
        self._http = http
        self._vault_id = None
        self._items = {}

    def _get(self, path):
        return self._http(f"{self.host}{path}", self.token)

    def _resolve_vault(self):
        if self._vault_id is None:
            if _VAULT_ID.match(self.vault):
                self._vault_id = self.vault
            else:
                found = self._get(f"/v1/vaults?{_filter('name', self.vault)}")
                if len(found) != 1:
                    raise OpConnectError(f"vault '{self.vault}': expected 1 match, found {len(found)}")
                self._vault_id = found[0]["id"]
        return self._vault_id

    def _item(self, title):
        if title not in self._items:
            vault = self._resolve_vault()
            matches = self._get(f"/v1/vaults/{vault}/items?{_filter('title', title)}")
            if not matches:
                raise OpConnectError(f"item '{title}' not found in vault")
            if len(matches) > 1:
                raise OpConnectError(f"item '{title}': {len(matches)} items share this title")
            self._items[title] = self._get(f"/v1/vaults/{vault}/items/{matches[0]['id']}")
        return self._items[title]

    def get_field(self, title, field):
        fields = self._item(title).get("fields") or []
        labelled = [f for f in fields if f.get("label")]
        by_label = [f for f in labelled if f["label"] == field]
        if len(by_label) > 1:
            raise OpConnectError(f"item '{title}': duplicate label '{field}'")
        if by_label:
            match = by_label[0]
        else:
            by_id = [f for f in fields if f.get("id") == field]
            if not by_id:
                raise OpConnectError(f"item '{title}': field '{field}' not found")
            match = by_id[0]
        value = match.get("value")
        if value in (None, ""):
            raise OpConnectError(f"item '{title}': field '{field}' is empty")
        return value

    def item_metadata(self):
        """Every item in the vault, without any value: title, category, tags,
        and each field's id and label with a has_value flag. For audits."""
        vault = self._resolve_vault()
        out = []
        for summary in self._get(f"/v1/vaults/{vault}/items"):
            item = self._get(f"/v1/vaults/{vault}/items/{summary['id']}")
            out.append({
                "id": item["id"],
                "title": item.get("title", ""),
                "category": item.get("category", ""),
                "tags": list(item.get("tags") or []),
                "fields": [
                    {"id": f.get("id", ""), "label": f.get("label", ""), "has_value": bool(f.get("value"))}
                    for f in item.get("fields") or []
                ],
            })
        return out
