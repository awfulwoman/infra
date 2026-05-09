#!/bin/bash
mosquitto_pub -h "${MQTT_HOST:?MQTT_HOST not set}" -t servers/server-8gb-backups -m suspend
