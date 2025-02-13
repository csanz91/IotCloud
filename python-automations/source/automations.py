import logging
import logging.config
from logging import handlers
from threading import Event
import signal
from mqtt_setup import mqttclient
import devices
import actions
import os
import pkgutil
import importlib
from api import start_api_server
import threading

actions_dir = os.path.dirname(actions.__file__)
for _, module_name, _ in pkgutil.iter_modules([actions_dir]):
    importlib.import_module(f"actions.{module_name}")

logger = logging.getLogger()
handler = handlers.RotatingFileHandler(
    "../logs/automations.log", mode="a", maxBytes=1024 * 1024 * 10, backupCount=2
)
formatter = logging.Formatter(
    "%(asctime)s <%(levelname).1s> %(funcName)s:%(lineno)s: %(message)s"
)
logger.setLevel(logging.INFO)
handler.setFormatter(formatter)
logger.addHandler(handler)

####################################
# Global variables
####################################
exitEvent = Event()


def exit_gracefully(signum, frame):
    exitEvent.set()
    # Shutdown all event stream executors
    for device in devices.all_devices:
        for stream in getattr(device, 'event_streams', []):
            stream.shutdown()


signal.signal(signal.SIGINT, exit_gracefully)
signal.signal(signal.SIGTERM, exit_gracefully)

def onConnect(client, userdata, flags, rc):
    logger.info("Connected to the MQTT broker")
    # Subscribe all devices after connection
    for device in devices.all_devices:
        device.subscribe()

mqttclient.on_connect = onConnect

# Connect and start the MQTT client loop
mqttclient.connect("mosquitto")
mqttclient.loop_start()

# Start API server in a separate thread
api_thread = threading.Thread(target=start_api_server, daemon=True)
api_thread.start()

logger.info("Starting...")

try:
    while not exitEvent.is_set():
        exitEvent.wait(1.0)
finally:
    # Shutdown all event stream executors
    for device in devices.all_devices:
        for stream in getattr(device, 'event_streams', []):
            stream.shutdown()
    mqttclient.loop_stop()
    logger.info("Exiting...")
