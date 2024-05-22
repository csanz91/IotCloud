import logging
import signal

from threading import Event

import energy_calc
import influxdb_interface

logger = logging.getLogger()
handler = logging.handlers.RotatingFileHandler(
    "../logs/energy.log", mode="a", maxBytes=1024 * 1024 * 10, backupCount=2
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


MONITORING_FREC = 3600 * 2  # seconds

logger.info("Starting...")

try:
    while not exitEvent.is_set():
        tariffs_cost = energy_calc.get_data()
        influxdb_interface.saveTariffsCost(tariffs_cost)

        exitEvent.wait(MONITORING_FREC)
finally:
    logger.info("Exiting...")
