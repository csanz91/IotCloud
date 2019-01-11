import logging
import logging.config
import time
import datetime
from dateutil import tz

import gateway

logger = logging.getLogger()

# Thermostats variables
thermostats = {}
thermostatsValues = {}

class Thermostat():
    def __init__(self, tags, mqttClient):

        # Aux variables
        self.tags = tags
        self.topicHeader = "{version}/{locationId}/{deviceId}/{sensorId}/".format(version=tags['version'],
                                                                                  locationId=tags['locationId'],
                                                                                  deviceId=tags['deviceId'],
                                                                                  sensorId=tags['sensorId'])

        # Runtime variables
        self.temperatureReferences = {}
        self.heating = False
        self.alarm = False
        self.state = False
        self.schedule = [[], [], [], [], [], [], []]
        self.scheduleRunning = False

        # Default settings
        self.startHeatingAt = int(time.time())
        self.setpoint = 0.0
        self.hysteresisHigh = -0.1
        self.hysteresisLow = -0.8
        self.maxHeatingTime = 3600 * 8 # 8 hours

        # Subscribe to the relevant topics
        self.addTempReference(mqttClient, self.topicHeader+"value", 2)
        mqttClient.subscribe(self.topicHeader+"state")
        mqttClient.subscribe(self.topicHeader+"updatedSensor")

    def addTempReference(self, mqttClient, temperatureReferenceTopic, factor):
        if not temperatureReferenceTopic in self.temperatureReferences:
            mqttClient.subscribe(temperatureReferenceTopic)
        self.temperatureReferences[temperatureReferenceTopic] = factor

    def updateSettings(self, mqttClient, metadata):
        try:
            self.hysteresisHigh = float(metadata['hysteresisHigh'])
            logger.info("hysteresisHigh updated: %s" % self.hysteresisHigh)
        except:
            pass

        try:
            self.hysteresisLow = float(metadata['hysteresisLow'])
            logger.info("hysteresisLow updated: %s" % self.hysteresisLow)
        except:
            pass

        try:
            self.maxHeatingTime = int(metadata['maxHeatingTime'])
            logger.info("maxHeatingTime updated: %s" % self.maxHeatingTime)
        except:
            pass

        try:
            self.schedule = metadata['schedule']
            logger.info("schedule updated: %s" % self.schedule)
        except:
            pass

        try:
            logger.info(metadata['temperatureReferences'])
            for temperatureReferenceTopic, factor in metadata['temperatureReferences'].items():
                self.addTempReference(mqttClient, temperatureReferenceTopic, factor)
                logger.info("temperature references updated: %s" % temperatureReferenceTopic)
        except:
            logger.error("Excepcion: ", exc_info=True)
            pass

    def calculateTempReference(self):
        tempReference = 0.0
        factorsSum = 0.0
        for temperatureReferenceTopic, factor in self.temperatureReferences.items():
            try:
                temperature = thermostatsValues[temperatureReferenceTopic]
                # If the temperature value was received more than 15 minutes ago, discard it
                if temperature['timestamp']+60*15 < int(time.time()):
                    logger.warn("Expired temperature value from the topic: %s" % temperatureReferenceTopic)
                    continue
                factorsSum += factor
                tempReference += temperature['value']*factor
            # The sensor was not found
            except KeyError:
                logger.warning("Temperature value from the topic: %s not available" % temperatureReferenceTopic)
        if tempReference and factorsSum:
            tempReference = tempReference / factorsSum

        return tempReference

    def setHeating(self, mqttClient, heating):
        self.heating = heating
        mqttClient.publish(self.topicHeader+"aux/setHeating", heating, qos=1, retain=True)

    def setAlarm(self, mqttClient, alarm):
        self.alarm = alarm
        mqttClient.publish(self.topicHeader+"aux/alarm", alarm, qos=1, retain=True)

    def setState(self, mqttClient, state):
        mqttClient.publish(self.topicHeader+"setState", state, qos=1, retain=True)

    def setSetpoint(self, mqttClient, setpoint):
        mqttClient.publish(self.topicHeader+"aux/setpoint", setpoint, qos=1, retain=True)

    def runSchedule(self, mqttClient):
        now = datetime.datetime.today()
        localZone = tz.gettz("Europe/Madrid")
        nowAware = now.replace(tzinfo=tz.UTC)
        nowNaive = nowAware.astimezone(localZone)
        today = nowNaive.weekday() # Mon: 0, Sun: 6
        currentMinute = nowNaive.hour * 60 + nowNaive.minute
        
        todaySchedule = self.schedule[today]
        logger.info("currentMinute: %s, todaySchedule: %s" % (currentMinute, todaySchedule))
        for scheduleElement in todaySchedule:
            # If schedule is activated
            if currentMinute >= scheduleElement[0] and currentMinute < scheduleElement[0] + scheduleElement[1]:
                # If the schedule wasnt active
                if not self.scheduleRunning:
                    self.scheduleRunning = True
                    self.setState(mqttClient, True)
                    self.setSetpoint(mqttClient, scheduleElement[2])
                return

        # If the schudele is not active anymore, shut it down
        if self.scheduleRunning:
            self.scheduleRunning = False
            self.setState(mqttClient, False)

    def engine(self, mqttClient, influxDb):

        # Check the schedule
        self.runSchedule(mqttClient)

        # The thermostat cannot run if there is an alarm active or if it is not active
        if self.alarm or not self.state:
            logger.debug("Thermostat: %s not running because is stopped or an alarm is set" % self.topicHeader)
            # If it was heating stop now. The device also evaluates this condition
            if self.heating:
                self.setHeating(mqttClient, False)
            return

        tempReference = self.calculateTempReference()
        logger.info("tempReference: %s, setpoint: %s" % (tempReference, self.setpoint))

        # These values are needed to be able to run the algorithm
        if not tempReference or not self.setpoint:
            logger.warning("Some of the core values are not valid. tempReference: %s, setpoint: %s" % (tempReference, self.setpoint))
            return

        gateway.saveReference(influxDb, self.tags, tempReference)

        # If the heating has been running for more than [maxHeatingTime] there could be
        # something wrong. Trigger the alarm to protect the instalation.
        if self.heating and self.startHeatingAt+self.maxHeatingTime < int(time.time()):
            logger.warning("Heating running for more than %s seconds. Triggering alarm" % self.maxHeatingTime)
            self.setHeating(mqttClient, False)
            self.setAlarm(mqttClient, True)
            return
        
        # The reference temperature is below the setpoint -> start heating
        if not self.heating and tempReference < self.setpoint+self.hysteresisLow:
            self.setHeating(mqttClient, True)
            self.startHeatingAt = int(time.time())
            logger.info("Start heating")
        # The reference temperature is above the setpoint -> stop heating
        elif self.heating and tempReference > self.setpoint+self.hysteresisHigh:
            self.setHeating(mqttClient, False)
            logger.info("Stop heating")