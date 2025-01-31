from pydantic import BaseModel
from typing import List, Optional

class GenreSchema(BaseModel):
    id: int
    name: str

    model_config = {
        "from_attributes": True,
    }


class GenreCreateSchema(BaseModel):
    name: str

    model_config = {
        "from_attributes": True,
    }


class GenreUpdateSchema(BaseModel):
    name: Optional[str] = None

    model_config = {
        "from_attributes": True,
    }


class GenreListResponseSchema(BaseModel):
    genres: List[GenreSchema]
    prev_page: Optional[str]
    next_page: Optional[str]
    total_pages: int
    total_items: int

    model_config = {
        "from_attributes": True,
    }


class GenreDetailSchema(BaseModel):
    id: int
    name: str

    model_config = {
        "from_attributes": True,
    }