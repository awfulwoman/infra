# Devices

What do I mean by a device? I see a device as something that isn't fully under my control and/or cannot be configured via SSH. This means things like Chromecasts are definitely a device because Google controls it, and I can't SSH in. Same goes for any Kindles, Apple TVs, iPads, etc.

What about things that I can SSH into? My reMarkable 2 tablet lets me SSH in. But I can't configure it. Same with my partner's Netgear NAS.

Things that definitely _aren't_ simple devices are x86 servers, Raspberry Pi devices, and laptops.

## Zigbee

Most of the devices in my house are not connected by WiFi - they're connected by [https://en.wikipedia.org/wiki/Zigbee](Zigbee). This is a lightweight over the air protocol that allows simple sensors and switches to form their own radio mesh.

They're all controlled by a Conbee II USB stick that is connected to one of my many Raspberry Pis.


## MQTT

MQTT is a simple messaging protocol running over HTTP. 

## Zigbee and MQTT

I use [http://zigbee2mqtt.io](Zigbee2MQTT) to take the Zigbee signals and turn them into well formatted MQTT messages that can be consumed/updated across my network.

## Naming conventions for Zigbee devices

Back when I started I made this spreadsheet to help me to name devices in a way that is compatible with both MQTT and Home Assistant. You might find it useful!

https://docs.google.com/spreadsheets/d/1JEz_QobnGvY8sxKx7RLfsss1d7irSiBMTl8NEbtI3H0
