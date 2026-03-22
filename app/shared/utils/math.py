from math import floor


def round_down(value: float, step: float) -> float:
    if step <= 0:
        return value
    return floor(value / step) * step
