def saveReference(influxDb, tags, reference):

    fields = {"reference": reference}
    measurement = "thermostatData"
    influxDb.writeData(measurement, tags, fields)

def saveSetpoint(influxDb, tags, setpoint):

    fields = {"setpoint": setpoint}
    measurement = "thermostatData"
    influxDb.writeData(measurement, tags, fields)

def saveHeatingState(influxDb, tags, heating):

    fields = {"heating": heating}
    measurement = "thermostatData"
    influxDb.writeData(measurement, tags, fields)