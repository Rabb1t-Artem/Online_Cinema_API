from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from database import get_db
from database.models.movies import (
    MovieModel,
    GenreModel,
    DirectorModel,
    CertificationModel,
    StarModel,
)
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
)
def get_movie_list(
    page: int = Query(1, ge=1, description="Page number (1-based index)"),
    per_page: int = Query(10, ge=1, le=20, description="Number of items per page"),
    db: Session = Depends(get_db),
) -> MovieListResponseSchema:
    """
    Fetch a paginated list of movies from the database.
    """
    offset = (page - 1) * per_page

    query = db.query(MovieModel).order_by(MovieModel.year.desc())

    total_items = query.count()
    movies = query.offset(offset).limit(per_page).all()

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
    status_code=201,
)
def create_movie(movie_data: MovieCreateSchema, db: Session = Depends(get_db)) -> MovieDetailSchema:
    """
    Add a new movie to the database.
    """
    existing_movie = (
        db.query(MovieModel).filter(MovieModel.name == movie_data.name, MovieModel.year == movie_data.year).first()
    )

    if existing_movie:
        raise HTTPException(
            status_code=409,
            detail=f"A movie with the name '{movie_data.name}' and year '{movie_data.year}' already exists.",
        )

    try:
        director = db.query(DirectorModel).filter_by(name=movie_data.director.name).first()
        if not director:
            director = DirectorModel(name=movie_data.director.name)
            db.add(director)
            db.flush()

        certification = db.query(CertificationModel).filter_by(name=movie_data.certification.name).first()
        if not certification:
            certification = CertificationModel(name=movie_data.certification.name)
            db.add(certification)
            db.flush()

        genres = []
        for genre_name in movie_data.genres:
            genre = db.query(GenreModel).filter_by(name=genre_name).first()
            if not genre:
                genre = GenreModel(name=genre_name)
                db.add(genre)
                db.flush()
            genres.append(genre)

        stars = []
        for star_name in movie_data.stars:
            star = db.query(StarModel).filter_by(name=star_name).first()
            if not star:
                star = StarModel(name=star_name)
                db.add(star)
                db.flush()
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
            director=director,
            certification=certification,
            genres=genres,
            stars=stars,
        )
        db.add(movie)
        db.commit()
        db.refresh(movie)

        return MovieDetailSchema.model_validate(movie)
    except IntegrityError:
        db.rollback()
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
)
def get_movie_by_id(
    movie_id: int,
    db: Session = Depends(get_db),
) -> MovieDetailSchema:
    """
    Retrieve detailed information about a specific movie by its ID.
    """
    movie = (
        db.query(MovieModel)
        .options(
            joinedload(MovieModel.director),
            joinedload(MovieModel.certification),
            joinedload(MovieModel.genres),
            joinedload(MovieModel.stars),
        )
        .filter(MovieModel.id == movie_id)
        .first()
    )

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
    status_code=204,
)
def delete_movie(
    movie_id: int,
    db: Session = Depends(get_db),
):
    """
    Delete a specific movie by its ID.
    """
    movie = db.query(MovieModel).filter(MovieModel.id == movie_id).first()

    if not movie:
        raise HTTPException(status_code=404, detail="Movie with the given ID was not found.")

    db.delete(movie)
    db.commit()
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
)
def update_movie(
    movie_id: int,
    movie_data: MovieUpdateSchema,
    db: Session = Depends(get_db),
):
    """
    Update a specific movie by its ID.
    """
    movie = db.query(MovieModel).filter(MovieModel.id == movie_id).first()

    if not movie:
        raise HTTPException(status_code=404, detail="Movie with the given ID was not found.")

    for key, value in movie_data.dict(exclude_unset=True).items():
        setattr(movie, key, value)

    db.commit()
    db.refresh(movie)

    return MovieDetailSchema.model_validate(movie)
