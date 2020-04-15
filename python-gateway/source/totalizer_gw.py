import logging
import logging.config
import os
from threading import Timer, Thread
import queue

import utils

logger = logging.getLogger(__name__)

##################
# Global values
##################
influxDb = None

# Stores the list of threads started
threads = []

# Maximum number of retries if a network depending function fails
maxRetries = 5

# Configure the number of workers
onTotalizerValueNumWorkerThreads = 3


# MQTT constants
version = 'v1'
topicHeader = "{version}/+/+/+/aux/".format(version=version)
totalizerTopic = topicHeader + "totalizer"


def onConnect(mqttclient, influxClient):
    global influxDb
    influxDb = influxClient

    mqttclient.subscribe(totalizerTopic)
    mqttclient.message_callback_add(totalizerTopic, onTotalizerValue)

    influxClient.client.query(""" CREATE CONTINUOUS QUERY "totalizer" ON %s BEGIN
                        SELECT NON_NEGATIVE_DIFFERENCE(LAST("totalizer")) as value
                        INTO "raw"."sensorsData"
                        FROM "raw"."totalizerData"
                        GROUP BY time(40s), *
                        END
                    """ % os.environ['INFLUXDB_DB'])

    influxClient.client.query(""" CREATE CONTINUOUS QUERY "totalizer_rate" ON %s
                        RESAMPLE EVERY 5m FOR 90m
                        BEGIN
                        SELECT NON_NEGATIVE_DERIVATIVE(LAST("totalizer"), 1h) as rate
                        INTO "raw"."totalizerData"
                        FROM "raw"."totalizerData"
                        GROUP BY time(20m), *
                        END
                    """ % os.environ['INFLUXDB_DB'])


####################################
# Tot value message processing
####################################
totalizerValueQueue = queue.Queue()


def totalizerValueWorker():
    while True:
        item = totalizerValueQueue.get()
        if item is None:
            break
        onTotalizerValueWork(item)
        totalizerValueQueue.task_done()


def onTotalizerValueWork(msg):
    try:
        value = utils.parseFloat(msg.payload)
        tags = utils.selectTags(msg.topic)
    except:
        logger.error(
            f'The message: "{msg.payload}" cannot be processed. Topic: "{msg.topic}" is malformed. Ignoring data')
        return

    try:
        fields = {tags["endpoint"]: value}
        tagsToSave = ["locationId", "sensorId"]
        measurement = "totalizerData"
        influxDb.writeData(measurement, utils.selectTags(
            tagsToSave, tags), fields, retentionPolicy="raw")
    except:
        logger.error(
            f'onTotalizerValueWork message failed. message: {msg.payload}. Exception: ', exc_info=True)


for i in range(onTotalizerValueNumWorkerThreads):
    t = Thread(target=totalizerValueWorker)
    t.start()
    threads.append(t)


def onTotalizerValue(client, userdata, msg):
    totalizerValueQueue.put(msg)
