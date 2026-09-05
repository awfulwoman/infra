# WPA Supplicant

This role writes a minimal `wpa_supplicant.conf` to `/etc/wpa_supplicant/wpa_supplicant.conf`, with the home network SSID and PSK. Use it on hosts where `wpa_supplicant` manages WiFi directly, rather than NetworkManager or netplan.

Credentials are pulled from Ansible Vault variables:

- `vault_homenetwork_ssid` — the WiFi network name
- `vault_homenetwork_password` — the WPA2 pre-shared key

## Notes

- This role is deliberately minimal: one network, no priority, no extras.
- The task does not use `become`, so the Ansible user needs write access to `/etc/wpa_supplicant/`. Most deployments need `become: true` added, or the file permissions adjusted first.
- If the new configuration does not take effect after deployment, restart `wpa_supplicant` or the network manager service.
