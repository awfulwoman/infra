import paho.mqtt.client as mqtt
import os
import re

def on_connect(client, userdata, flags, rc):  
	print("Connected to %s:%s" % (client._host, client._port))
	client.subscribe("servers/host-controller/wakeup")
	# client.subscribe("{{ wakeonlansend_topic }}")

def on_message(client, userdata, msg): 
	payload = str(msg.payload.decode("utf-8"))
	# Valid MAC addresses only
	if re.match("[0-9a-f]{2}([-:]?)[0-9a-f]{2}(\\1[0-9a-f]{2}){4}$", payload.lower()):
		command = "wakeonlan " + str(msg.payload.decode("utf-8"))
		# command = "{{ wakeonlansend_command }} " + str(msg.payload.decode("utf-8"))
		os.system(command)

client = mqtt.Client("wakeonlan_mqtt")
client.on_connect = on_connect
client.on_message = on_message
client.connect("mqtt.affordablepotatoes.com", 1883, 60)
# client.connect("{{ wakeonlansend_broker }}", {{ wakeonlansend_broker_port}}, 60)
client.loop_forever()
