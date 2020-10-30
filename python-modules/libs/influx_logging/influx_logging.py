import logging
import time
from influxdb import InfluxDBClient


SYSLOG_LEVELS = {
    logging.CRITICAL: 2,
    logging.ERROR: 3,
    logging.WARNING: 4,
    logging.INFO: 6,
    logging.DEBUG: 7,
}


# skip_list is used to filter additional fields in a log message.
# It contains all attributes listed in
# http://docs.python.org/library/logging.html#logrecord-attributes
# plus exc_text, which is only found in the logging module source,
# and id, which is prohibited by the GELF format.

SKIP_LIST = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "id",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "thread",
    "threadName",
    "stack_info",
}


class InfluxHandler(logging.Handler):
    """InfluxDB Log handler
    """

    def __init__(self, serviceName):
        database = "logging"
        rp = "10weeks"
        self.measurement = "logs"
        self.serviceName = serviceName
        self.client = InfluxDBClient(host="influxdb", database=database)

        if database not in {x["name"] for x in self.client.get_list_database()}:
            self.client.create_database(database)

        if rp not in {x["name"] for x in self.client.get_list_retention_policies()}:
            self.client.create_retention_policy(rp, "10w", 1, default=True)

        logging.Handler.__init__(self)

    def emit(self, record):
        """
        Emit a record.

        Send the record to the Web server as line protocol
        """
        if not has_extra_fields(record):
            return

        self.client.write_points(self.get_point(record))

    def get_point(self, record):
        fields = {
            "message": record.getMessage(),
            "level_name": logging.getLevelName(record.levelno),
        }

        tags = {
            "service": self.serviceName,
            "level": SYSLOG_LEVELS.get(record.levelno, record.levelno),
        }
        tags = add_extra_fields(tags, record)

        return [
            {
                "measurement": self.measurement,
                "tags": tags,
                "fields": fields,
                "time": int(record.created * 10 ** 9),  # nanoseconds
            }
        ]


def has_extra_fields(record):
    for key in record.__dict__:
        if key not in SKIP_LIST and not key.startswith("_"):
            return True
    return False


def add_extra_fields(message_dict, record):
    for key, value in record.__dict__.items():
        if key not in SKIP_LIST and not key.startswith("_"):
            message_dict[key] = value
    return message_dict
