from datetime import datetime
from typing import Optional, List

from pydantic import Field, field_validator

from schemas.genres import GenreSchema
from schemas.stars import StarSchema
from schemas.custom_base_model import CustomBaseModel


class DirectorSchema(CustomBaseModel):
    id: int
    name: str


class CertificationSchema(CustomBaseModel):
    id: int
    name: str


class MovieBaseSchema(CustomBaseModel):
    name: str = Field(..., max_length=255)
    year: int
    time: int = Field(..., ge=0)
    imdb: float = Field(..., ge=0, le=100)
    votes: int = Field(..., ge=0)
    meta_score: float | None = Field(None, ge=0)
    gross: float | None = Field(None, ge=0)
    description: str
    price: float = Field(..., ge=0)

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


class MovieListItemSchema(CustomBaseModel):
    id: int
    name: str = Field(..., max_length=255)
    year: int
    time: int = Field(..., ge=0)
    imdb: float = Field(..., ge=0, le=100)


class MovieListResponseSchema(CustomBaseModel):
    movies: List[MovieListItemSchema]
    prev_page: Optional[str]
    next_page: Optional[str]
    total_pages: int
    total_items: int


class MovieCreateSchema(CustomBaseModel):
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


class MovieUpdateSchema(CustomBaseModel):
    name: str | None = Field(None, max_length=255)
    year: int | None = None
    time: int | None = Field(None, ge=0)
    imdb: float | None = Field(None, ge=0, le=100)
    votes: int | None = Field(None, ge=0)
    meta_score: float | None = Field(None, ge=0)
    gross: float | None = Field(None, ge=0)
    description: str | None = None
    price: float | None = Field(None, ge=0)


class MovieLikeSchema(CustomBaseModel):
    movie_id: int
    is_liked: bool = False


class MovieCommentCreateSchema(CustomBaseModel):
    content: str


class MovieCommentSchema(MovieCommentCreateSchema):
    id: int
    user_id: int
    created_at: datetime


class FavoriteMovieSchema(CustomBaseModel):
    user_id: int
    movie_id: int


class FavoriteMovieResponseSchema(CustomBaseModel):
    message: str


class FavoriteMovieListSchema(CustomBaseModel):
    movies: List[MovieDetailSchema]


class NotificationSchema(CustomBaseModel):
    id: int
    user_id: int
    message: str
    is_read: bool
    created_at: datetime
