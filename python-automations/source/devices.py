import devices_types
from docker_secrets import get_docker_secrets
from events import EventStream
from mqtt_setup import mqttclient
from zones import Zone

# Create devices list to track all devices that need subscriptions
all_devices = []

activate_living_room_stream = EventStream("Activate Living Room")
activate_bathroom_stream = EventStream("Activate Bathroom")
activate_kitchen_stream = EventStream("Activate Kitchen")
activate_central_light_stream = EventStream("Activate Central Light")
deactivate_living_room_stream = EventStream("Deactivate Living Room")
clock_brightness_stream = EventStream("Clock Brightness")
door_activation_stream = EventStream("Door Activation")
occupancy_stream_in = EventStream("Occupancy In")
occupancy_stream = EventStream("Occupancy")
control_office_light_stream = EventStream("Control Office Light")
bedroom_light_stream = EventStream("Control Bedroom Light")
flow_control_stream = EventStream("Control Flow")
alarm_armed_stream = EventStream("Alarm Armed")
bed_brightness_stream = EventStream("Bedroom Brightness")
teruel_presence_stream = EventStream("Teruel Presence")
teruel_puerta_abajo_stream = EventStream("Teruel Puerta Abajo")
teruel_puerta_arriba_stream = EventStream("Teruel Puerta Arriba")
camera_alarm_stream = EventStream("Camera Alarm")

# Device creation
living_room_light = devices_types.Switch(
    "Living Room Light",
    "v1/5ca4784d931b1502f377c92d/e7c11470597011e99689411d0bd5e2e4/b4e62d55-444c_switch",
    mqtt_client=mqttclient,
    event_streams=[
        occupancy_stream_in,
        activate_central_light_stream,
        flow_control_stream,
    ],
)
all_devices.append(living_room_light)

light_sensor = devices_types.AnalogSensor(
    "Light Sensor",
    "v1/5ca4784d931b1502f377c92d/505635d0b2fa11efb78f611decd54098/bcddc224-879f_003_L/value",
    mqttclient,
    event_streams=[
        activate_living_room_stream,
        clock_brightness_stream,
        control_office_light_stream,
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
        flow_control_stream,
    ],
)
all_devices.append(living_room_presence)

living_room_center_light = devices_types.Switch(
    "Living Room Center Light",
    "v1/5ca4784d931b1502f377c92d/42f79360bd4111efafb993c0c03a9994/2cf4327a-732c_Switch",
    mqttclient,
    event_streams=[occupancy_stream_in, flow_control_stream],
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
        control_office_light_stream,
        flow_control_stream,
        activate_bathroom_stream,
        activate_kitchen_stream,
        activate_living_room_stream,
    ],
)
all_devices.append(living_room_presence_center)

office_presence = devices_types.DigitalSensor(
    "Office Presence",
    "v1/5ca4784d931b1502f377c92d/e9261190bebc11efb5c3d5853ddfd4d6/2cf43279-f068_002_S/state",
    mqttclient,
    event_streams=[
        occupancy_stream_in,
        control_office_light_stream,
        flow_control_stream,
        activate_bathroom_stream,
        deactivate_living_room_stream,
    ],
)
all_devices.append(office_presence)

bedroom_presence = devices_types.DigitalSensor(
    "Bedroom Presence",
    "v1/5ca4784d931b1502f377c92d/21a5dc40c9bb11efa617b1415820b92f/fc00803d-fc3f_Presence/state",
    mqttclient,
    event_streams=[
        occupancy_stream_in,
        bedroom_light_stream,
        control_office_light_stream,
        activate_bathroom_stream,
        deactivate_living_room_stream,
    ],
)
all_devices.append(bedroom_presence)

door_sensor = devices_types.NotifierSensor(
    "Door Sensor",
    "v1/5ca4784d931b1502f377c92d/43246d90b0a411ee890291fa48babfc8/4cebd6f7-28d8_001_N/aux/notification",
    mqttclient,
    event_streams=[door_activation_stream],
)
all_devices.append(door_sensor)

bedroom_light = devices_types.Switch(
    "Bedroom Light",
    "v1/5ca4784d931b1502f377c92d/21a5dc40c9bb11efa617b1415820b92f/fc00803d-fc3f_Switch1",
    mqttclient,
    event_streams=[
        occupancy_stream_in,
        flow_control_stream,
    ],
)
all_devices.append(bedroom_light)

office_light = devices_types.Switch(
    "Office Light",
    "v1/5ca4784d931b1502f377c92d/21a5dc40c9bb11efa617b1415820b92f/fc00803d-fc3f_Switch2",
    mqttclient,
    event_streams=[occupancy_stream_in, flow_control_stream],
)
all_devices.append(office_light)

# office_light_brightness = devices_types.AnalogSensor(
#     "Office Light Brightness",
#     "v1/5ca4784d931b1502f377c92d/e9261190bebc11efb5c3d5853ddfd4d6/2cf43279-f068_003_L/value",
#     mqttclient,
#     event_streams=[control_office_light_stream],
# )
# all_devices.append(office_light_brightness)

