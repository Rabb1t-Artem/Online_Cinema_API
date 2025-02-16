from datetime import date, datetime
from typing import List, Optional

from pydantic import Field, ConfigDict, model_validator

from schemas.custom_base_model import CustomBaseModel


class MovieInCartSchema(CustomBaseModel):
    id: int
    name: str
    genres: List[str]
    price: float = Field(..., ge=0)

    date: Optional[date] = None
    release_year: Optional[int] = None

    @model_validator(mode="after")
    def fill_release_year(self):
        if self.date:
            self.release_year = self.date.year
        return self


class CartItemBaseSchema(CustomBaseModel):
    movie_id: int = Field(..., description="Movie ID")


class CartItemResponseSchema(CustomBaseModel):
    id: int
    cart_id: int
    added_at: datetime
    movie: MovieInCartSchema


class CartCreateSchema(CustomBaseModel):
    user_id: int = Field(..., description="USER ID")


class CartResponseSchema(CustomBaseModel):
    id: int
    user_id: int
    cart_items: List[CartItemResponseSchema]
