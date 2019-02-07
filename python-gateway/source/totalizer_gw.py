import logging
import logging.config
import os

import utils

logger = logging.getLogger(__name__)

##################
# Global values
##################
influxDb = None

# MQTT constants
version = 'v1'
topicHeader= "{version}/+/+/+/aux/".format(version=version)
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


    influxClient.client.query(""" CREATE CONTINUOUS QUERY "totalizer_rate" ON %s BEGIN
                        SELECT NON_NEGATIVE_DERIVATIVE(LAST("totalizer"), 1h) as rate
                        INTO "raw"."totalizerData"
                        FROM "raw"."totalizerData"
                        GROUP BY time(3m), *
                        END
                    """ % os.environ['INFLUXDB_DB'])

def onTotalizerValue(client, userdata, msg):
    try:
        value = utils.parseFloat(msg.payload)
        tags, endpoint = utils.decodeTopic(msg.topic)
    except:
        logger.error('The message: "%s" cannot be processed. Topic: "%s" is malformed. Ignoring data' % (msg.payload, msg.topic))
        return

    fields = {endpoint: value}
    measurement = "totalizerData"
    influxDb.writeData(measurement, tags, fields, retentionPolicy="raw")
