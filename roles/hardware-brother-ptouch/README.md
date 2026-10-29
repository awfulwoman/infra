# Hardware Brother P-touch

Lets the Ansible user print to a USB-connected Brother P-touch label printer (a PT-E550W on camina) without sudo. The kernel's `usblp` driver exposes the printer as `/dev/usb/lp0`, owned by `root:lp`, so the role adds the user to the `lp` group.

The user must log in again before the new group applies.

## Design Notes

[ptlabel](https://github.com/awfulwoman/ptlabel) prints through `/dev/usb/lp0`. It does not use raw USB access through pyusb, which needs the kernel driver detached and a udev rule. Group membership is enough.
