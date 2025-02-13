from datetime import datetime
import logging
import logging.config
import os
from zoneinfo import ZoneInfo

import influxdb

logger = logging.getLogger(__name__)

ENERGY_DB = os.environ["INFLUXDB_DB"]


def init(influxDb):
    """
    From the docs: If you attempt to create a retention policy identical to one that
        already exists, InfluxDB does not return an error. If you attempt to create a
        retention policy with the same name as an existing retention policy but with
        differing attributes, InfluxDB returns an error.
    -i.e. If we want to edit some of the following values, do it in the Influx cli.

    The values received will be stored for 45 days at their original resolution,
        and they are aggregated every:
            -hour and stored for 2 years
    """
    # Create the database
    influxDb.create_database(ENERGY_DB)


# Influx databse setup
influxDb = influxdb.InfluxDBClient(
    os.environ["INFLUXDB_HOST"], database=ENERGY_DB, username="", password=""
)

# Initialize the database
init(influxDb)


def getLastTimestamp() -> datetime:
    """Get the last timestamp from the energy_consumption measurement"""
    query = 'SELECT * FROM "3years"."energy_consumption" ORDER BY time DESC LIMIT 1'
    result = influxDb.query(query)
    points = list(result.get_points())

    if not points:
        # If no data exists, return a date far in the past
        return datetime(2023, 1, 1, tzinfo=ZoneInfo("Europe/Madrid"))

    return datetime.fromisoformat(points[0]["time"].replace("Z", "+00:00")).astimezone(ZoneInfo("Europe/Madrid"))


def saveTariffsCost(data: dict[datetime, dict]):

    dataToWrite = [
        {"measurement": "tariffs_cost", "tags": {}, "fields": point, "time": time}
        for time, point in data.items()
    ]

    influxDb.write_points(dataToWrite, retention_policy="3years")


def saveEnergyConsumption(cups: str, data: dict[datetime, dict]):

    dataToWrite = [
        {
            "measurement": "energy_consumption",
            "tags": {"cups": cups},
            "fields": point,
            "time": time,
        }
        for time, point in data.items()
    ]

    influxDb.write_points(dataToWrite, retention_policy="3years")
