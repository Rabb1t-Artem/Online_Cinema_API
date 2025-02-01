from decimal import Decimal
from typing import Optional

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


class OrderWithMoviesResponseSchema(BaseModel):
    id: int
    user_id: int
    created_at: str
    status: str
    total_amount: Decimal
    movies: List[str]  # Тут буде список назв фільмів

    model_config = {"from_attributes": True}


class OrderListResponseSchema(BaseModel):
    orders: List[OrderWithMoviesResponseSchema]
    prev_page: Optional[str]
    next_page: Optional[str]
    total_pages: int
    total_items: int

    model_config = {
        "from_attributes": True,
    }
