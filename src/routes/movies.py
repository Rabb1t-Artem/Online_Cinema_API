from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from starlette import status

from database import get_db
from database.models.movies import (
    MovieModel,
    GenreModel,
    DirectorModel,
    CertificationModel,
    StarModel,
    MovieLikeModel,
    MovieCommentModel,
    FavoriteMovieModel,
    MovieRatingModel,
    NotificationModel,
    CommentLikeModel,
)
from database.models.orders import OrderItemModel
from database.models.accounts import UserModel
from config.dependencies import get_current_user
from schemas import (
    MovieListResponseSchema,
    MovieListItemSchema,
    MovieDetailSchema,
    MovieCreateSchema,
    MovieUpdateSchema,
)
from schemas.movies import (
    MovieLikeSchema,
    MovieCommentCreateSchema,
    MovieCommentSchema,
    FavoriteMovieListSchema,
    FavoriteMovieResponseSchema,
    NotificationSchema,
)

router = APIRouter()


@router.get(
    "/movies/",
    response_model=MovieListResponseSchema,
    summary="Get a paginated list of movies",
    description=(
        "<h3>This endpoint retrieves a paginated list of movies from the database. "
        "Clients can specify the `page` number and the number of items per page using `per_page`. "
        "The response includes details about the movies, total pages, and total items, "
        "along with links to the previous and next pages if applicable.</h3>"
    ),
    responses={
        404: {
            "description": "No movies found.",
            "content": {"application/json": {"example": {"detail": "No movies found."}}},
        }
    },
    tags=["Movies"],
)
async def get_movie_list(
    page: int = Query(1, ge=1, description="Page number (1-based index)"),
    per_page: int = Query(10, ge=1, le=20, description="Number of items per page"),
    db: AsyncSession = Depends(get_db),
) -> MovieListResponseSchema:
    """
    Asynchronously fetch a paginated list of movies from the database.
    """
    offset = (page - 1) * per_page

    total_items_result = await db.execute(select(func.count()).select_from(MovieModel))
    total_items = total_items_result.scalar_one()

    result = await db.execute(select(MovieModel).order_by(MovieModel.year.desc()).offset(offset).limit(per_page))
    movies = result.scalars().all()

    if not movies:
        raise HTTPException(status_code=404, detail="No movies found.")

    movie_list = [MovieListItemSchema.model_validate(movie) for movie in movies]

    total_pages = (total_items + per_page - 1) // per_page

    response = MovieListResponseSchema(
        movies=movie_list,
        prev_page=f"/theater/movies/?page={page - 1}&per_page={per_page}" if page > 1 else None,
        next_page=f"/theater/movies/?page={page + 1}&per_page={per_page}" if page < total_pages else None,
        total_pages=total_pages,
        total_items=total_items,
    )
    return response


