#!/usr/bin/env python3
"""Refuse a task that renders a secret into a result without `no_log: true`.

A deploy runs with the vault unlocked, so a task that prints a vaulted value
writes it, in plaintext, into the run log — and the run log is readable over the
API. Masking at the read side is a last resort, not the control: it can only
recognise shapes it has been taught, and it cannot tell a real key from a task
name. This is the control.

What counts as printing: a task result Ansible always shows, or shows when the
task fails.

  debug        msg, var
  assert       fail_msg
  fail         msg
  command      cmd, argv, a bare string, _raw_params
  shell        same as command
  raw          a bare string
  uri/others   not checked: the arguments are not shown on success, and
               flagging every module that passes a secret in its arguments
               would push `no_log` onto tasks that do not need it

The task is reported when a `{{ ... }}` in one of those fields names a variable
that looks like a secret, and neither the task nor an enclosing block sets
`no_log: true`.

Deliberately needs neither Ansible nor the vault password: it reads YAML and
matches variable names, so it runs in pre-commit on any checkout.

    scripts/validate-secret-logging.py [paths...]     (default: roles/ playbooks/)
    scripts/validate-secret-logging.py --report       (list, always exit 0)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
SCAN_DIRS = ["roles", "playbooks"]

# A variable name that carries a secret. Matched against the identifier inside
# {{ }}, never against the surrounding text, so prose that merely says "token"
# is not flagged.
#
# The secret word must be the whole name or its last component. A looser
# `\w*password\w*` also matched `onepassword_connect_host` and
# `preflight_onepassword_timeout` — the product name contains "password", and
# those are a host and a timeout, not secrets.
SECRET_NAME = re.compile(
    r"(?ix)^(?:"
    r"vault_\w*"  # everything in the vault, by convention
    r"|(?:password|passwd|passphrase|secret|token|pass)"  # bare
    r"|\w*_(?:password|passwd|passphrase|secret|token|pass"
    r"|api[_-]?key|access[_-]?key|private[_-]?key|client[_-]?secret)"
    r")$"
)

# {{ ... }} and {% ... %} bodies, so only identifiers inside an expression are
# considered.
EXPRESSION = re.compile(r"\{\{(.*?)\}\}|\{%(.*?)%\}", re.DOTALL)
IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

# module -> fields of its arguments that reach the result
PRINTERS = {
    "debug": ("msg", "var"),
    "assert": ("fail_msg",),
    "fail": ("msg",),
    "command": ("cmd", "argv", "_raw_params"),
    "shell": ("cmd", "argv", "_raw_params"),
    "raw": ("_raw_params",),
}

# Ansible's documented prefixes; `ansible.builtin.debug` and a bare `debug` are
# the same module.
MODULE_PREFIXES = ("ansible.builtin.", "ansible.legacy.", "ansible.raw.", "")

# no_log applies to the whole block, so it is tracked down the task tree.
BLOCK_KEYS = ("block", "rescue", "always")


class _Loader(yaml.SafeLoader):
    """SafeLoader that ignores Ansible tags (`!vault`, `!unsafe`)."""


def _unknown(loader: yaml.SafeLoader, node: yaml.Node) -> None:
    return None


_Loader.add_multi_constructor("", lambda loader, suffix, node: None)


def documents(path: Path):
    try:
        return list(yaml.load_all(path.read_text(), Loader=_Loader))
    except yaml.YAMLError as exc:
        print(f"{path}: unreadable YAML: {exc}", file=sys.stderr)
        raise SystemExit(1)


def module_name(key: str) -> str | None:
    for prefix in MODULE_PREFIXES:
        if key.startswith(prefix):
            name = key[len(prefix):]
            if name in PRINTERS:
                return name
    return None


def fields_for(module: str, args) -> list[str]:
    """The values from a module's arguments that can reach the result."""
    wanted = PRINTERS[module]
    if isinstance(args, str):
        return [args]
    if not isinstance(args, dict):
        return []
    values = []
    for field in wanted:
        value = args.get(field)
        if value is None:
            continue
        if isinstance(value, (list, tuple)):
            values.extend(str(v) for v in value)
        else:
            values.append(str(value))
    return values


def secret_names_in(text: str) -> set[str]:
    names = set()
    for braced, statement in EXPRESSION.findall(text):
        for identifier in IDENTIFIER.findall(braced or statement):
            if SECRET_NAME.match(identifier):
                names.add(identifier)
    return names


def walk(node, protected: bool, findings: list, path: Path, task_name: str) -> None:
    """Walk every mapping, carrying whether an enclosing block set no_log."""
    if isinstance(node, list):
        for item in node:
            walk(item, protected, findings, path, task_name)
        return
    if not isinstance(node, dict):
        return

    name = node.get("name") or task_name
    no_log = node.get("no_log")
    here_protected = protected or (no_log is not None and no_log is not False)

    for key, args in node.items():
        module = module_name(key) if isinstance(key, str) else None
        if module is None:
            if key in BLOCK_KEYS:
                walk(args, here_protected, findings, path, name)
            continue
        if here_protected:
            continue
        for value in fields_for(module, args):
            for secret in sorted(secret_names_in(value)):
                findings.append((path, name, module, secret))

    for key in BLOCK_KEYS:
        if key in node:
            walk(node[key], here_protected, findings, path, name)


def yaml_files(paths: list[Path]) -> list[Path]:
    files = []
    for path in paths:
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend(sorted(path.rglob("*.yaml")))
    # roles/*/templates/ holds Jinja-templated YAML, not playbook YAML — the same
    # reason check-yaml excludes it. `vault_` files are ciphertext.
    return [
        f
        for f in files
        if f.suffix in {".yaml", ".yml"}
        and "templates" not in f.parts
        and not f.name.startswith("vault_")
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", help="files or directories to scan")
    parser.add_argument(
        "--report", action="store_true", help="list findings and always exit 0"
    )
    args = parser.parse_args()

    roots = [Path(p) for p in args.paths] or [REPO / d for d in SCAN_DIRS]
    findings = []
    checked = 0
    for path in yaml_files(roots):
        checked += 1
        for document in documents(path):
            walk(document, False, findings, path, "")

    if not findings:
        if args.report:
            print(f"secret logging: {checked} files, nothing printed in the clear")
        return 0

    stream = sys.stdout if args.report else sys.stderr
    print(
        f"secret logging: {len(findings)} field(s) print a secret without no_log: true:",
        file=stream,
    )
    for path, name, module, secret in findings:
        where = f'{name}' if name else "(unnamed task)"
        print(f"  {path.relative_to(REPO)}: {where}", file=stream)
        print(f"    {module} renders {secret} into the result", file=stream)
    if not args.report:
        print(
            "\nAdd `no_log: true` to the task, or stop printing the value. "
            "See .opencode/rules/ansible-vault.md",
            file=stream,
        )
        sys.exit(1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
