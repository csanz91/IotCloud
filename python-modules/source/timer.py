import logging
import logging.config
import time

logger = logging.getLogger()

class Timer():
    def __init__(self, setState):
        self.initialTimestamp = 0
        self.duration = 0
        self.timerRunning = False
        self.setState = setState

    def importSettings(self, timerSettings):
        self.initialTimestamp = timerSettings["initialTimestamp"]
        self.duration = timerSettings["duration"]

    def runTimer(self, mqttClient):
        currentTimestamp = int(time.time())
        
        # If the timer is activated
        if currentTimestamp < self.initialTimestamp + self.duration:
            # If the schedule wasnt active
            if not self.timerRunning:
                self.timerRunning = True
                self.setState(mqttClient, True)

        # If the timer is not active anymore, shut it down
        elif self.timerRunning:
            self.timerRunning = False
            self.setState(mqttClient, False)
        