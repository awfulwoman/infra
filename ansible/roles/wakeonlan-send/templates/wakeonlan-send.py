import paho.mqtt.client as mqtt
import os
import re

def on_connect(client, userdata, flags, rc):  
	# The callback for when the client connects to the broker 
	print("Connected with result code {0}".format(str(rc)))
	print("Connected to %s:%s" % (client._host, client._port))
	client.subscribe("servers/host-controller/wakeup")  

def on_message(client, userdata, msg): 
	# The callback for when a PUBLISH message is received from the server. 
	# print(msg.topic+" "+str(msg.qos)+" "+str(msg.payload.decode("utf-8")))
	payload = str(msg.payload.decode("utf-8"))
	if re.match("[0-9a-f]{2}([-:]?)[0-9a-f]{2}(\\1[0-9a-f]{2}){4}$", payload.lower()):
		command = "wakeonlan " + str(msg.payload.decode("utf-8"))
		os.system(command)

client = mqtt.Client("wakeonlan_mqtt")
client.on_connect = on_connect
client.on_message = on_message
client.connect("mqtt.affordablepotatoes.com", 1883, 60) 
client.loop_forever()


