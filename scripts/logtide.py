#!/usr/bin/env python3
"""Query the Logtide log API from the command line.

Credentials are not stored here. By default the API key and the infra domain
are resolved from Ansible Vault at run time, via a host in the `infra` group
(NOT localhost — `group_vars/infra/` does not apply to it, so the lookup
silently yields an error string instead of the key). Override either value
with LOGTIDE_API_KEY / LOGTIDE_URL to skip the Ansible call entirely.

Server-side filtering is limited to --level and --service; the API accepts
`search`, `startTime` and `endTime` but silently ignores them, so --grep,
--since and --host are applied here after fetching. That means those three
read up to --max-scan records to find their matches.

Examples:
    scripts/logtide.py logs --level error -n 20
    scripts/logtide.py logs --service traefik --since 2h
    scripts/logtide.py logs --grep 'certificate' --level warn
    scripts/logtide.py services
    scripts/logtide.py stats
"""

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

# Any host in the `infra` group will do; this one is the Ansible controller
# itself, so -c local keeps the lookup off the network.
VAULT_HOST = "apple-macmini-m4-16gb-malcolm"

# The API caps a single response; page through with offset rather than asking
# for everything at once.
PAGE_SIZE = 200

LEVEL_COLOURS = {
    "critical": "\033[1;35m",
    "error": "\033[0;31m",
    "warn": "\033[0;33m",
    "info": "\033[0;32m",
    "debug": "\033[0;90m",
}
RESET = "\033[0m"


class LogtideError(Exception):
    """Anything that should stop the run with a readable message."""


def resolve_config():
    """Return (base_url, api_key), preferring the environment over Vault."""
    url = os.environ.get("LOGTIDE_URL")
    key = os.environ.get("LOGTIDE_API_KEY")
    if url and key:
        return url.rstrip("/"), key

    # One ad-hoc call resolves both values. The json callback gives parseable
    # output; the minimal default callback does not.
    env = dict(os.environ, ANSIBLE_STDOUT_CALLBACK="json", ANSIBLE_LOAD_CALLBACK_PLUGINS="1")
    template = "{{ vault_logtide_agent_key }}\t{{ domainname_infra }}"
    proc = subprocess.run(
        ["ansible", VAULT_HOST, "-c", "local", "-m", "debug", "-a", f"msg={template}"],
        capture_output=True,
        text=True,
        env=env,
    )
    if proc.returncode != 0:
        raise LogtideError(f"Ansible lookup failed:\n{proc.stderr.strip()}")
    try:
        report = json.loads(proc.stdout)
        host_result = next(iter(report["plays"][0]["tasks"][0]["hosts"].values()))
        resolved_key, domain = host_result["msg"].split("\t")
    except (ValueError, KeyError, StopIteration) as exc:
        raise LogtideError(f"Could not parse the Ansible lookup output: {exc}")
    if "{{" in resolved_key or not resolved_key:
        raise LogtideError("Vault lookup returned no key — is the vault password file readable?")

    return url.rstrip("/") if url else f"https://logtide.{domain}", key or resolved_key


def api_get(base_url, key, path, params=None):
    """GET a JSON endpoint. Unknown query params make the API 500, so only
    pass ones known to be accepted."""
    query = f"?{urllib.parse.urlencode(params)}" if params else ""
    request = urllib.request.Request(
        f"{base_url}{path}{query}", headers={"X-API-Key": key}
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:300]
        raise LogtideError(f"{exc.code} from {path}: {detail}")
    except urllib.error.URLError as exc:
        raise LogtideError(f"Could not reach {base_url}: {exc.reason}")


def parse_since(value):
    """Turn '90m', '2h', '3d' into a UTC cutoff datetime."""
    match = re.fullmatch(r"(\d+)([smhd])", value.strip())
    if not match:
        raise LogtideError(f"--since must look like 30m, 2h or 3d (got {value!r})")
    amount, unit = int(match.group(1)), match.group(2)
    unit_names = {"s": "seconds", "m": "minutes", "h": "hours", "d": "days"}
    return datetime.now(timezone.utc) - timedelta(**{unit_names[unit]: amount})


def record_time(record):
    """Parse a record's ISO-8601 time, tolerating the trailing Z."""
    try:
        return datetime.fromisoformat(record.get("time", "").replace("Z", "+00:00"))
    except ValueError:
        return None


