def simple_moving_average(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    subset = values[-period:]
    return sum(subset) / period


def momentum(values: list[float], period: int) -> float | None:
    if len(values) < period + 1:
        return None
    previous = values[-(period + 1)]
    current = values[-1]
    if previous == 0:
        return None
    return ((current - previous) / previous) * 100


def volatility(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    subset = values[-period:]
    average = sum(subset) / len(subset)
    variance = sum((item - average) ** 2 for item in subset) / len(subset)
    return variance ** 0.5


def rsi(values: list[float], period: int = 14) -> float | None:
    if len(values) < period + 1:
        return None

    gains = []
    losses = []
    for index in range(-period, 0):
        delta = values[index] - values[index - 1]
        gains.append(max(delta, 0))
        losses.append(abs(min(delta, 0)))

    average_gain = sum(gains) / period
    average_loss = sum(losses) / period

    if average_loss == 0:
        return 100.0

    rs = average_gain / average_loss
    return 100 - (100 / (1 + rs))
