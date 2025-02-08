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
)
from database.models.orders import OrderItemModel
from schemas import (
    MovieListResponseSchema,
    MovieListItemSchema,
    MovieDetailSchema,
    MovieCreateSchema,
    MovieUpdateSchema,
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
    tags=["Movies", "All"],
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
    tags=["Movies", "Create"],
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
            result_director = await db.execute(select(DirectorModel).filter(DirectorModel.name == director_item.name))
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
                selectinload(MovieModel.certification),
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
    tags=["Movies", "ID_search"],
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
    tags=["Movies", "Delete"],
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
    tags=["Movies", "Update"],
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
            selectinload(MovieModel.certification),
        )
        .filter(MovieModel.id == movie.id)
    )
    movie = result.scalars().first()

    return MovieDetailSchema.model_validate(movie)
