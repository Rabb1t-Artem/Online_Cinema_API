from pydantic import ConfigDict
from typing import List, Optional

from schemas.custom_base_model import CustomBaseModel


class StarSchema(CustomBaseModel):
    id: int
    name: str


class StarCreateSchema(CustomBaseModel):
    name: str


class StarUpdateSchema(CustomBaseModel):
    name: Optional[str] = None


class StarListResponseSchema(CustomBaseModel):
    stars: List[StarSchema]
    prev_page: Optional[str]
    next_page: Optional[str]
    total_pages: int
    total_items: int


class StarDetailSchema(CustomBaseModel):
    id: int
    name: str