@router.post(
    "/movies/",
    response_model=MovieDetailSchema,
    summary="Add a new movie",
    description=(
        "<h3>This endpoint allows clients to add a new movie to the database. "
        "It accepts details such as name, year, time, genres, "
        "stars, director, certification, and other attributes. "
        "The associated genres, stars, director, "
        "and certification will be created or linked automatically.</h3>"
    ),
    responses={
        201: {
            "description": "Movie created successfully.",
        },
        400: {
            "description": "Invalid input.",
            "content": {"application/json": {"example": {"detail": "Invalid input data."}}},
        },
    },
    status_code=status.HTTP_201_CREATED,
    tags=["Movies"],
)
async def create_movie(
    movie_data: MovieCreateSchema,
    db: AsyncSession = Depends(get_db),
) -> MovieDetailSchema:
    """
    Asynchronously add a new movie to the database.
    Checks for duplicates and automatically links or creates associated entities
    such as director, certification, genres, and stars.
    """

    result = await db.execute(
        select(MovieModel).filter(MovieModel.name == movie_data.name, MovieModel.year == movie_data.year)
    )

    existing_movie = result.scalars().first()
    if existing_movie:
        raise HTTPException(
            status_code=409,
            detail=f"A movie with the name '{movie_data.name}' and year '{movie_data.year}' already exists.",
        )

    try:
        directors = []
        for director_item in movie_data.directors:
            result_director = await db.execute(
                select(DirectorModel).filter(DirectorModel.name == director_item.name)
            )
            director = result_director.scalar_one_or_none()
            if not director:
                director = DirectorModel(name=director_item.name)
                db.add(director)
                await db.flush()
            directors.append(director)

        result_certification = await db.execute(
            select(CertificationModel).filter(CertificationModel.name == movie_data.certification_id.name)
        )
        certification = result_certification.scalars().first()

        if not certification:
            certification = CertificationModel(name=movie_data.certification_id.name)
            db.add(certification)
            await db.flush()

        genres = []
        for genre_name in movie_data.genres:
            result_genres = await db.execute(select(GenreModel).filter(GenreModel.name == genre_name.name))
            genre = result_genres.scalars().first()
            if not genre:
                genre = GenreModel(name=genre_name.name)
                db.add(genre)
                await db.flush()
            genres.append(genre)

        stars = []
        for star_item in movie_data.stars:
            result_stars = await db.execute(select(StarModel).filter(StarModel.name == star_item.name))
            star = result_stars.scalars().first()
            if not star:
                star = StarModel(name=star_item.name)
                db.add(star)
                await db.flush()
            stars.append(star)

        movie = MovieModel(
            name=movie_data.name,
            year=movie_data.year,
            time=movie_data.time,
            imdb=movie_data.imdb,
            votes=movie_data.votes,
            meta_score=movie_data.meta_score,
            gross=movie_data.gross,
            description=movie_data.description,
            price=movie_data.price,
            directors=directors,
            certification_id=certification.id,
            genres=genres,
            stars=stars,
        )
        db.add(movie)
        await db.commit()
        await db.refresh(movie)

        result = await db.execute(
            select(MovieModel)
            .options(
                selectinload(MovieModel.directors),
                selectinload(MovieModel.genres),
                selectinload(MovieModel.stars),
                selectinload(MovieModel.certification)
            )
            .filter(MovieModel.id == movie.id)
        )
        movie = result.scalars().first()

        return MovieDetailSchema.model_validate(movie)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Invalid input data.")


@router.get(
    "/movies/{movie_id}/",
    response_model=MovieDetailSchema,
    summary="Get movie details by ID",
    description=(
        "<h3>Fetch detailed information about a specific movie by its unique ID. "
        "This endpoint retrieves all available details for the movie, such as "
        "its name, genre, director, stars, certification, and other attributes. "
        "If the movie with the given ID is not found, a 404 error will be returned.</h3>"
    ),
    responses={
        404: {
            "description": "Movie not found.",
            "content": {"application/json": {"example": {"detail": "Movie with the given ID was not found."}}},
        }
    },
    tags=["Movies"],
)
async def get_movie_by_id(
    movie_id: int,
    db: AsyncSession = Depends(get_db),
) -> MovieDetailSchema:
    """
    Asynchronously retrieve detailed information about a specific movie by its ID.
    """
    result = await db.execute(
        select(MovieModel)
        .options(
            joinedload(MovieModel.directors),
            joinedload(MovieModel.certification),
            joinedload(MovieModel.genres),
            joinedload(MovieModel.stars),
        )
        .filter(MovieModel.id == movie_id)
    )

    movie = result.scalars().first()

    if not movie:
        raise HTTPException(status_code=404, detail="Movie with the given ID was not found.")

    return MovieDetailSchema.model_validate(movie)


