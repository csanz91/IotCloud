def decodeBoolean(value):
    assert value.lower() in ["true", "false"]
    state = value.lower()=="true"
    return state

def decodeStatus(value):
    assert value.lower() in ["online", "offline"]
    status = value.lower()=="online"
    return status