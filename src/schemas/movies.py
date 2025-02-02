from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field, field_validator

from schemas.genres import GenreSchema
from schemas.stars import StarSchema


class DirectorSchema(BaseModel):
    id: int
    name: str

    model_config = {
        "from_attributes": True,
    }


class CertificationSchema(BaseModel):
    id: int
    name: str

    model_config = {
        "from_attributes": True,
    }


class MovieBaseSchema(BaseModel):
    name: str = Field(..., max_length=255)
    year: int
    time: int = Field(..., ge=0)
    imdb: float = Field(..., ge=0, le=100)
    votes: int = Field(..., ge=0)
    meta_score: float | None = Field(None, ge=0)
    gross: float | None = Field(None, ge=0)
    description: str
    price: float = Field(..., ge=0)

    model_config = {"from_attributes": True}

    @field_validator("year")
    def validate_year(cls, value):
        current_year = datetime.now().year
        if value > current_year + 1:
            raise ValueError(f"The year cannot be greater than {current_year + 1}.")
        return value


class MovieDetailSchema(MovieBaseSchema):
    id: int
    directors: DirectorSchema
    genres: List[GenreSchema]
    stars: List[StarSchema]
    certification: CertificationSchema

    model_config = {
        "from_attributes": True,
    }


class MovieListItemSchema(BaseModel):
    id: int
    name: str = Field(..., max_length=255)
    year: int
    time: int = Field(..., ge=0)
    imdb: float = Field(..., ge=0, le=100)

    model_config = {
        "from_attributes": True,
    }


class MovieListResponseSchema(BaseModel):
    movies: List[MovieListItemSchema]
    prev_page: Optional[str]
    next_page: Optional[str]
    total_pages: int
    total_items: int

    model_config = {
        "from_attributes": True,
    }


class MovieCreateSchema(BaseModel):
    name: str = Field(..., max_length=255)
    year: int
    time: int = Field(..., ge=0)
    imdb: float = Field(..., ge=0, le=100)
    votes: int = Field(..., ge=0)
    meta_score: Optional[float] = Field(..., ge=0)
    gross: Optional[float] = Field(..., ge=0)
    description: str
    price: float = Field(..., ge=0)
    directors: DirectorSchema
    genres: List[GenreSchema]
    stars: List[StarSchema]
    certification: CertificationSchema

    model_config = {
        "from_attributes": True,
    }


class MovieUpdateSchema(BaseModel):
    name: str | None = Field(None, max_length=255)
    year: int | None = None
    time: int | None = Field(None, ge=0)
    imdb: float | None = Field(None, ge=0, le=100)
    votes: int  | None  = Field(None, ge=0)
    meta_score: float | None = Field(None, ge=0)
    gross: float | None = Field(None, ge=0)
    description: str | None = None
    price: float | None = Field(None, ge=0)

    model_config = {
        "from_attributes": True,
    }


class MovieLikeSchema(BaseModel):
    movie_id: int
    is_liked: bool = False

    model_config = {
        "from_attributes": True,
    }


class MovieCommentCreateSchema(BaseModel):
    content: str

    model_config = {
        "from_attributes": True,
    }


class MovieCommentSchema(MovieCommentCreateSchema):
    id: int
    user_id: int
    created_at: datetime

    model_config = {
        "from_attributes": True,
    }


class FavoriteMovieSchema(BaseModel):
    user_id: int
    movie_id: int

    model_config = {
        "from_attributes": True,
    }


class FavoriteMovieResponseSchema(BaseModel):
    message: str

    model_config = {
        "from_attributes": True,
    }


class FavoriteMovieListSchema(BaseModel):
    movies: List[MovieDetailSchema]

    model_config = {
        "from_attributes": True,
    }


class NotificationSchema(BaseModel):
    id: int
    user_id: int
    message: str
    is_read: bool
    created_at: datetime

    model_config = {
        "from_attributes": True,
    }
