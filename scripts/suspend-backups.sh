#!/bin/bash
mosquitto_pub -h "${MQTT_HOST:?MQTT_HOST not set}" -t servers/host-backups -m suspend
