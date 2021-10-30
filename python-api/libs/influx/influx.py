from influxdb import InfluxDBClient
import logging

logger = logging.getLogger(__name__)


class InfluxClient:
    def __init__(
        self, host, username, password, database, ssl=False, timeout=60, port=8086
    ):

        self.connectionCredentials = {
            "host": host,
            "username": username,
            "password": password,
            "database": database,
            "ssl": ssl,
            "timeout": timeout,
            "port": port,
            "verify_ssl": True,
        }

        self.connect()

    def connect(self):
        self.client = InfluxDBClient(**self.connectionCredentials)

    def query(self, query, database=None):
        try:
            result = self.client.query(query, database=database, epoch="s")
            return result
        except KeyboardInterrupt:
            raise KeyboardInterrupt()
        except:
            logger.error("Exception when query the data.", exc_info=True)
            self.connect()

    def close(self, *args):
        self.client.close()
        logger.info("Influx closed")
