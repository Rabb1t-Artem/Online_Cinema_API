from decimal import Decimal

from pydantic import BaseModel
from typing import List


class OrderItemResponseSchema(BaseModel):
    movie_id: int
    price_at_order: Decimal

    class Config:
        orm_mode = True

class OrderResponseSchema(BaseModel):
    id: int
    user_id: int
    created_at: str
    status: str
    total_amount: Decimal
    items: List[OrderItemResponseSchema]

    class Config:
        orm_mode = True
