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

    print(
        f"dns_records validation OK: {len(result['cnames'])} labels across "
        f"{len(result['a_records'])} hosts, no duplicates."
    )


if __name__ == "__main__":
    main()
