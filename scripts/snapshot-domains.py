#!/usr/bin/env python3
"""Capture DNS resolution and TLS certificate state for a list of service names.

Reads a JSON array of names, resolves each one's CNAME chain and final IP(s)
with `dig`, then probes HTTPS status and the served certificate's subject,
issuer, and expiry with `curl` and `openssl`. Output is sorted-key JSON with
no volatile fields, so two runs against unchanged infrastructure diff cleanly.

Intended to run from two vantages: a LAN host and a remote host (public01),
so the same service names can be compared before and after a DNS/TLS change.
"""

import argparse
import json
import subprocess
import sys

TIMEOUT = 8


def resolve(name: str) -> dict:
    try:
        result = subprocess.run(
            ["dig", "+noall", "+answer", name],
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return {"cname_chain": [], "resolved_ips": [], "error": "dig timed out"}

    chain = []
    ips = []
    for line in result.stdout.splitlines():
        fields = line.split()
        if len(fields) < 5:
            continue
        record_type, data = fields[3], fields[4]
        if record_type == "CNAME":
            chain.append(data.rstrip("."))
        elif record_type == "A":
            ips.append(data)

    return {"cname_chain": chain, "resolved_ips": sorted(ips)}


def http_status(name: str, ip: str) -> str:
    try:
        result = subprocess.run(
            [
                "curl", "-s", "-k",
                "-o", "/dev/null",
                "-w", "%{http_code}",
                "--resolve", f"{name}:443:{ip}",
                "--max-time", str(TIMEOUT),
                f"https://{name}/",
            ],
            capture_output=True,
            text=True,
            timeout=TIMEOUT + 2,
        )
    except subprocess.TimeoutExpired:
        return "error: curl timed out"

    return result.stdout.strip() or f"error: {result.stderr.strip() or 'no response'}"


def cert_info(name: str, ip: str) -> dict:
    s_client = subprocess.Popen(
        ["openssl", "s_client", "-connect", f"{ip}:443", "-servername", name],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    try:
        x509 = subprocess.run(
            ["openssl", "x509", "-noout", "-subject", "-issuer", "-enddate"],
            stdin=s_client.stdout,
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
        )
        s_client.stdout.close()
        s_client.wait(timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        return {"cert_subject": None, "cert_issuer": None, "cert_expiry": None, "error": "openssl timed out"}
    finally:
        if s_client.poll() is None:
            s_client.kill()
            s_client.wait()

    subject = issuer = expiry = None
    for line in x509.stdout.splitlines():
        if line.startswith("subject="):
            subject = line.removeprefix("subject=").strip()
        elif line.startswith("issuer="):
            issuer = line.removeprefix("issuer=").strip()
        elif line.startswith("notAfter="):
            expiry = line.removeprefix("notAfter=").strip()

    return {"cert_subject": subject, "cert_issuer": issuer, "cert_expiry": expiry}


def snapshot_name(name: str) -> dict:
    entry = resolve(name)
    ip = entry["resolved_ips"][0] if entry["resolved_ips"] else None

    if not ip:
        entry["https_status"] = "no A record"
        entry.update({"cert_subject": None, "cert_issuer": None, "cert_expiry": None})
        return entry

    entry["https_status"] = http_status(name, ip)
    entry.update(cert_info(name, ip))
    return entry


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("names_file", help="JSON file containing an array of service names")
    parser.add_argument("--vantage", required=True, choices=["lan", "remote"], help="Where this snapshot was captured from")
    parser.add_argument("-o", "--output", help="Output path (default: stdout)")
    args = parser.parse_args()

    with open(args.names_file) as f:
        names = json.load(f)

    snapshot = {
        "vantage": args.vantage,
        "services": {name: snapshot_name(name) for name in sorted(set(names))},
    }

    output = json.dumps(snapshot, indent=2, sort_keys=True) + "\n"
    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
    else:
        sys.stdout.write(output)


if __name__ == "__main__":
    main()
