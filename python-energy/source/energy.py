from datetime import datetime, timedelta
import logging
import signal

from threading import Event
from zoneinfo import ZoneInfo

import pandas as pd

import energy_tariffs
import energy_consumption
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

tz = ZoneInfo(key="Europe/Madrid")

MONITORING_FREC = 3600 * 8  # seconds
PAST_DAYS = 2

logger.info("Starting...")

try:
    while not exitEvent.is_set():

        # Get the current date
        current_date = datetime.now(tz=tz)
        start_date = current_date - timedelta(days=PAST_DAYS)
        end_date = current_date + timedelta(days=2)

        # Save the tariffs cost
        tariffs: pd.DataFrame = energy_tariffs.get_indexed_tariffs_cost(
            start_date, end_date, tz
        )
        influxdb_interface.saveTariffsCost(tariffs.to_dict(orient="index"))

        # Save the energy consumption
        consumption = energy_consumption.get_energy_consumption(start_date, end_date)
        if consumption.empty:
            logger.error("Unable to retrieve the consumption data")
            continue

        cups = consumption.iloc[0]["cups"]
        consumption.drop(columns="cups", inplace=True)

        influxdb_interface.saveEnergyConsumption(
            cups, consumption.to_dict(orient="index")
        )
        exitEvent.wait(MONITORING_FREC)
finally:
    logger.info("Exiting...")
