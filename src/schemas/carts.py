from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict, model_validator


class MovieInCartSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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


class CartItemBaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    movie_id: int = Field(..., description="Movie ID")


class CartItemResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cart_id: int
    added_at: datetime
    movie: MovieInCartSchema


class CartCreateSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int = Field(..., description="USER ID")


class CartResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    cart_items: List[CartItemResponseSchema]
