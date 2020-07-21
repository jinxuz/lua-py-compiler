# type conversion
def convert_to_integer(v):
    if type(v) is int:
        return v, True
    if type(v) is str:
        try:
            v = float(v)
        except (TypeError, ValueError):
            return 0, False
    if type(v) is float:
        if v % 1 == 0:
            return int(v), True
        else:
            return v, False
    return 0, False


def convert_to_float(v):
    if type(v) is float:
        return v, True
    if type(v) is int:
        return float(v), True
    if type(v) is str:
        try:
            v = float(v)
            return v, True
        except (TypeError, ValueError):
            return 0, False
    return 0, True


def convert_to_boolean(v):
    return not (v is None or v is False)