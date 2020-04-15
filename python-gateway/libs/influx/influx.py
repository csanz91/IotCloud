from influxdb import InfluxDBClient, exceptions
import logging
import time
from threading import Thread, Event
from collections import defaultdict
import atexit
import signal
import queue

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
        
        self.dataBucket = defaultdict(queue.Queue)
        self.dataPackedQueue = queue.Queue()

        # Make sure the instance is always properly closed and no data is lose
        atexit.register(self.close)
        try:
            signal.signal(signal.SIGTERM, self.close)
        except ValueError:
            pass

        self.endEvent = Event()

        self.bucketThread = Thread(target=self.prepareSendBatch)
        self.bucketThread.daemon = True
        self.bucketThread.start()

        self.dataSendNumThreads = 2
        self.dataSendThreads = []
        for numThread in range(self.dataSendNumThreads):
            t = Thread(target=self.sendData)
            t.daemon = True
            t.start()
            self.dataSendThreads.append(t)


    def connect(self):
        self.client = InfluxDBClient(**self.connectionCredentials)

    def writeData(self, measurement, tags, fields, measureTime=None, retentionPolicy=None):

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
            measureTime = int(time.time()*1000000)
        body["time"] = measureTime

        self.dataBucket[retentionPolicy].put(body)


    def getBucketLen(self):
        dataBucketLen = 0
        for bucket in self.dataBucket.values():
            dataBucketLen += bucket.qsize()

        return dataBucketLen


    def prepareSendBatch(self):

        dataChunk = 5000
        sleepTime = 5

        while not self.endEvent.isSet() or self.getBucketLen():

            # Sleep for some time and listen for the end event
            for _ in range(sleepTime):
                if self.endEvent.isSet():
                    break
                time.sleep(1)

            for retentionPolicy, dataQueue in self.dataBucket.items():
                bucketEmpty = False
                while not bucketEmpty:
                    dataToSend = []
                    for numOfItemsRetrieved in range(dataChunk):
                        try:
                            dataToSend.append(dataQueue.get(False))
                        except queue.Empty:
                            bucketEmpty = True
                            break

                    if not dataToSend:
                        break

                    self.dataPackedQueue.put((dataToSend, retentionPolicy))
                    logger.debug(f"Added new package of {len(dataToSend)} values")


        for _ in range(self.dataSendNumThreads):
            self.dataPackedQueue.put(None)
                

    def sendData(self):

        client = InfluxDBClient(**self.connectionCredentials)

        while True:

            d = self.dataPackedQueue.get()
            if d is None:
                break
            dataToSend, rp = d

            logger.debug(f"Sending {len(dataToSend)} values")

            try:
                assert(client.write_points(dataToSend, 
                                                time_precision='u', 
                                                retention_policy=rp,
                                                batch_size=10000))
            except:
                logger.error("Exception when saving the data", exc_info=True)

                # If the batch fails try to send the values one by one
                for value in dataToSend:
                    try:
                        assert(client.write_points([value],
                                                        time_precision='u', 
                                                        retention_policy=rp))
                    except:
                        logger.error(f"Ignoring value: {value}")

        client.close()



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
        for t in self.dataSendThreads:
            t.join()
        self.client.close()
        logger.info("Influx closed")