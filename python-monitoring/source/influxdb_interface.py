import logging
import logging.config
import os

import influxdb
import utils

logger = logging.getLogger(__name__)

MONITORING_DB = os.environ["INFLUXDB_MONITORING_DB"]


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
    influxDb.create_database(MONITORING_DB)

    # Setup the retention policies
    influxDb.create_retention_policy("monitoring_raw", "45d", 1)
    influxDb.create_retention_policy("monitoring_downsampled", "730d", 1)

    influxDb.query(f""" DROP CONTINUOUS QUERY "monitoring_1h" ON {MONITORING_DB};""")
    influxDb.query(
        f""" CREATE CONTINUOUS QUERY "monitoring_1h" ON {MONITORING_DB} BEGIN
                                SELECT mean("value") AS "value",
                                       max("value") AS "max_value",
                                       min("value") AS "min_value"
                                INTO "monitoring_downsampled"."monitoring"
                                FROM "monitoring_raw"."monitoring"
                                GROUP BY time(1h), *
                              END """
    )


# Influx databse setup
influxDb = influxdb.InfluxDBClient(
    os.environ["INFLUXDB_HOST"], database=MONITORING_DB, username="", password=""
)

# Initialize the database
init(influxDb)


def saveHostMetrics(data):

    dataToWrite = [
        {
            "measurement": "hosts_monitoring",
            "tags": {"host": utils.getHostname()},
            "fields": data,
        }
    ]

    influxDb.write_points(dataToWrite, retention_policy="monitoring_raw")


def saveDockerMetrics(containersMetrics):

    dataToWrite = [
        {
            "measurement": "containers_monitoring",
            "tags": {"container": name, "host": utils.getHostname()},
            "fields": metrics,
        }
        for name, metrics in containersMetrics.items()
    ]
    influxDb.write_points(dataToWrite, retention_policy="monitoring_raw")
