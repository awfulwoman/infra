#!/usr/bin/python
# -*- coding: utf-8 -*-
DOCUMENTATION = r"""
  name: onepassword_connect
  short_description: Read one field of a 1Password item through Connect
  description:
    - Finds the item in the Infra vault by exact title and returns one field,
      matched by label then by field id (Login built-ins C(username), C(password)).
    - Raises on any failure. Never returns an empty value; there is no default.
    - Host, token and vault come from the variables C(onepassword_connect_host),
      C(onepassword_connect_token) and C(onepassword_connect_vault_id).
  options:
    _terms:
      description: Two terms, the item title and the field.
      required: true
    vault:
      description: Vault name or ID, instead of C(onepassword_connect_vault_id).
"""

import sys
from pathlib import Path

from ansible.errors import AnsibleLookupError
from ansible.plugins.lookup import LookupBase

sys.path.insert(0, str(Path(__file__).parent))

from op_connect_client import OpConnectClient, OpConnectError  # noqa: E402

# One client per run (per Ansible worker process), so each item is fetched once.
_CLIENTS = {}


class LookupModule(LookupBase):
    def run(self, terms, variables=None, **kwargs):
        if len(terms) != 2:
            raise AnsibleLookupError("onepassword_connect takes exactly two terms: title, field")
        title, field = terms
        variables = variables or {}
        self._templar.available_variables = variables
        host = self._templar.template(variables.get("onepassword_connect_host"))
        token = self._templar.template(variables.get("onepassword_connect_token"))
        vault = kwargs.get("vault") or self._templar.template(variables.get("onepassword_connect_vault_id"))
        try:
            key = (host, vault)
            if key not in _CLIENTS:
                _CLIENTS[key] = OpConnectClient(host, token, vault)
            return [_CLIENTS[key].get_field(title, field)]
        except OpConnectError as err:
            raise AnsibleLookupError(str(err)) from None
