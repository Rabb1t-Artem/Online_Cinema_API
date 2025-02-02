from decimal import Decimal
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from enum import Enum

class PaymentStatusEnum(str, Enum):
    successful = "successful"
    canceled = "canceled"
    refunded = "refunded"

class PaymentItem(BaseModel):
    id: int
    payment_id: int
    order_item_id: int
    price_at_payment: Decimal

    class Config:
        orm_mode = True

class Payment(BaseModel):
    id: int
    user_id: int
    order_id: int
    created_at: datetime
    status: PaymentStatusEnum
    amount: Decimal
    external_payment_id: Optional[str]
    payment_method: Optional[str]
    client_secret: Optional[str]
    payment_items: List[PaymentItem]

    class Config:
        orm_mode = True
