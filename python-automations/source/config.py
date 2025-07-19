"""
Configuration constants for home automation system
"""

# Light sensor thresholds
OFFICE_DARK_THRESHOLD = 2.5
OFFICE_VERY_BRIGHT_THRESHOLD = 8.0
LIVING_ROOM_DARK_THRESHOLD = 1.5
BEDROOM_DARK_THRESHOLD = 2.5
TERUEL_DARK_THRESHOLD = 2.5

# Time intervals (in seconds)
ALARM_PRESENCE_CHECK_TIMEOUT = 180  # 3 minutes
ALARM_DOOR_DELAY = 180  # 3 minutes
ALARM_EMPTY_HOUSE_DELAY = 300  # 5 minutes
ALARM_AUTO_ARM_DELAY = 36000  # 10 hours

# Clock brightness settings
CLOCK_MIN_BRIGHTNESS = 0.03
CLOCK_MAX_BRIGHTNESS = 0.7
CLOCK_BRIGHTNESS_SCALE = 1000

# Light control delays (in seconds)
FLOW_CONTROL_DEFAULT_DELAY = 10
FLOW_CONTROL_LIVING_ROOM_DELAY = 8

# Vacuum states that prevent alarm arming
VACUUM_ACTIVE_STATES = [
    "Returning home",
    "Cleaning",
    "Zoned cleaning",
    "Going to target",
]

KNOWN_HOSTNAMES = [
    "Pixel-8.lan",
    "iPhonedePierina.lan",
]
