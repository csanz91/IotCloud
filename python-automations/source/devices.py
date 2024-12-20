from mqtt_setup import mqttclient
from events import EventStream
from docker_secrets import getDocketSecrets
import devices_types

# Create devices list to track all devices that need subscriptions
all_devices = []

activate_living_room_stream = EventStream("Activate Living Room")
activate_central_light_stream = EventStream("Activate Central Light")
deactivate_living_room_stream = EventStream("Deactivate Living Room")
clock_brightness_stream = EventStream("Clock Brightness")
door_activation_stream = EventStream("Door Activation")
occupancy_stream_in = EventStream("Occupancy In")
occupancy_stream = EventStream("Occupancy")
control_office_light_stream = EventStream("Control Office Light")

# Device creation
living_room_light = devices_types.Switch(
    "Living Room Light",
    "v1/5ca4784d931b1502f377c92d/e7c11470597011e99689411d0bd5e2e4/b4e62d55-444c_switch",
    mqttclient,
    event_streams=[occupancy_stream_in, activate_central_light_stream],
)
all_devices.append(living_room_light)

light_sensor = devices_types.AnalogSensor(
    "Light Sensor",
    "v1/5ca4784d931b1502f377c92d/505635d0b2fa11efb78f611decd54098/bcddc224-879f_003_L/value",
    mqttclient,
    event_streams=[
        activate_living_room_stream,
        clock_brightness_stream,
    ],
)
all_devices.append(light_sensor)

living_room_presence = devices_types.DigitalSensor(
    "Living Room Presence Corner",
    "v1/5ca4784d931b1502f377c92d/505635d0b2fa11efb78f611decd54098/bcddc224-879f_002_S/aux/presence",
    mqttclient,
    event_streams=[
        activate_living_room_stream,
        activate_central_light_stream,
        deactivate_living_room_stream,
        clock_brightness_stream,
        occupancy_stream_in,
    ],
)
all_devices.append(living_room_presence)

living_room_center_light = devices_types.Switch(
    "Living Room Center Light",
    "v1/5ca4784d931b1502f377c92d/42f79360bd4111efafb993c0c03a9994/2cf4327a-732c_Switch",
    mqttclient,
    event_streams=[occupancy_stream_in],
)
all_devices.append(living_room_center_light)

living_room_presence_center = devices_types.DigitalSensor(
    "Living Room Presence Center",
    "v1/5ca4784d931b1502f377c92d/42f79360bd4111efafb993c0c03a9994/2cf4327a-732c_Switch/aux/presence",
    mqttclient,
    event_streams=[
        activate_central_light_stream,
        deactivate_living_room_stream,
        occupancy_stream_in,
    ],
)
all_devices.append(living_room_presence_center)

office_presence = devices_types.DigitalSensor(
    "Office Presence",
    "v1/5ca4784d931b1502f377c92d/e9261190bebc11efb5c3d5853ddfd4d6/2cf43279-f068_002_S/aux/presence",
    mqttclient,
    event_streams=[occupancy_stream_in, control_office_light_stream],
)
all_devices.append(office_presence)

door_sensor = devices_types.NotifierSensor(
    "Door Sensor",
    "v1/5ca4784d931b1502f377c92d/43246d90b0a411ee890291fa48babfc8/4cebd6f7-28d8_001_N/aux/notification",
    mqttclient,
    event_streams=[door_activation_stream],
)
all_devices.append(door_sensor)

bedroom_light = devices_types.Switch(
    "Bedroom Light",
    "v1/5ca4784d931b1502f377c92d/a7292150597011e9fbcd91b8845423f9/b4e62d55-4dfc_switch",
    mqttclient,
    event_streams=[deactivate_living_room_stream, occupancy_stream_in],
)
all_devices.append(bedroom_light)

office_light = devices_types.Switch(
    "Office Light",
    "v1/5ca4784d931b1502f377c92d/47d2dfd05a9211ecbcd4f1054dad6805/d8f15bc6-5b5c_SonoffMini",
    mqttclient,
    event_streams=[occupancy_stream_in],
)
all_devices.append(office_light)

office_light_brightness = devices_types.AnalogSensor(
    "Office Light Brightness",
    "v1/5ca4784d931b1502f377c92d/e9261190bebc11efb5c3d5853ddfd4d6/2cf43279-f068_003_L/value",
    mqttclient,
    event_streams=[control_office_light_stream],
)
all_devices.append(office_light_brightness)

bathroom_light = devices_types.Switch(
    "Bathroom Light",
    "v1/5ca4784d931b1502f377c92d/b3b95b20b49511ee8374bbb5750c2833/2cf43214-6d41_BathroomLight",
    mqttclient,
    event_streams=[deactivate_living_room_stream, occupancy_stream_in],
)
all_devices.append(bathroom_light)

kitchen_light = devices_types.Switch(
    "Kitchen Light",
    "v1/5ca4784d931b1502f377c92d/bdff5490b78311eea32dc905b74984d4/807d3a32-e1a5_KitchenLight",
    mqttclient,
    event_streams=[deactivate_living_room_stream, occupancy_stream_in],
)
all_devices.append(kitchen_light)

clock = devices_types.Clock(
    "Clock",
    "v1/5ca4784d931b1502f377c92d/92339c90259a11eca7bcf303922fb2ff/2cf43251-230e_001/aux/setBrightness",
    mqttclient,
)

notifier = devices_types.NotifierSensor(
    "Notifier",
    "v1/5ca4784d931b1502f377c92d/505635d0b2fa11efb78f611decd54098/bcddc224-879f_001_N/aux/notification",
    mqttclient,
)

pihole_url = getDocketSecrets("pihole_url")
api_token = getDocketSecrets("api_token")
pihole_client = devices_types.PiholeAPIClient(pihole_url, api_token)

cesar_presence = devices_types.Presence("Cesar Presence", "Pixel-8.lan", pihole_client)
pieri_presence = devices_types.Presence(
    "Pieri Presence", "iPhonedePierina.lan", pihole_client
)
