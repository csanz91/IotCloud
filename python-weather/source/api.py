import logging
import logging.config

import falcon

import weather_api

# Logging setup
logger = logging.getLogger()
handler = logging.handlers.RotatingFileHandler('../logs/weather.log', mode='a', maxBytes=1024*1024*10, backupCount=2)
formatter = logging.Formatter('%(asctime)s <%(levelname).1s> %(funcName)s:%(lineno)s: %(message)s')
logger.setLevel(logging.INFO)
handler.setFormatter(formatter)
logger.addHandler(handler)

app = falcon.App()
app.req_options.auto_parse_form_urlencoded = True

app.add_route("/api/postalcode/{postalCode}/weather", weather_api.Weather())
app.add_route("/api/postalcode/{postalCode}/sunschedule", weather_api.SunSchedule())
app.add_route("/api/postalcode/{postalCode}/timezone", weather_api.TimeZone())
app.add_route("/api/postalcode/{postalCode}/alerts", weather_api.LatestsWeatherAlerts())
app.add_route("/api/postalcode/{postalCode}/geocode", weather_api.Geocode())