#!/usr/bin/env python3
"""Rotate a host's vault_password in two phases, without printing a secret.

  stage HOST    write a new random value to the host's vault_credentials.yaml
                as `vault_password_next` (encrypted; the live password is kept)
  promote HOST  move `vault_password_next` into `vault_password`

Between the two, run playbooks/utility/rotate-account-password.yaml: it sets
the real account password to vault_password_next while Ansible still uses the
old one. Promote only after that playbook has passed.

The secret exists in this process only, and goes to ansible-vault on stdin.
It is never printed, logged or put on a command line. Promote moves ciphertext
as text and decrypts nothing.
"""

import argparse
import re
import secrets
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LIVE = "vault_password"
NEXT = "vault_password_next"
HOST_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


class RotationError(Exception):
    pass


def vault_file_for(host):
    if not HOST_RE.fullmatch(host):
        raise RotationError(f"not a host name: {host!r}")
    path = REPO / "inventory" / "host_vars" / host / "vault_credentials.yaml"
    if not path.is_file():
        raise RotationError(f"no such file: {path.relative_to(REPO)}")
    return path


def _block_re(name):
    # A top-level `name: !vault |` key and its indented ciphertext lines.
    return re.compile(rf"^{re.escape(name)}: !vault \|\n(?:[ \t]+[^\n]*\n?)+", re.M)


def _find(text, name):
    return _block_re(name).search(text)


def _vault_id(block):
    header = re.search(r"\$ANSIBLE_VAULT;[^;\n]+;[^;\n]+;([^\s;]+)", block)
    return header.group(1) if header else None


def ansible_vault_encrypt(name, value, vault_id):
    """Encrypt `value` as an inline vault string. The value goes in on stdin."""
    cmd = ["ansible-vault", "encrypt_string", "--stdin-name", name]
    if vault_id:
        cmd += ["--encrypt-vault-id", vault_id]
    done = subprocess.run(cmd, input=value, capture_output=True, text=True, check=False)
    if done.returncode != 0:
        # stderr from ansible-vault does not hold the value; stdin is not echoed.
        raise RotationError(f"ansible-vault failed: {done.stderr.strip()[:200]}")
    return done.stdout


def _without(text, name):
    return _block_re(name).sub("", text)


def stage(path, encrypt=ansible_vault_encrypt):
    text = Path(path).read_text()
    live = _find(text, LIVE)
    if not live:
        raise RotationError(f"no live `{LIVE}` block in {path}")
    value = secrets.token_hex(32)
    block = encrypt(NEXT, value, _vault_id(live.group(0)))
    del value
    text = _without(text, NEXT).rstrip("\n") + "\n\n" + block.rstrip("\n") + "\n"
    Path(path).write_text(text)
    return f"staged {NEXT} in {path}"


def promote(path):
    text = Path(path).read_text()
    nxt = _find(text, NEXT)
    if not nxt:
        raise RotationError(f"no `{NEXT}` block in {path}: run stage first")
    if not _find(text, LIVE):
        raise RotationError(f"no live `{LIVE}` block in {path}")
    renamed = nxt.group(0).replace(f"{NEXT}: !vault", f"{LIVE}: !vault", 1)
    text = _without(text, NEXT)
    live = _find(text, LIVE)
    text = text[: live.start()] + renamed + text[live.end():]
    Path(path).write_text(text.rstrip("\n") + "\n")
    return f"promoted {NEXT} to {LIVE} in {path}"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("action", choices=["stage", "promote"])
    parser.add_argument("host", help="inventory host name, e.g. server-8gb-backups")
    args = parser.parse_args(argv)
    try:
        path = vault_file_for(args.host)
        print({"stage": stage, "promote": promote}[args.action](path))
    except RotationError as err:
        print(f"error: {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
