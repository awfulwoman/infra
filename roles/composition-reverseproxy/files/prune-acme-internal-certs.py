#!/usr/bin/env python3
"""Remove internal-domain certificates from a Traefik ACME store (#276).

On a host that serves the internal wildcard as its default certificate, no
router asks ACME for an internal name any more. Certificates issued for those
names before the flip still linger in acme.json, and Traefik does not care that
nothing references them:

  - its renewal loop walks the whole store, so they keep getting renewed -
    exactly the DNS-01 challenge race #262 exists to remove; and
  - an exact-name match beats a wildcard during SNI selection, so the stale
    cert is served in preference to the wildcard it was supposed to replace.

Both stop once the entries are gone. Nothing re-creates them: the certresolver
labels for internal names are guarded on reverseproxy_wildcard_cert.

Usage:
    prune-acme-internal-certs.py <store.json> <internal-suffix> [--apply]

Without --apply, reports what it would remove and changes nothing. Prints
"REMOVED=<n>" either way, so the caller can drive changed_when off it.
"""

import json
import os
import stat
import sys
import tempfile


def is_internal(cert: dict, suffix: str) -> bool:
    """True if every name on the cert sits under the internal suffix.

    Deliberately conservative: a cert mixing internal and public names would be
    doing double duty for something public, so it is left alone and reported.
    """
    domain = cert.get("domain") or {}
    names = [domain.get("main")] + list(domain.get("sans") or [])
    names = [n for n in names if n]
    if not names:
        return False
    return all(n == suffix or n.endswith("." + suffix) for n in names)


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    apply_changes = "--apply" in sys.argv[1:]

    if len(args) != 2:
        print(__doc__, file=sys.stderr)
        return 2

    store_path, suffix = args

    if not os.path.exists(store_path) or os.path.getsize(store_path) == 0:
        print("REMOVED=0")
        print(f"store {store_path} is absent or empty; nothing to do")
        return 0

    with open(store_path) as handle:
        store = json.load(handle)

    removed = []
    mixed = []

    for resolver, section in store.items():
        certs = section.get("Certificates")
        if not certs:
            continue

        keep = []
        for cert in certs:
            domain = cert.get("domain") or {}
            names = [domain.get("main")] + list(domain.get("sans") or [])
            names = [n for n in names if n]

            if is_internal(cert, suffix):
                removed.append(f"{resolver}: {', '.join(names)}")
                continue

            if any(n == suffix or n.endswith("." + suffix) for n in names):
                mixed.append(f"{resolver}: {', '.join(names)}")

            keep.append(cert)

        section["Certificates"] = keep

    print(f"REMOVED={len(removed)}")
    for line in removed:
        print(f"  - {line}")
    for line in mixed:
        print(f"  ! kept (mixes internal and public names): {line}")

    if not removed or not apply_changes:
        return 0

    # Atomic replace inside the same directory, preserving the original's
    # ownership and mode - the file holds private keys.
    original = os.stat(store_path)
    directory = os.path.dirname(store_path) or "."
    handle, temp_path = tempfile.mkstemp(dir=directory)
    try:
        with os.fdopen(handle, "w") as out:
            json.dump(store, out, indent=2)
        os.chmod(temp_path, stat.S_IMODE(original.st_mode))
        try:
            os.chown(temp_path, original.st_uid, original.st_gid)
        except PermissionError:
            pass
        os.replace(temp_path, store_path)
    except Exception:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise

    return 0


if __name__ == "__main__":
    sys.exit(main())
