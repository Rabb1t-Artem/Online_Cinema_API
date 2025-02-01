from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from database.models.movies import GenreModel
from schemas.genres import GenreListResponseSchema, GenreDetailSchema, GenreCreateSchema, GenreUpdateSchema

router = APIRouter()


@router.get(
    "/genres/",
    response_model=GenreListResponseSchema,
    summary="Get a paginated list of genres",
    description=(
        "<h3>This endpoint retrieves a paginated list of genres from the database. "
        "Clients can specify the `page` number and the number of items per page using `per_page`. "
        "The response includes details about the genres, total pages, and total items, "
        "along with links to the previous and next pages if applicable.</h3>"
    ),
    responses={
        404: {
            "description": "No genres found.",
            "content": {"application/json": {"example": {"detail": "No genres found."}}},
        }
    },
)
def get_genre_list(
    page: int = Query(1, ge=1, description="Page number (1-based index)"),
    per_page: int = Query(10, ge=1, le=20, description="Number of items per page"),
    db: Session = Depends(get_db),
) -> GenreListResponseSchema:
    """
    Fetch a paginated list of genres from the database.
    """
    offset = (page - 1) * per_page
    query = db.query(GenreModel).order_by(GenreModel.name.asc())

    total_items = query.count()
    genres = query.offset(offset).limit(per_page).all()

    if not genres:
        raise HTTPException(status_code=404, detail="No genres found.")

    genre_list = [GenreDetailSchema.model_validate(genre) for genre in genres]

    total_pages = (total_items + per_page - 1) // per_page

    response = GenreListResponseSchema(
        genres=genre_list,
        prev_page=f"/theater/genres/?page={page - 1}&per_page={per_page}" if page > 1 else None,
        next_page=f"/theater/genres/?page={page + 1}&per_page={per_page}" if page < total_pages else None,
        total_pages=total_pages,
        total_items=total_items,
    )
    return response


@router.post(
    "/genres/",
    response_model=GenreDetailSchema,
    summary="Add a new genre",
    description=(
        "<h3>This endpoint allows clients to add a new genre to the database. "
        "It accepts details such as the genre's name and associates it with movies if necessary.</h3>"
    ),
    responses={
        201: {
            "description": "Genre created successfully.",
        },
        400: {
            "description": "Invalid input.",
            "content": {"application/json": {"example": {"detail": "Invalid input data."}}},
        },
    },
    status_code=201,
)
def create_genre(genre_data: GenreCreateSchema, db: Session = Depends(get_db)) -> GenreDetailSchema:
    """
    Add a new genre to the database.
    """
    existing_genre = db.query(GenreModel).filter(GenreModel.name == genre_data.name).first()

    if existing_genre:
        raise HTTPException(status_code=409, detail=f"A genre with the name '{genre_data.name}' already exists.")

    genre = GenreModel(name=genre_data.name)
    db.add(genre)
    db.commit()
    db.refresh(genre)

    return GenreDetailSchema.model_validate(genre)


@router.get(
    "/genres/{genre_id}/",
    response_model=GenreDetailSchema,
    summary="Get genre details by ID",
    description=(
        "<h3>Fetch detailed information about a specific genre by its unique ID. "
        "If the genre with the given ID is not found, a 404 error will be returned.</h3>"
    ),
    responses={
        404: {
            "description": "Genre not found.",
            "content": {"application/json": {"example": {"detail": "Genre with the given ID was not found."}}},
        }
    },
)
def get_genre_by_id(
    genre_id: int,
    db: Session = Depends(get_db),
) -> GenreDetailSchema:
    """
    Retrieve detailed information about a specific genre by its ID.
    """
    genre = db.query(GenreModel).filter(GenreModel.id == genre_id).first()

    if not genre:
        raise HTTPException(status_code=404, detail="Genre with the given ID was not found.")

    return GenreDetailSchema.model_validate(genre)


@router.delete(
    "/genres/{genre_id}/",
    summary="Delete a genre by ID",
    description=(
        "<h3>Delete a specific genre from the database by its unique ID.</h3>"
        "<p>If the genre exists, it will be deleted. If it does not exist, "
        "a 404 error will be returned.</p>"
    ),
    responses={
        204: {"description": "Genre deleted successfully."},
        404: {
            "description": "Genre not found.",
            "content": {"application/json": {"example": {"detail": "Genre with the given ID was not found."}}},
        },
    },
    status_code=204,
)
def delete_genre(
    genre_id: int,
    db: Session = Depends(get_db),
):
    """
    Delete a specific genre by its ID.
    """
    genre = db.query(GenreModel).filter(GenreModel.id == genre_id).first()

    if not genre:
        raise HTTPException(status_code=404, detail="Genre with the given ID was not found.")

    db.delete(genre)
    db.commit()
    return {"detail": "Genre deleted successfully."}


@router.patch(
    "/genres/{genre_id}/",
    summary="Update a genre by ID",
    description=(
        "<h3>Update details of a specific genre by its unique ID.</h3>"
        "<p>This endpoint updates the details of an existing genre. If the genre with "
        "the given ID does not exist, a 404 error is returned.</p>"
    ),
    responses={
        200: {
            "description": "Genre updated successfully.",
            "content": {"application/json": {"example": {"detail": "Genre updated successfully."}}},
        },
        404: {
            "description": "Genre not found.",
            "content": {"application/json": {"example": {"detail": "Genre with the given ID was not found."}}},
        },
    },
)
def update_genre(
    genre_id: int,
    genre_data: GenreUpdateSchema,
    db: Session = Depends(get_db),
):
    """
    Update a specific genre by its ID.
    """
    genre = db.query(GenreModel).filter(GenreModel.id == genre_id).first()

    if not genre:
        raise HTTPException(status_code=404, detail="Genre with the given ID was not found.")

    for key, value in genre_data.dict(exclude_unset=True).items():
        setattr(genre, key, value)

    db.commit()
    db.refresh(genre)

    return GenreDetailSchema.model_validate(genre)
