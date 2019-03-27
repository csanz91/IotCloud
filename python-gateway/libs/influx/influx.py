from influxdb import InfluxDBClient, exceptions
import logging
import time
from threading import Thread, Event
from collections import defaultdict
import atexit
import signal
import Queue

logger = logging.getLogger(__name__)

class InfluxClient():

    def __init__(self, host, username, password, database, ssl=False, timeout=60, port=8086):

        self.connectionCredentials = {'host': host,
                                      'username': username,
                                      'password': password,
                                      'database': database,
                                      'ssl': ssl,
                                      'timeout': timeout,
                                      'port': port,
                                      'verify_ssl': True}

        self.connect()
        
        self.dataBucket = defaultdict(Queue.Queue)

        # Make sure the instance is always properly closed and no data is lose
        atexit.register(self.close)
        try:
            signal.signal(signal.SIGTERM, self.close)
        except ValueError:
            pass

        self.endEvent = Event()

        self.bucketThread = Thread(target=self.emptyBucket)
        self.bucketThread.daemon = True
        self.bucketThread.start()


    def connect(self):
        self.client = InfluxDBClient(**self.connectionCredentials)

    def writeData(self, measurement, tags, fields, measureTime=None, bucketMode=True, retentionPolicy=None):

        if not measurement or not type(tags) is dict or not type(fields) is dict:
            logger.warning("no data to insert. tags: %s. fields: %s" % (tags, fields))
            return

        if not measurement:
            logger.warning("no measurement to insert")
            return  

        body = {
                "measurement": measurement,
                "fields": fields,
                "tags": tags
        }

        if not measureTime:
            measureTime = int(time.time())
        body["time"] = measureTime

        if bucketMode:
            # Wait for the bucket to empty, otherwise memory overload is guaranteed ;)
            while self.getBucketLen() > 100000:
                time.sleep(0.1)

            self.dataBucket[retentionPolicy].put(body)
        else:
            try:
                self.client.write_points([body], time_precision='s', retention_policy=retentionPolicy)
            except KeyboardInterrupt:
                raise KeyboardInterrupt()
            except:
                logger.error("Exception when saving the data.", exc_info=True)
                self.connect()

    def getBucketLen(self):
        dataBucketLen = 0
        for bucket in self.dataBucket.values():
            dataBucketLen += bucket.qsize()

        return dataBucketLen


    def emptyBucket(self):

        dataChunk = 50000
        sleepTime = 10

        while not self.endEvent.isSet() or self.getBucketLen():

            # Sleep for some time and listen for the end event
            for _ in xrange(sleepTime):
                if self.endEvent.isSet() or self.getBucketLen() >= dataChunk:
                    break
                time.sleep(1)

            for retentionPolicy, queue in self.dataBucket.items():

                dataToSend = []
                while not queue.empty() and len(dataToSend)<dataChunk:

                    try:
                        dataToSend.append(queue.get(False))
                    except Queue.Empty:
                        continue

     
                logger.debug("sending %s values" % len(dataToSend))
            
                if dataToSend:
                    try:
                        assert(self.client.write_points(dataToSend, time_precision='s', retention_policy=retentionPolicy))
                    except KeyboardInterrupt:
                        raise KeyboardInterrupt()
                    except:
                        logger.error("Exception when saving the data", exc_info=True)

                        # If the batch fails try to send the values one by one
                        for value in dataToSend:
                            try:
                                assert(self.client.write_points([value], time_precision='s', retention_policy=retentionPolicy))
                            except:
                                logger.error("Ignoring value: %s" % value)



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
        self.endEvent.set()
        self.bucketThread.join()
        self.client.close()
        logger.info("Influx closed")