@router.delete(
    "/movies/{movie_id}/",
    summary="Delete a movie by ID",
    description=(
        "<h3>Delete a specific movie from the database by its unique ID.</h3>"
        "<p>If the movie exists, it will be deleted. If it does not exist, "
        "a 404 error will be returned.</p>"
    ),
    responses={
        204: {"description": "Movie deleted successfully."},
        404: {
            "description": "Movie not found.",
            "content": {"application/json": {"example": {"detail": "Movie with the given ID was not found."}}},
        },
    },
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Movies"],
)
async def delete_movie(
    movie_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Asynchronously delete a specific movie by its ID.
    Prevent deletion if at least one order item (purchase) exists for the movie.
    """
    result = await db.execute(select(MovieModel).filter(MovieModel.id == movie_id))
    movie = result.scalars().first()

    if not movie:
        raise HTTPException(status_code=404, detail="Movie with the given ID was not found.")

    result = await db.execute(select(OrderItemModel).filter(OrderItemModel.movie_id == movie_id))
    order_items_count = len(result.scalars().all())

    if order_items_count > 0:
        raise HTTPException(status_code=400, detail="Cannot delete movie, it has been purchased by at least one user.")

    await db.delete(movie)
    await db.commit()

    return {"detail": "Movie deleted successfully."}


@router.patch(
    "/movies/{movie_id}/",
    summary="Update a movie by ID",
    description=(
        "<h3>Update details of a specific movie by its unique ID.</h3>"
        "<p>This endpoint updates the details of an existing movie. If the movie with "
        "the given ID does not exist, a 404 error is returned.</p>"
    ),
    responses={
        200: {
            "description": "Movie updated successfully.",
            "content": {"application/json": {"example": {"detail": "Movie updated successfully."}}},
        },
        404: {
            "description": "Movie not found.",
            "content": {"application/json": {"example": {"detail": "Movie with the given ID was not found."}}},
        },
    },
    tags=["Movies"],
)
async def update_movie(
    movie_id: int,
    movie_data: MovieUpdateSchema,
    db: AsyncSession = Depends(get_db),
):
    """
    Asynchronously update a specific movie by its ID.
    """
    result = await db.execute(select(MovieModel).filter(MovieModel.id == movie_id))
    movie = result.scalars().first()

    if not movie:
        raise HTTPException(status_code=404, detail="Movie with the given ID was not found.")

    for key, value in movie_data.model_dump(exclude_unset=True).items():
        setattr(movie, key, value)

    await db.commit()
    await db.refresh(movie)

    result = await db.execute(
        select(MovieModel)
        .options(
            selectinload(MovieModel.directors),
            selectinload(MovieModel.genres),
            selectinload(MovieModel.stars),
            selectinload(MovieModel.certification)
        )
        .filter(MovieModel.id == movie.id)
    )
    movie = result.scalars().first()

    return MovieDetailSchema.model_validate(movie)


@router.post(
    "/movies/{movie_id}/like/",
    summary="Like or dislike a movie",
    response_model=MovieLikeSchema,
    tags=["Movies"],
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
    result = await db.execute(select(MovieModel).filter(MovieModel.id == movie_id))
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
    return {"message": "Movie like status updated successfully", "is_liked": is_liked}


@router.get(
    "/movies/{movie_id}/likes/",
    summary="Get like/dislike count for a movie",
    tags=["Movies"],
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


# @router.post(
#     "/movies/{movie_id}/comments/",
#     response_model=MovieCommentSchema,
#     tags=["Movies", "Comments"],
# )
# async def add_comment(
#     movie_id: int,
#     comment_data: MovieCommentCreateSchema,
#     db: AsyncSession = Depends(get_db),
#     current_user: UserModel = Depends(get_current_user),
# ):
#     """
#     Asynchronously add a comment to a movie.
#     """
#     result = await db.execute(select(MovieModel).filter(MovieModel.id == movie_id))
#     movie = result.scalars().first()
#     if not movie:
#         raise HTTPException(status_code=404, detail="Movie not found.")
#
#     comment = MovieCommentModel(movie_id=movie_id, user_id=current_user.id, content=comment_data.content)
#     db.add(comment)
#     await db.commit()
#     await db.refresh(comment)
#
#     return comment


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

    return favorite_movies


@router.post("/movies/{movie_id}/rating/", summary="Rate a movie", tags=["Movies", "Rating"])
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

    average_rating = movie.average_rating
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
    content: str,
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
        content=content,
        movie_id=parent_comment.movie_id,
        user_id=current_user.id,
        id=comment_id,
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
