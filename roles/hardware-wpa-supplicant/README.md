# WPA Supplicant

Writes a minimal `wpa_supplicant.conf` to `/etc/wpa_supplicant/wpa_supplicant.conf` with the home network SSID and PSK. Used on hosts where WiFi is managed directly by `wpa_supplicant` rather than NetworkManager or netplan.

Credentials are pulled from Ansible Vault variables:

- `vault_homenetwork_ssid` — the WiFi network name
- `vault_homenetwork_password` — the WPA2 pre-shared key

## Notes

- This role is intentionally minimal — single network, no priority, no extras.
- The task does not use `become`, so the Ansible user needs write access to `/etc/wpa_supplicant/`. Most deployments will need `become: true` added, or the file permissions adjusted beforehand.
- After deployment, `wpa_supplicant` or the network manager service may need to be restarted for the new config to take effect.
