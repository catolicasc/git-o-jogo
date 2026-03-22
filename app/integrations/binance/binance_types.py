from pydantic import BaseModel


class BinanceSymbolRules(BaseModel):
    min_qty: float
    max_qty: float
    step_size: float
    min_notional: float
    tick_size: float | None = None


class PreparedOrderPayload(BaseModel):
    symbol: str
    side: str
    type: str
    quantity: str
    price: str | None = None
    timeInForce: str | None = None
    recvWindow: int = 5000
    timestamp: int
    newOrderRespType: str = "FULL"
