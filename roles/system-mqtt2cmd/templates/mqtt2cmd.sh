#!/bin/bash

# mqtt2cmd - A simple MQTT client that executes commands based on received MQTT messages.

while true  # Keep an infinite loop to reconnect when connection lost/broker unavailable
do
    mosquitto_sub -h "{{ mqtt2cmd_broker }}" -t "{{ mqtt2cmd_basetopic }}/{{ ansible_facts['hostname'] }}" | while read -r payload
    do
        echo "Rx MQTT: ${payload}"

        if [ "$payload" == "shutdown" ]; then
            wall "System is being shutdown via mqtt2cmd"
            shutdown now
        fi

        if [ "$payload" == "suspend" ]; then
            wall "System is being suspended via mqtt2cmd"
            systemctl suspend
        fi

        if [ "$payload" == "reboot" ]; then
            wall "System is being rebooted via mqtt2cmd"
            reboot
        fi

        if [ "$payload" == "ansiblepull" ]; then
            wall "System is being updated via mqtt2cmd"
            runuser -l "{{ ansible_user }}" -c "/opt/ansible/ansible-pull-full.sh"
        fi

        if [ "$payload" == "restart zigbee2mqtt" ]; then
            wall "zigbee2mqtt is being restarted via mqtt2cmd"
            docker restart zigbee2mqtt
        fi

        if [ "$payload" == "restart torrents" ]; then
            wall "torrent service is being restarted via mqtt2cmd"
            docker restart qbittorrent
        fi

        if [ "$payload" == "restart downloads" ]; then
            wall "Downloads are being restarted via mqtt2cmd"
            docker compose --file /fastpool/compositions/downloads/docker-compose.yaml restart
        fi
    done
    sleep 10
done
