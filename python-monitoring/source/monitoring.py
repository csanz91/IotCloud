import logging
import os
import socket
import time

from logging import handlers

import influxdb_interface
import docker_metrics
import host_metrics
import utils


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

MONITORING_FREC = 10  # seconds

logger.info("Starting...")


while True:

    hostMetrics = host_metrics.getHostMetrics()
    influxdb_interface.saveHostMetrics(hostMetrics)

    dockerMetrics = docker_metrics.getContainersMetrics()
    influxdb_interface.saveDockerMetrics(dockerMetrics)

    time.sleep(MONITORING_FREC)
