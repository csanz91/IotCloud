import logging
import logging.config
import time

logger = logging.getLogger()

class Timer(object):
    def __init__(self):
        self.timerRunning = False

    def runTimer(self, mqttclient):

        try:
            initialTimestamp = self.metadata['timer']['initialTimestamp']
            duration = self.metadata['timer']['duration']
        except KeyError:
            logger.error(f"initialTimestamp not found in metadata. Metadata: {self.metadata}")
            return

        currentTimestamp = int(time.time())
        
        # If the timer is activated
        if currentTimestamp < initialTimestamp + duration:
            # If the schedule wasnt active
            if not self.timerRunning:
                self.timerRunning = True
                self.setState(mqttclient, True)

        # If the timer is not active anymore, shut it down
        elif self.timerRunning:
            self.timerRunning = False
            self.setState(mqttclient, False)
        