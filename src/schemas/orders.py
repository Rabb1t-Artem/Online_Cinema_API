from decimal import Decimal
from typing import Optional

from typing import List

from schemas.custom_base_model import CustomBaseModel


class OrderItemResponseSchema(CustomBaseModel):
    movie_id: int
    price_at_order: Decimal


class OrderResponseSchema(CustomBaseModel):
    id: int
    user_id: int
    created_at: str
    status: str
    total_amount: Decimal
    items: List[OrderItemResponseSchema]


class OrderWithMoviesResponseSchema(CustomBaseModel):
    id: int
    user_id: int
    created_at: str
    status: str
    total_amount: Decimal
    movies: List[str]  # Тут буде список назв фільмів


class OrderListResponseSchema(CustomBaseModel):
    orders: List[OrderWithMoviesResponseSchema]
    prev_page: Optional[str]
    next_page: Optional[str]
    total_pages: int
    total_items: int
