from datetime import datetime
from typing import List, Optional

from schemas.custom_base_model import CustomBaseModel
from schemas.movies import MovieBaseSchema


class MovieLikeSchema(CustomBaseModel):
    movie_id: int
    message: str
    is_liked: bool = False


class MovieCommentCreateSchema(CustomBaseModel):
    movie_id: int
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
    movies: List[MovieBaseSchema]


class NotificationSchema(CustomBaseModel):
    id: int
    user_id: int
    message: str
    is_read: bool
    created_at: datetime


class ReplyContentSchema(CustomBaseModel):
    content: str


class RatingResponseSchema(CustomBaseModel):
    message: str


class AverageRatingResponseSchema(CustomBaseModel):
    average_rating: Optional[float] = None
    message: Optional[str] = None
