# Naming schemes

## Infrastructure

configure-dns-server                to    infra/name-server
configure-dhcpd-server              to    infra/dhcp-server
configure-acme-wildcard             to    infra/cert-renewal-server
install-msmtp                       to    infra/smtp-server
install-nut-server                  to    infra/nut-server
nfs-server                          to    infra/nfs-server
zfs-backup-server                   to    infra/zbackup-server

## Bootstrap

bootstrap-ubuntu-server             to    bootstrap/ubuntu-server
bootstrap-intel-mac                 to    bootstrap/intel-mac

## Hardware

hardware-enable-console-blanking    to    hardware/enable-console-blanking
hardware-grub-tune                  to    hardware/grub-tune
hardware-host-bus-adapter           to    hardware/host-bus-adapter
hardware-raspberry-pi               to    hardware/raspberry-pi
hardware-raspberrypi-camera         to    hardware/raspberry-pi-camera
hardware-rtl-433                    to    hardware/rtl-433
hardware-wpa-supplicant             to    hardware/wpa-supplicant
hardware-wyse-5070                  to    hardware/wyse-5070
hardware-zigbee-conbee              to    hardware/zigbee-conbee
wakeonlan                           to    hardware/wakeonlan

## Networking

configure-dns                       to    networking/register-tailscale-subdomain
ip-address-dhcp                     to    networking/address-dhcp
ip-address-forwarding               to    networking/address-forwarding
ip-address-static                   to    networking/address-static

## Ansible

install-ansible                     to    ansible/core
install-ansible-pull                to    ansible/autoupdate

## System

configure-motd                      to    system/motd
configure-sshkey                    to    system/generate-sshkey
configure-smartmontools             to    system/smartmontools
install-beep                        to    system/beep
sleepuntil                          to    system/sleepuntil
powertop                            to    system/powertop

## Client

nfs-client                          to    clients/nfs
install-nut-client                  to    clients/nut
zfs-backup-client                   to    clients/zbackup

## Monitoring

monitoring-healthchecksio           to    monitoring/healthchecksio
install-linux2mqtt                  to    monitoring/linux2mqtt

## Virtualization

vm-guest                            to    virtualisation/qemu-guest
vm-host                             to    virtualisation/qemu-host

## Users

config-deployment-user              to    users/sitedeployment

## ZFS

zfs-core                            to    zfs/core

## Compositions
