import logging
import logging.config
import datetime
from dateutil import tz

logger = logging.getLogger()

class Schedule():
    def __init__(self, setState, setValue=lambda a,b: None):
        self.schedule = [[], [], [], [], [], [], []]
        self.scheduleRunning = False
        self.setState = setState
        self.setValue = setValue

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
                    self.setValue(mqttClient, scheduleElement[2])
                return

        # If the schudele is not active anymore, shut it down
        if self.scheduleRunning:
            self.scheduleRunning = False
            self.setState(mqttClient, False)
        