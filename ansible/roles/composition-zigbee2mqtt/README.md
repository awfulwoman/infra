# container-zigbee2mqtt

## Reason for enabling multiple containers

Xiaomi devices do not play nicely with the Zigbee spec and can break networks when used with devices from other manufacturers. They therefore need to be sanboxed on their own Zigbee network.

- https://community.hubitat.com/t/xiaomi-aqara-devices-pairing-keeping-them-connected/623
- https://community.home-assistant.io/t/aqara-temperature-sensors/451505/11

## Notes

- If running multiple instances use two different MQTT base topics! See: https://github.com/Koenkk/zigbee2mqtt/issues/3557
