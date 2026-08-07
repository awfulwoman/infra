#!/usr/bin/python
# -*- coding: utf-8 -*-
DOCUMENTATION = r"""
  name: composition_dns_subdomains
  short_description: Discover each composition-* role's declared DNS subdomains
  description:
    - Scans roles/composition-*/defaults/main.yaml for a composition_dns_subdomains
      key, read as plain YAML (no Jinja rendering), and returns a dict mapping
      each composition's name to its declared subdomains list.
    - Runs on the controller only. A role with no composition_dns_subdomains
      key is simply absent from the result, not present with an empty list.
  options:
    _terms:
      description: Ignored — this lookup takes no arguments.
"""

import sys
from pathlib import Path

from ansible.plugins.lookup import LookupBase

# Ansible's plugin loader doesn't put a plugin's own directory on sys.path,
# so a sibling import (the pure, ansible-independent logic this wraps) needs
# it added explicitly.
sys.path.insert(0, str(Path(__file__).parent))

from discover_composition_subdomains import discover_composition_subdomains  # noqa: E402


class LookupModule(LookupBase):
    def run(self, terms, variables=None, **kwargs):
        return [discover_composition_subdomains("roles")]
