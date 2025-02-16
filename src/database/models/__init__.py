from sqlalchemy.orm import declarative_base

Base = declarative_base()
from .accounts import (
    UserGroupEnum,
    GenderEnum,
    UserGroupModel,
    UserModel,
    UserProfileModel,
    ActivationTokenModel,
    PasswordResetTokenModel,
    RefreshTokenModel,
)
from .payments import PaymentModel, PaymentItemModel
from .orders import OrderItemModel, OrderModel
from .carts import CartModel, CartItemModel
from .movies import (
    MoviesGenresModel,
    StarsMoviesModel,
    MoviesDirectorsModel,
    GenreModel,
    StarModel,
    DirectorModel,
    CertificationModel,
    MovieModel,
    MovieLikeModel,
    MovieCommentModel,
    FavoriteMovieModel,
    MovieRatingModel,
    NotificationModel,
    CommentLikeModel,
)
