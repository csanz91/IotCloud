from docker_secrets import getDocketSecrets
import paho.mqtt.client as mqtt

# Setup MQTT client
mqttclient = mqtt.Client()
token = getDocketSecrets("mqtt_token")
mqttclient.username_pw_set(token, "_")