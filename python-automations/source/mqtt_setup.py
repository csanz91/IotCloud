from docker_secrets import get_docker_secrets
import paho.mqtt.client as mqtt

# Setup MQTT client
mqttclient = mqtt.Client()
token = get_docker_secrets("mqtt_token")
mqttclient.username_pw_set(token, "_")