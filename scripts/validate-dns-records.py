#!/usr/bin/env python3
"""Validate the dns_records filter's derived DNS record set for duplicate labels.

Reads the JSON exported by playbooks/utility/export-dns-records-input.yaml
and calls the dns_records filter's pure logic directly — no Ansible needed
at this stage, so this runs standalone in pre-commit or CI.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "plugins" / "filters"))

from dns_records import DuplicateLabelError, derive_dns_records  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "input_file",
        nargs="?",
        default=str(Path(__file__).parent / "dns-records-input.json"),
        help="JSON file from export-dns-records-input.yaml (default: scripts/dns-records-input.json)",
    )
    args = parser.parse_args()

    data = json.loads(Path(args.input_file).read_text())

    try:
        result = derive_dns_records(data["hosts"], data["compositions"])
    except DuplicateLabelError as exc:
        print(f"dns_records validation FAILED: {exc}", file=sys.stderr)
        sys.exit(1)

    # cnames_additional (names with no owning composition) isn't part of the
    # filter's own contract, but the same duplicate-CNAME rule still applies —
    # BIND doesn't care which mechanism produced a colliding label.
    domain_suffix = "." + data["domainname_infra"]
    derived_qualified = {label + domain_suffix for label in result["cnames"]}
    cnames_additional = data.get("cnames_additional", [])
    duplicates = derived_qualified & set(cnames_additional)
    if duplicates:
        print(
            f"dns_records validation FAILED: cnames_additional collides with a "
            f"composition-derived label: {', '.join(sorted(duplicates))}",
            file=sys.stderr,
        )
        sys.exit(1)
    if len(cnames_additional) != len(set(cnames_additional)):
        seen = set()
        repeated = sorted({n for n in cnames_additional if n in seen or seen.add(n)})
        print(
            f"dns_records validation FAILED: cnames_additional declared twice: {', '.join(repeated)}",
            file=sys.stderr,
        )
        sys.exit(1)

    print(
        f"dns_records validation OK: {len(result['cnames'])} composition-derived labels + "
        f"{len(cnames_additional)} cnames_additional across {len(result['a_records'])} hosts, "
        f"no duplicates."
    )


if __name__ == "__main__":
    main()
