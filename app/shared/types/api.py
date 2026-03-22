from pydantic import BaseModel, Field


class PaperOrderRequest(BaseModel):
    symbol: str
    side: str
    quantity: float = Field(gt=0)
    price: float = Field(gt=0)
    rationale: str = "Manual paper order"
    confidence: float = Field(default=1.0, ge=0, le=1)


class TestOrderRequest(BaseModel):
    symbol: str
    side: str
    quantity: float = Field(gt=0)
    price: float | None = Field(default=None, gt=0)
    order_type: str = "MARKET"


class LiveOrderRequest(BaseModel):
    symbol: str
    side: str
    quantity: float = Field(gt=0)
    price: float | None = Field(default=None, gt=0)
    rationale: str = "Manual live order"
    confidence: float = Field(default=1.0, ge=0, le=1)
    order_type: str = "MARKET"
