from discover_composition_subdomains import discover_composition_subdomains


def write_role_defaults(roles_dir, role_name, content):
    defaults_dir = roles_dir / role_name / "defaults"
    defaults_dir.mkdir(parents=True)
    (defaults_dir / "main.yaml").write_text(content)


def test_discovers_declared_subdomains(tmp_path):
    write_role_defaults(
        tmp_path,
        "composition-jellyfin",
        "composition_name: jellyfin\ncomposition_dns_subdomains: [jellyfin, jellyfin-vue]\n",
    )

    result = discover_composition_subdomains(tmp_path)

    assert result == {"jellyfin": ["jellyfin", "jellyfin-vue"]}


def test_role_without_declared_subdomains_is_absent_not_empty(tmp_path):
    write_role_defaults(
        tmp_path,
        "composition-container-management",
        "composition_name: container-management\n",
    )

    result = discover_composition_subdomains(tmp_path)

    assert result == {}


def test_declared_empty_list_is_present_as_empty(tmp_path):
    write_role_defaults(
        tmp_path,
        "composition-matter",
        "composition_name: matter\ncomposition_dns_subdomains: []\n",
    )

    result = discover_composition_subdomains(tmp_path)

    assert result == {"matter": []}


def test_non_composition_role_is_ignored(tmp_path):
    write_role_defaults(
        tmp_path,
        "system-docker",
        "composition_dns_subdomains: [docker]\n",
    )

    result = discover_composition_subdomains(tmp_path)

    assert result == {}


def test_role_with_no_defaults_file_does_not_crash(tmp_path):
    (tmp_path / "composition-no-defaults" / "tasks").mkdir(parents=True)

    result = discover_composition_subdomains(tmp_path)

    assert result == {}
