#!/usr/bin/env python3
"""Validate that every composition states a ZFS policy.

The compositions parent dataset is `low`, so a composition nobody decided
about is snapshotted briefly and never replicated. ADR-0001 makes that a hard
error rather than a silent default.

Reads inventory/host_vars directly and calls the zfs_datasets filter's pure
logic. Deliberately needs neither Ansible nor the vault password, so it runs
anywhere — pre-commit, CI, a fresh checkout. Vaulted values are opaque here;
none of them affect a composition's policy.
"""

import argparse
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "plugins" / "filters"))

from zfs_datasets import compositions_missing_policy  # noqa: E402

# Matches the composition-common role default.
DEFAULT_COMPOSITIONS_DATASET = "fastpool/compositions"


class InventoryLoader(yaml.SafeLoader):
    """SafeLoader that tolerates Ansible's tags, notably !vault."""


InventoryLoader.add_multi_constructor("!", lambda loader, suffix, node: None)


def load_host_vars(host_dir):
    """Merge a host's var files into one mapping of top-level keys."""
    merged = {}
    for path in sorted(host_dir.glob("*.yaml")):
        try:
            data = yaml.load(path.read_text(), Loader=InventoryLoader)
        except yaml.YAMLError as exc:
            raise SystemExit(f"could not parse {path}: {exc}")
        if isinstance(data, dict):
            merged.update(data)
    return merged


def load_dataset_names(roles_root):
    """Map composition name to dataset name, for roles that rename their dataset.

    composition-1password-connect sets composition_name: onepassword-connect,
    so its dataset is fastpool/compositions/onepassword-connect. A policy
    stated under 1password-connect would protect nothing.
    """
    overrides = {}
    for role_dir in sorted(roles_root.glob("composition-*")):
        defaults = role_dir / "defaults" / "main.yaml"
        if not defaults.is_file():
            continue
        data = yaml.load(defaults.read_text(), Loader=InventoryLoader)
        if not isinstance(data, dict):
            continue
        name = data.get("composition_name")
        entry = role_dir.name[len("composition-"):]
        if name and name != entry:
            overrides[entry] = name
    return overrides


def find_missing(host_vars_root, dataset_names):
    """Return {host: [composition, ...]} for compositions with no stated policy."""
    missing_by_host = {}
    checked = 0

    for host_dir in sorted(p for p in host_vars_root.iterdir() if p.is_dir()):
        host_vars = load_host_vars(host_dir)
        compositions = host_vars.get("compositions")
        if not compositions:
            continue

        checked += len(compositions)
        missing = compositions_missing_policy(
            compositions,
            host_vars.get("zfs") or {},
            host_vars.get("compositions_dataset") or DEFAULT_COMPOSITIONS_DATASET,
            dataset_names,
        )
        if missing:
            missing_by_host[host_dir.name] = missing

    return missing_by_host, checked


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--report",
        action="store_true",
        help="List what is missing and exit 0, instead of failing",
    )
    args = parser.parse_args()

    dataset_names = load_dataset_names(REPO_ROOT / "roles")
    missing_by_host, checked = find_missing(
        REPO_ROOT / "inventory" / "host_vars", dataset_names
    )

    if not missing_by_host:
        print(f"composition policies OK: {checked} compositions, all state a policy")
        return

    total = sum(len(names) for names in missing_by_host.values())
    stream = sys.stdout if args.report else sys.stderr
    verb = "have no stated policy" if args.report else "FAILED: no stated policy for"
    print(f"composition policies {verb} {total} of {checked}:", file=stream)
    for host, names in sorted(missing_by_host.items()):
        print(f"  {host}", file=stream)
        for name in names:
            print(f"    {name}", file=stream)

    if not args.report:
        print(
            "\nEvery composition must state its own policy "
            "(none/low/high/critical), next to the service in the host's zfs: "
            "config. See docs/adr/0001-policy-is-the-single-backup-flag.md",
            file=stream,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
