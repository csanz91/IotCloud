from datetime import datetime
import logging
import logging.handlers

from zoneinfo import ZoneInfo

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

tz = ZoneInfo(key="Europe/Madrid")

logger.info("Starting...")


def main():
    logger.info("Starting energy consumption check...")
    try:
        # Get the last saved timestamp and current date
        current_date = datetime.now(tz=tz)
        start_date = influxdb_interface.getLastTimestamp()
        end_date = current_date

        logger.info(f"Checking energy consumption from {start_date} to {end_date}")

        # Save the energy consumption
        consumption = energy_consumption.get_energy_consumption(start_date, end_date)
        if consumption.empty:
            logger.error("Unable to retrieve the consumption data")
            return

        cups = consumption.iloc[0]["cups"]
        consumption.drop(columns="cups", inplace=True)

        logger.info(f"Saving energy consumption for {cups}")
        logger.info(f"Got {len(consumption)} rows")

        influxdb_interface.saveEnergyConsumption(
            cups, consumption.to_dict(orient="index")
        )

        last_measurment_saved = influxdb_interface.getLastTimestamp()
        logger.info(f"Last measurement saved: {last_measurment_saved}")
        
    except Exception as e:
        logger.error(f"Error during execution: {e}", exc_info=True)
    finally:
        logger.info("Finished energy consumption check")


if __name__ == "__main__":
    main()
