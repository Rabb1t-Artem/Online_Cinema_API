from pydantic import ConfigDict
from typing import List, Optional

from schemas.custom_base_model import CustomBaseModel


class GenreSchema(CustomBaseModel):
    id: int
    name: str


class GenreCreateSchema(CustomBaseModel):
    name: str


class GenreUpdateSchema(CustomBaseModel):
    name: Optional[str] = None


class GenreListResponseSchema(CustomBaseModel):
    genres: List[GenreSchema]
    prev_page: Optional[str]
    next_page: Optional[str]
    total_pages: int
    total_items: int


class GenreDetailSchema(CustomBaseModel):
    id: int
    name: str
    movie_count: int


class GenreCountSchema(CustomBaseModel):
    genre_name: str
    movie_count: int
