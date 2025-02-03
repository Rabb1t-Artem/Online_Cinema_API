from typing import Optional, List
import uuid

from datetime import datetime, timezone

from sqlalchemy import (
    String,
    Float,
    Text,
    DECIMAL,
    UniqueConstraint,
    ForeignKey,
    Table,
    Column,
    Integer,
    Boolean,
    DateTime,
)
from sqlalchemy.orm import mapped_column, Mapped, relationship
from sqlalchemy import func

from database import Base
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from database.models.orders import OrderItemModel
    from database.models.accounts import UserModel


MoviesGenresModel = Table(
    "movies_genres",
    Base.metadata,
    Column(
        "movie_id",
        ForeignKey("movies.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
    Column(
        "genre_id",
        ForeignKey("genres.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
)

StarsMoviesModel = Table(
    "stars_movies",
    Base.metadata,
    Column(
        "movie_id",
        ForeignKey("movies.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
    Column(
        "star_id",
        ForeignKey("stars.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
)

MoviesDirectorsModel = Table(
    "movies_directors",
    Base.metadata,
    Column("movie_id", ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True),
    Column("director_id", ForeignKey("directors.id", ondelete="CASCADE"), primary_key=True),
)


class GenreModel(Base):
    __tablename__ = "genres"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    movies: Mapped[list["MovieModel"]] = relationship(
        "MovieModel", secondary=MoviesGenresModel, back_populates="genres"
    )

    def __repr__(self):
        return f"<Genre(name='{self.name}')>"


class StarModel(Base):
    __tablename__ = "stars"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    movies: Mapped[list["MovieModel"]] = relationship("MovieModel", secondary=StarsMoviesModel, back_populates="stars")

    def __repr__(self):
        return f"<Star(name='{self.name}')>"


class DirectorModel(Base):
    __tablename__ = "directors"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    movies: Mapped[list["MovieModel"]] = relationship(
        "MovieModel",
        secondary=MoviesDirectorsModel,
        back_populates="directors",
    )

    def __repr__(self):
        return f"<Director(name='{self.name}')>"


class CertificationModel(Base):
    __tablename__ = "certifications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    movies: Mapped[list["MovieModel"]] = relationship(
        "MovieModel",
        back_populates="certification",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Certification(name='{self.name}')>"


class MovieModel(Base):
    __tablename__ = "movies"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    uuid: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    time: Mapped[int] = mapped_column(Integer, nullable=False)
    imdb: Mapped[float] = mapped_column(Float, nullable=False)
    votes: Mapped[int] = mapped_column(Integer, nullable=False)
    meta_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gross: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False)

    certification_id: Mapped[int] = mapped_column(ForeignKey("certifications.id"), nullable=False)
    order_items: Mapped[List["OrderItemModel"]] = relationship("OrderItemModel", back_populates="movie")

    genres: Mapped[list["GenreModel"]] = relationship(
        "GenreModel", secondary=MoviesGenresModel, back_populates="movies"
    )

    stars: Mapped[list["StarModel"]] = relationship("StarModel", secondary=StarsMoviesModel, back_populates="movies")

    directors: Mapped[list["DirectorModel"]] = relationship(
        "DirectorModel", secondary=MoviesDirectorsModel, back_populates="movies"
    )
    likes = relationship("MovieLikeModel", back_populates="movie", cascade="all, delete-orphan")
    comments = relationship("MovieCommentModel", back_populates="movie", cascade="all, delete-orphan")
    ratings: Mapped[List["MovieRatingModel"]] = relationship("MovieRatingModel", back_populates="movie")
    certification: Mapped["CertificationModel"] = relationship(
        "CertificationModel",
        back_populates="movies"
    )
    favorites = relationship("FavoriteMovieModel", back_populates="movie", cascade="all, delete-orphan")
    ratings = relationship("MovieRatingModel", back_populates="movie", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("name", "year", "time", name="unique_movie_constraint"),)

    @property
    def average_rating(self):
        if not self.ratings:
            return None
        return sum(rating.rating for rating in self.ratings) / len(self.ratings)

    @classmethod
    def default_order_by(cls):
        return [cls.id.desc()]

    def __repr__(self):
        return f"<Movie(name='{self.name}', release_year='{self.year}', score={self.imdb})>"


class MovieLikeModel(Base):
    __tablename__ = "movie_likes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    movie_id: Mapped[int] = mapped_column(Integer, ForeignKey("movies.id", ondelete="CASCADE"), nullable=False)
    is_liked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    movie: Mapped["MovieModel"] = relationship("MovieModel", back_populates="likes")
    user: Mapped["UserModel"] = relationship("UserModel", back_populates="movie_likes")

    __table_args__ = (UniqueConstraint("user_id", "movie_id", name="unique_user_movie_like"),)


class MovieCommentModel(Base):
    __tablename__ = "movie_comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    movie_id: Mapped[int] = mapped_column(Integer, ForeignKey("movies.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))

    movie: Mapped["MovieModel"] = relationship("MovieModel", back_populates="comments")
    user: Mapped["UserModel"] = relationship("UserModel", back_populates="comments")

    likes: Mapped[List["CommentLikeModel"]] = relationship(
        "CommentLikeModel", back_populates="comment", cascade="all, delete-orphan"
    )


class FavoriteMovieModel(Base):
    __tablename__ = "favorite_movies"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id"), nullable=False)

    user: Mapped["UserModel"] = relationship("UserModel", back_populates="favorites")
    movie: Mapped["MovieModel"] = relationship("MovieModel", back_populates="favorites")

    def __repr__(self):
        return f"<FavoriteMovie(user_id={self.user_id}, movie_id={self.movie_id})>"


class MovieRatingModel(Base):
    __tablename__ = "movie_ratings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    rating: Mapped[float] = mapped_column(Float, nullable=False)

    movie: Mapped["MovieModel"] = relationship("MovieModel", back_populates="ratings")
    user: Mapped["UserModel"] = relationship("UserModel", back_populates="ratings")

    __table_args__ = (UniqueConstraint("movie_id", "user_id", name="unique_movie_user_rating_constraint"),)


class NotificationModel(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    message: Mapped[str] = mapped_column(String(255), nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    user: Mapped["UserModel"] = relationship("UserModel", back_populates="notifications")

    def __repr__(self):
        return f"<Notification(user_id={self.user_id}, message='{self.message}', is_read={self.is_read})>"


class CommentLikeModel(Base):
    __tablename__ = "comment_likes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    comment_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("movie_comments.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    user: Mapped["UserModel"] = relationship("UserModel", back_populates="comment_likes")
    comment: Mapped["MovieCommentModel"] = relationship("MovieCommentModel", back_populates="likes")

    __table_args__ = (UniqueConstraint("user_id", "comment_id", name="unique_user_comment_like"),)

    def __repr__(self):
        return f"<CommentLike(user_id={self.user_id}, comment_id={self.comment_id})>"
