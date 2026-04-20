# Dell Wyse 5070 Hardware

Installs the `r8168-dkms` driver for the Realtek RTL8111/8168 PCIe Gigabit NIC found in the Dell Wyse 5070 thin client. Ubuntu ships the generic `r8169` driver by default, which can cause intermittent connectivity issues on this hardware. The DKMS package builds and installs the vendor `r8168` driver and blacklists `r8169`.

## Notes

- A reboot is typically required after first installation for the new driver to load and `r8169` to be blacklisted.
- This is the entirety of Wyse 5070-specific configuration needed beyond standard Ubuntu provisioning — the rest is handled by generic roles.
