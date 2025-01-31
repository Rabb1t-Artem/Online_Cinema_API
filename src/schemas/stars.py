from pydantic import BaseModel
from typing import List, Optional


class StarSchema(BaseModel):
    id: int
    name: str

    model_config = {
        "from_attributes": True,
    }


class StarCreateSchema(BaseModel):
    name: str

    model_config = {
        "from_attributes": True,
    }


class StarUpdateSchema(BaseModel):
    name: Optional[str] = None

    model_config = {
        "from_attributes": True,
    }


class StarListResponseSchema(BaseModel):
    stars: List[StarSchema]
    prev_page: Optional[str]
    next_page: Optional[str]
    total_pages: int
    total_items: int

    model_config = {
        "from_attributes": True,
    }


class StarDetailSchema(BaseModel):
    id: int
    name: str

    model_config = {
        "from_attributes": True,
    }