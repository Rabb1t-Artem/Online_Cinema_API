from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from database.models.movies import (
    MovieModel,
    MovieLikeModel,
    MovieCommentModel,
    FavoriteMovieModel,
    MovieRatingModel,
    NotificationModel,
    CommentLikeModel,
)
from database.models.accounts import UserModel
from config.dependencies import get_current_user
from schemas.movie_interaction import (
    MovieLikeSchema,
    MovieCommentSchema,
    FavoriteMovieListSchema,
    FavoriteMovieResponseSchema,
    NotificationSchema,
    MovieCommentCreateSchema,
    ReplyContentSchema,
    AverageRatingResponseSchema,
    RatingResponseSchema,
)
from schemas.movies import MovieBaseSchema

router = APIRouter()


@router.post(
    "/movies/{movie_id}/like/",
    summary="Like or dislike a movie",
    response_model=MovieLikeSchema,
    tags=["Movies", "Likes"],
)
async def like_movie(
    movie_id: int,
    is_liked: bool,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """
    Asynchronously like or dislike a specific movie.
    If the movie is already liked/disliked, update the status.
    """
    result = await db.execute(select(MovieModel).where(MovieModel.id == movie_id))
    movie = result.scalars().first()

    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found.")

    result_like = await db.execute(
        select(MovieLikeModel).filter(
            MovieLikeModel.movie_id == movie_id,
            MovieLikeModel.user_id == current_user.id,
        )
    )
    like_entry = result_like.scalar_one_or_none()

    if like_entry:
        like_entry.is_liked = is_liked
    else:
        new_like = MovieLikeModel(user_id=current_user.id, movie_id=movie_id, is_liked=is_liked)
        db.add(new_like)

    await db.commit()
    return {
        "movie_id": movie_id,
        "message": "Movie like status updated successfully",
        "is_liked": is_liked,
    }


@router.get(
    "/movies/{movie_id}/likes/",
    summary="Get like/dislike count for a movie",
    tags=["Movies", "Likes"],
)
async def get_movie_likes(movie_id: int, db: AsyncSession = Depends(get_db)):
    """
    Asynchronously get the count of likes and dislikes for a specific movie.
    """
    result = await db.execute(select(MovieModel).filter(MovieModel.id == movie_id))
    movie = result.scalars().first()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found.")

    likes_count = await db.scalar(
        select(func.count()).select_from(MovieLikeModel).filter_by(movie_id=movie_id, is_liked=True)
    )

    dislikes_count = await db.scalar(
        select(func.count()).select_from(MovieLikeModel).filter_by(movie_id=movie_id, is_liked=False)
    )

    return {"movie_id": movie_id, "likes": likes_count, "dislikes": dislikes_count}


@router.post(
    "/movies/{movie_id}/comments/",
    response_model=MovieCommentSchema,
    tags=["Movies", "Comments"],
)
async def add_comment(
    movie_id: int,
    comment_data: MovieCommentCreateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """
    Asynchronously add a comment to a movie.
    """
    result = await db.execute(select(MovieModel).filter(MovieModel.id == movie_id))
    movie = result.scalars().first()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found.")

    comment = MovieCommentModel(movie_id=movie_id, user_id=current_user.id, content=comment_data.content)
    db.add(comment)
    await db.commit()
    await db.refresh(comment)

    return comment


@router.get(
    "/movies/{movie_id}/comments/",
    response_model=List[MovieCommentSchema],
    tags=["Movies", "Comments"],
)
async def get_comments(movie_id: int, db: AsyncSession = Depends(get_db)):
    """
    Asynchronously retrieve comments for a specific movie.
    """
    result = await db.execute(select(MovieModel).filter(MovieModel.id == movie_id))
    movie = result.scalars().first()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found.")

    result = await db.execute(select(MovieCommentModel).filter(MovieCommentModel.movie_id == movie_id))
    comments = result.scalars().all()

    return comments


@router.post(
    "/movies/{movie_id}/favorites/",
    summary="Add a movie to favorites",
    tags=["Movies", "Favorites"],
    response_model=FavoriteMovieResponseSchema,
)
async def add_to_favorites(
    movie_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """
    Asynchronously add a movie to the favorites list of the current user.
    """
    result = await db.execute(select(MovieModel).filter(MovieModel.id == movie_id))
    movie = result.scalars().first()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found.")

    result = await db.execute(
        select(FavoriteMovieModel).filter(
            FavoriteMovieModel.movie_id == movie_id,
            FavoriteMovieModel.user_id == current_user.id,
        )
    )
    favorite = result.scalars().first()

    if favorite:
        raise HTTPException(status_code=400, detail="Movie is already in favorites.")

    new_favorite = FavoriteMovieModel(user_id=current_user.id, movie_id=movie_id)
    db.add(new_favorite)
    await db.commit()

    return {"message": "Movie added to favorites."}


@router.delete(
    "/movies/{movie_id}/favorites/",
    summary="Remove a movie from favorites",
    tags=["Movies", "Favorites"],
    response_model=FavoriteMovieResponseSchema,
)
async def remove_from_favorites(
    movie_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """
    Asynchronously remove a movie from the favorites list of the current user.
    """
    result = await db.execute(
        select(FavoriteMovieModel).filter(
            FavoriteMovieModel.movie_id == movie_id,
            FavoriteMovieModel.user_id == current_user.id,
        )
    )
    favorite = result.scalars().first()

    if not favorite:
        raise HTTPException(status_code=404, detail="Movie not in favorites.")

    await db.delete(favorite)
    await db.commit()

    return {"message": "Movie removed from favorites."}


@router.get(
    "/movies/favorites/",
    summary="Get all favorite movies",
    tags=["Movies", "Favorites"],
    response_model=FavoriteMovieListSchema,
)
async def get_favorite_movies(
    search: Optional[str] = None,
    sort_by: Optional[str] = "name",
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """
    Asynchronously get the list of favorite movies with optional search, filter, and sort options.
    """

    query = select(MovieModel).join(FavoriteMovieModel).filter(FavoriteMovieModel.user_id == current_user.id)

    if search:
        query = query.filter(MovieModel.name.ilike(f"%{search}%"))

    if sort_by:
        if sort_by == "name":
            query = query.order_by(MovieModel.name)
        elif sort_by == "year":
            query = query.order_by(MovieModel.year)

    result = await db.execute(query)
    favorite_movies = result.scalars().all()

    if not favorite_movies:
        return {"movies": []}

    movie_schemas = [MovieBaseSchema.from_orm(movie) for movie in favorite_movies]

    return {"movies": movie_schemas}


@router.post(
    "/movies/{movie_id}/rating/",
    summary="Rate a movie",
    tags=["Movies", "Rating"],
    response_model=RatingResponseSchema,
)
async def rate_movie(
    movie_id: int,
    rating: float,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """
    Rate a movie on a 10-point scale.
    """
    if rating < 1 or rating > 10:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 10.")

    result = await db.execute(select(MovieModel).filter(MovieModel.id == movie_id))
    movie = result.scalars().first()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found.")

    result_rating = await db.execute(
        select(MovieRatingModel).filter(
            MovieRatingModel.movie_id == movie_id, MovieRatingModel.user_id == current_user.id
        )
    )
    existing_rating = result_rating.scalars().first()

    if existing_rating:
        existing_rating.rating = rating
    else:
        new_rating = MovieRatingModel(movie_id=movie_id, user_id=current_user.id, rating=rating)
        db.add(new_rating)

    await db.commit()

    return {"message": "Rating added/updated successfully."}


@router.get(
    "/movies/{movie_id}/rating/",
    summary="Get the average rating of a movie",
    tags=["Movies", "Rating"],
    response_model=AverageRatingResponseSchema,
)
async def get_movie_rating(
    movie_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get the average rating of a movie.
    """
    result = await db.execute(select(MovieModel).filter(MovieModel.id == movie_id))
    movie = result.scalars().first()

    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found.")

    result_rating = await db.execute(
        select(func.avg(MovieRatingModel.rating)).filter(MovieRatingModel.movie_id == movie_id)
    )
    average_rating = result_rating.scalar()

    if average_rating is None:
        return {"message": "No ratings yet for this movie."}

    return {"average_rating": average_rating}


async def create_notification(db: AsyncSession, user_id: int, message: str) -> NotificationModel:
    notification = NotificationModel(user_id=user_id, message=message)
    db.add(notification)
    await db.commit()
    await db.refresh(notification)
    return notification


@router.post(
    "/movies/comments/{comment_id}/reply/",
    summary="Reply to a comment",
    tags=["Comments", "Notifications"],
)
async def reply_to_comment(
    comment_id: int,
    reply: ReplyContentSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """
    Add a reply to a comment and notify the original comment's author.
    """

    result = await db.execute(select(MovieCommentModel).filter(MovieCommentModel.id == comment_id))
    parent_comment = result.scalars().first()
    if not parent_comment:
        raise HTTPException(status_code=404, detail="Comment not found.")

    reply = MovieCommentModel(
        content=reply.content,
        movie_id=parent_comment.movie_id,
        user_id=current_user.id,
    )
    db.add(reply)
    await db.commit()
    await db.refresh(reply)

    if parent_comment.user_id != current_user.id:
        await create_notification(
            db,
            user_id=parent_comment.user_id,
            message="Your comment has received a reply.",
        )

    return {"message": "Reply added successfully."}


@router.post(
    "/movies/comments/{comment_id}/like/",
    summary="Like a comment",
    tags=["Comments", "Notifications"],
)
async def like_comment(
    comment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """
    Like a comment and notify the comment's author.
    """
    result = await db.execute(select(MovieCommentModel).filter(MovieCommentModel.id == comment_id))
    comment = result.scalars().first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found.")

    result = await db.execute(
        select(CommentLikeModel).filter(
            CommentLikeModel.comment_id == comment_id,
            CommentLikeModel.user_id == current_user.id,
        )
    )
    existing_like = result.scalars().first()
    if existing_like:
        raise HTTPException(status_code=400, detail="You have already liked this comment.")

    new_like = CommentLikeModel(comment_id=comment_id, user_id=current_user.id)
    db.add(new_like)
    await db.commit()

    if comment.user_id != current_user.id:
        await create_notification(db, user_id=comment.user_id, message="Your comment has received a like.")

    return {"message": "Comment liked successfully."}


@router.get(
    "/notifications/",
    summary="Get notifications for the current user",
    response_model=List[NotificationSchema],
    tags=["Notifications"],
)
async def get_notifications(
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """
    Retrieve all notifications for the current user.
    """
    result = await db.execute(select(NotificationModel).filter(NotificationModel.user_id == current_user.id))
    notifications = result.scalars().all()
    if not notifications:
        raise HTTPException(status_code=404, detail="No notifications found.")
    return notifications
