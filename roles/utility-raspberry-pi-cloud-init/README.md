# Raspberry Pi cloud-init

## Download links

* [Ubuntu 26.04](https://cdimage.ubuntu.com/releases/26.04/release/ubuntu-26.04-preinstalled-server-arm64+raspi.img.xz)
* [Ubuntu 24.04.4](https://cdimage.ubuntu.com/releases/24.04/release/ubuntu-24.04.4-preinstalled-server-arm64+raspi.img.xz)

## Flashing images to card

```bash
xzcat ubuntu-26.04-preinstalled-server-arm64+raspi.img.xz | sudo dd of=/dev/rdisk4 bs=1m status=progress
```
