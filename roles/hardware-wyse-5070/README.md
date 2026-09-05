# Dell Wyse 5070 Hardware

This role installs the `r8168-dkms` driver for the Realtek RTL8111/8168 PCIe Gigabit NIC in the Dell Wyse 5070 thin client. Ubuntu installs the generic `r8169` driver by default, and this driver can cause intermittent connectivity problems on this hardware. The DKMS package builds and installs the vendor `r8168` driver, and blocks `r8169`.

## Notes

- After the first install, you must usually reboot for the new driver to load and for `r8169` to be blocked.
- This covers all Wyse 5070-specific configuration beyond standard Ubuntu provisioning. Generic roles handle the rest.
