# ansible-assert-platform

Utility role that asserts the current Ansible target platform is in a caller-supplied allowlist. Include this role at the top of any role that only supports specific operating systems, passing `ansible_assert_platform_supported` as a list of expected `ansible_facts['system']` values (e.g. `Linux`, `Darwin`).