bathroom_light = devices_types.Switch(
    "Bathroom Light",
    "v1/5ca4784d931b1502f377c92d/916b6e20708a11f09bfeb940134d3a0e/2cf43214-6d41_001_S",
    mqttclient,
    event_streams=[],
)
all_devices.append(bathroom_light)

bathroom_presence = devices_types.DigitalSensor(
    "Bathroom Presence",
    "v1/5ca4784d931b1502f377c92d/916b6e20708a11f09bfeb940134d3a0e/2cf43214-6d41_Presence/state",
    mqttclient,
    event_streams=[
        activate_bathroom_stream,
        occupancy_stream_in,
        control_office_light_stream,
        flow_control_stream,
        deactivate_living_room_stream,
    ],
)
all_devices.append(bathroom_presence)

kitchen_light = devices_types.Switch(
    "Kitchen Light",
    "v1/5ca4784d931b1502f377c92d/dca6b2d0708c11f09bfeb940134d3a0e/807d3a32-e1a5_KitchenLight",
    mqttclient,
    event_streams=[
        occupancy_stream_in,
        flow_control_stream,
    ],
)
all_devices.append(kitchen_light)

kitchen_presence = devices_types.DigitalSensor(
    "Kitchen Presence",
    "v1/5ca4784d931b1502f377c92d/dca6b2d0708c11f09bfeb940134d3a0e/807d3a32-e1a5_KitchenPresence/state",
    mqttclient,
    event_streams=[
        activate_kitchen_stream,
        occupancy_stream_in,
        flow_control_stream,
        deactivate_living_room_stream,
    ],
)
all_devices.append(kitchen_presence)

clock = devices_types.BrightnessDevice(
    "Clock",
    "v1/5ca4784d931b1502f377c92d/92339c90259a11eca7bcf303922fb2ff/2cf43251-230e_001",
    mqttclient,
)

temp_box = devices_types.BrightnessDevice(
    "Temperature Box",
    "v1/5ca4784d931b1502f377c92d/59f5ba00ef5b11ea8dc031f13c3780b7/18fe349d-6861_001_T",
    mqttclient,
)

notifier = devices_types.NotifierSensor(
    "Notifier",
    "v1/5ca4784d931b1502f377c92d/505635d0b2fa11efb78f611decd54098/bcddc224-879f_001_N/aux/notification",
    mqttclient,
)

enable_madrid_automations = devices_types.Switch(
    "Enable Automations",
    "v1/5ca4784d931b1502f377c92d/676d8c301a146aaf5c1acec3/202481596676681_001_Automations",
    mqttclient,
    event_streams=[
        activate_living_room_stream,
        activate_central_light_stream,
        deactivate_living_room_stream,
        activate_bathroom_stream,
        activate_kitchen_stream,
        clock_brightness_stream,
        control_office_light_stream,
    ],
)
all_devices.append(enable_madrid_automations)


alarm_armed = devices_types.Switch(
    "Alarm Armed",
    "v1/5ca4784d931b1502f377c92d/676d8c301a146aaf5c1acec3/202481596676681_002_Automations",
    mqttclient,
    event_streams=[alarm_armed_stream],
)
all_devices.append(alarm_armed)

bedroom_auto = devices_types.Switch(
    "Bedroom Auto",
    "v1/5ca4784d931b1502f377c92d/f6788090cad211ef93d45fb898747fd2/202481596676681_003_Bedroom",
    mqttclient,
    event_streams=[bedroom_light_stream],
)
all_devices.append(bedroom_auto)


home_alone = devices_types.Switch(
    "Home Alone",
    "v1/5ca4784d931b1502f377c92d/85d85b90cd8811efb4047175e3dde3ed/202481596676681_004_HomeAlone",
    mqttclient,
    event_streams=[flow_control_stream],
)
all_devices.append(home_alone)

bed_led = devices_types.BrightnessDevice(
    "Bedroom LED",
    "v1/5ca4784d931b1502f377c92d/1c64c6e0ca6c11ef8c983d3c5d9aede6/202481596676681_002_LED",
    mqttclient,
)
all_devices.append(bed_led)

bed_brightness = devices_types.AnalogSensor(
    "Bedroom Brightness Control",
    "v1/5ca4784d931b1502f377c92d/c26450c0dd4911ef847811885ea8c0f3/40000000-0000_001_E/value",
    mqttclient,
    event_streams=[bed_brightness_stream],
    notify_same_value=True,
)
all_devices.append(bed_brightness)

living_room_api = devices_types.APIOrderDevice(
    "living_room_light_api",
    event_streams=[activate_living_room_stream, clock_brightness_stream],
)
all_devices.append(living_room_api)


# Zones
living_room_zone = Zone(
    "Living Room",
    lights=[living_room_light, living_room_center_light],
    presence_sensors=[living_room_presence, living_room_presence_center],
)

office_zone = Zone("Office", lights=[office_light], presence_sensors=[office_presence])

bedroom_zone = Zone("Bedroom", lights=[bedroom_light], presence_sensors=[bedroom_presence])


all_zones = [living_room_zone, office_zone, bedroom_zone]


pihole_url = get_docker_secrets("pihole_url")
pihole_password = get_docker_secrets("pihole_password")
pihole_client = devices_types.PiholeAPIClient(pihole_url, pihole_password)
