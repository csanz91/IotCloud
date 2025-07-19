from devices_types import Switch, DigitalSensor

class Zone:
    def __init__(self, name: str, lights: list[Switch], presence_sensors: list[DigitalSensor]):
        self.name = name
        self.lights = lights
        self.presence_sensors = presence_sensors

    def is_presence_detected(self) -> bool:
        """Check if any presence sensor in the zone is active."""
        return any(sensor.state for sensor in self.presence_sensors)