def fetch_logs(base_url, key, args):
    """Page through /logs, applying the client-side filters as we go, and stop
    at --limit matches or --max-scan records read."""
    server_params = {}
    if args.level:
        server_params["level"] = args.level
    if args.service:
        server_params["service"] = args.service

    pattern = re.compile(args.grep, re.IGNORECASE) if args.grep else None
    cutoff = parse_since(args.since) if args.since else None

    matches = []
    scanned = 0
    offset = 0
    reached_cutoff = False

    while len(matches) < args.limit and scanned < args.max_scan and not reached_cutoff:
        page = api_get(
            base_url,
            key,
            "/api/v1/logs",
            {**server_params, "limit": PAGE_SIZE, "offset": offset},
        )
        records = page.get("logs", [])
        if not records:
            break
        scanned += len(records)
        offset += len(records)

        for record in records:
            when = record_time(record)
            # Records come back newest first, so the first one older than the
            # cutoff means everything after it is older too.
            if cutoff and when and when < cutoff:
                reached_cutoff = True
                break
            if pattern and not pattern.search(record.get("message", "")):
                continue
            if args.host and record.get("metadata", {}).get("hostname") != args.host:
                continue
            matches.append(record)
            if len(matches) >= args.limit:
                break

        if not page.get("hasMore"):
            break

    return matches, scanned


def format_record(record, use_colour):
    when = (record.get("time") or "")[:19].replace("T", " ")
    level = (record.get("level") or "?").lower()
    service = record.get("service") or "-"
    host = record.get("metadata", {}).get("hostname", "-")
    message = (record.get("message") or "").rstrip()
    if use_colour and level in LEVEL_COLOURS:
        level = f"{LEVEL_COLOURS[level]}{level:<8}{RESET}"
    else:
        level = f"{level:<8}"
    return f"{when}  {level}  {service:<22.22}  {host:<22.22}  {message}"


def command_logs(base_url, key, args):
    matches, scanned = fetch_logs(base_url, key, args)
    if args.json:
        json.dump(matches, sys.stdout, indent=2)
        print()
        return
    use_colour = sys.stdout.isatty()
    for record in reversed(matches):  # oldest first, like tail
        print(format_record(record, use_colour))
    if not matches:
        print(f"No matching logs (scanned {scanned} records).", file=sys.stderr)
    elif len(matches) < args.limit and scanned >= args.max_scan:
        print(
            f"\n{len(matches)} match(es) within the first {scanned} records — "
            f"raise --max-scan to look further back.",
            file=sys.stderr,
        )


def command_stats(base_url, key, args):
    stats = api_get(base_url, key, "/api/v1/stats")
    if args.json:
        json.dump(stats, sys.stdout, indent=2)
        print()
        return
    print(f"total  {stats.get('total', 0):,}")
    for level, count in sorted(
        stats.get("by_level", {}).items(), key=lambda item: -item[1]
    ):
        print(f"{level:<9}{count:,}")


def command_services(base_url, key, args):
    """Tally service names over a sample — the API has no endpoint listing them."""
    tally = {}
    scanned = 0
    offset = 0
    while scanned < args.max_scan:
        page = api_get(
            base_url, key, "/api/v1/logs", {"limit": PAGE_SIZE, "offset": offset}
        )
        records = page.get("logs", [])
        if not records:
            break
        for record in records:
            name = record.get("service") or "-"
            tally[name] = tally.get(name, 0) + 1
        scanned += len(records)
        offset += len(records)
        if not page.get("hasMore"):
            break

    if args.json:
        json.dump(tally, sys.stdout, indent=2)
        print()
        return
    print(f"Services seen in the most recent {scanned} records:\n")
    for name, count in sorted(tally.items(), key=lambda item: -item[1]):
        print(f"{count:>7}  {name}")


def build_parser():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command")

    def add_shared(subparser):
        subparser.add_argument("--json", action="store_true", help="emit raw JSON")
        subparser.add_argument(
            "--max-scan",
            type=int,
            default=2000,
            help="most records to read while filtering client-side (default: 2000)",
        )

    logs = subparsers.add_parser("logs", help="list log records (default)")
    logs.add_argument(
        "-l", "--level", choices=["debug", "info", "warn", "error", "critical"]
    )
    logs.add_argument("-s", "--service", help="exact service name, e.g. traefik")
    logs.add_argument("-n", "--limit", type=int, default=50, help="matches to show (default: 50)")
    logs.add_argument("--grep", metavar="REGEX", help="filter on message text (client-side)")
    logs.add_argument("--since", metavar="DURATION", help="30m, 2h, 3d (client-side)")
    logs.add_argument("--host", help="filter on metadata.hostname (client-side)")
    add_shared(logs)

    stats = subparsers.add_parser("stats", help="record counts by level")
    add_shared(stats)

    services = subparsers.add_parser("services", help="service names in recent records")
    add_shared(services)

    return parser


def main():
    parser = build_parser()
    # Bare invocation, or one that starts with a flag, means `logs`.
    argv = sys.argv[1:]
    if not argv or argv[0].startswith("-"):
        argv = ["logs"] + argv
    args = parser.parse_args(argv)

    try:
        base_url, key = resolve_config()
        handler = {
            "logs": command_logs,
            "stats": command_stats,
            "services": command_services,
        }[args.command]
        handler(base_url, key, args)
    except LogtideError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
    except BrokenPipeError:
        sys.exit(0)  # piped into head, etc.


if __name__ == "__main__":
    main()
