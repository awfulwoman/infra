from linux2mqtt import Linux2Mqtt, DEFAULT_CONFIG

cfg = Linux2MqttConfig({ 
  **DEFAULT_CONFIG,
  "host": "mosquitto",
})

try:
  linux2mqtt = Linux2Mqtt(cfg)
  linux2mqtt.connect()
  linux2mqtt.loop_busy()

except Exception as ex:
  # Do something
