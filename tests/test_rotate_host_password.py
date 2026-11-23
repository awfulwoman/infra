"""Tests for scripts/rotate-host-password.py.

The script moves a host's vault_password through two phases without ever
printing a secret: `stage` writes a new random value as vault_password_next,
`promote` swaps it into vault_password. Encryption is injected, so these tests
never call ansible-vault.
"""

import importlib.util
import re
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "rotate-host-password.py"
spec = importlib.util.spec_from_file_location("rotate_host_password", SCRIPT)
rotate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rotate)

IND = " " * 10


def block(name, body="aaaa", header="$ANSIBLE_VAULT;1.2;AES256;beanpod"):
    return f"{name}: !vault |\n{IND}{header}\n{IND}{body}\n"


def fake_encryptor(calls):
    def encrypt(name, value, vault_id):
        calls.append((name, value, vault_id))
        return f"{name}: !vault |\n{IND}$ANSIBLE_VAULT;1.2;AES256;beanpod\n{IND}NEWCIPHER\n"

    return encrypt


@pytest.fixture
def vault_file(tmp_path):
    path = tmp_path / "vault_credentials.yaml"
    path.write_text(
        "# become password for this host\n"
        "\n"
        + block("vault_password", "OLDCIPHER")
        + "\n"
        + block("vault_zfs_passphrase", "ZFSCIPHER")
    )
    return path


# --- stage -----------------------------------------------------------------


def test_stage_adds_next_block_and_keeps_everything_else(vault_file):
    calls = []
    rotate.stage(vault_file, fake_encryptor(calls))
    text = vault_file.read_text()
    assert "vault_password_next: !vault |" in text
    assert "NEWCIPHER" in text
    assert "OLDCIPHER" in text, "the live password must stay until promote"
    assert "ZFSCIPHER" in text
    assert text.startswith("# become password for this host\n")


def test_stage_generates_a_64_hex_secret_and_passes_the_vault_id(vault_file):
    calls = []
    rotate.stage(vault_file, fake_encryptor(calls))
    (name, value, vault_id), = calls
    assert name == "vault_password_next"
    assert re.fullmatch(r"[0-9a-f]{64}", value)
    assert vault_id == "beanpod"


def test_stage_never_returns_or_prints_the_secret(vault_file, capsys):
    calls = []
    result = rotate.stage(vault_file, fake_encryptor(calls))
    secret = calls[0][1]
    out = capsys.readouterr()
    assert secret not in (result or "")
    assert secret not in out.out + out.err
    assert secret not in vault_file.read_text()


def test_stage_replaces_an_earlier_next_block(vault_file):
    rotate.stage(vault_file, fake_encryptor([]))
    rotate.stage(vault_file, fake_encryptor([]))
    assert vault_file.read_text().count("vault_password_next:") == 1


def test_stage_uses_no_vault_id_when_the_live_block_has_none(tmp_path):
    path = tmp_path / "v.yaml"
    path.write_text(block("vault_password", "OLD", header="$ANSIBLE_VAULT;1.1;AES256"))
    calls = []
    rotate.stage(path, fake_encryptor(calls))
    assert calls[0][2] is None


def test_stage_refuses_when_there_is_no_live_vault_password(tmp_path):
    path = tmp_path / "v.yaml"
    path.write_text("# vault_password: !vault |\n#   $ANSIBLE_VAULT;1.2;AES256;beanpod\n#   x\n")
    with pytest.raises(rotate.RotationError):
        rotate.stage(path, fake_encryptor([]))


# --- promote ---------------------------------------------------------------


def test_promote_swaps_next_into_vault_password(vault_file):
    rotate.stage(vault_file, fake_encryptor([]))
    rotate.promote(vault_file)
    text = vault_file.read_text()
    assert "vault_password_next" not in text
    assert "OLDCIPHER" not in text
    assert re.search(r"^vault_password: !vault \|\n {10}\$ANSIBLE_VAULT[^\n]*\n {10}NEWCIPHER\n", text, re.M)
    assert "ZFSCIPHER" in text
    assert text.startswith("# become password for this host\n")


def test_promote_refuses_without_a_staged_value(vault_file):
    with pytest.raises(rotate.RotationError):
        rotate.promote(vault_file)


# --- host path -------------------------------------------------------------


def test_vault_file_for_host_points_at_its_credentials_file():
    path = rotate.vault_file_for("server-8gb-backups")
    assert path.parts[-3:] == ("server-8gb-backups", "vault_credentials.yaml")[-2:] or path.name == "vault_credentials.yaml"
    assert path.parent.name == "server-8gb-backups"


def test_vault_file_for_host_rejects_path_tricks():
    with pytest.raises(rotate.RotationError):
        rotate.vault_file_for("../etc")
