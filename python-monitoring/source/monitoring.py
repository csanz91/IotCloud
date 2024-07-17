import logging
import signal

from threading import Event

import docker_metrics
import host_metrics
import influxdb_interface

logger = logging.getLogger()
handler = logging.handlers.RotatingFileHandler(
    "../logs/monitoring.log", mode="a", maxBytes=1024 * 1024 * 10, backupCount=2
)
formatter = logging.Formatter(
    "%(asctime)s <%(levelname).1s> %(funcName)s:%(lineno)s: %(message)s"
)
logger.setLevel(logging.INFO)
handler.setFormatter(formatter)
logger.addHandler(handler)

exitEvent = Event()


def exit_gracefully(signum, frame):
    exitEvent.set()


signal.signal(signal.SIGINT, exit_gracefully)
signal.signal(signal.SIGTERM, exit_gracefully)


MONITORING_FREC = 10  # seconds

logger.info("Starting...")


try:
    while not exitEvent.is_set():
        hostMetrics = host_metrics.getHostMetrics()
        influxdb_interface.saveHostMetrics(hostMetrics)

        dockerMetrics = docker_metrics.getContainersMetrics()
        influxdb_interface.saveDockerMetrics(dockerMetrics)

        exitEvent.wait(MONITORING_FREC)
finally:
    logger.info("Exiting...")
