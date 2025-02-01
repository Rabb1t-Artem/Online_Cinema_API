from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from database import get_db
from database.models.movies import StarModel
from schemas.stars import (
    StarListResponseSchema,
    StarSchema,
    StarCreateSchema,
    StarUpdateSchema,
    StarDetailSchema,
)

router = APIRouter()


@router.get(
    "/stars/",
    response_model=StarListResponseSchema,
    summary="Get a paginated list of stars",
    description=(
        "<h3>This endpoint retrieves a paginated list of stars from the database. "
        "Clients can specify the `page` number and the number of items per page using `per_page`. "
        "The response includes details about the stars, total pages, and total items, "
        "along with links to the previous and next pages if applicable.</h3>"
    ),
    responses={
        404: {
            "description": "No stars found.",
            "content": {"application/json": {"example": {"detail": "No stars found."}}},
        }
    },
    tags=["Stars"],
)
async def get_star_list(
    page: int = Query(1, ge=1, description="Page number (1-based index)"),
    per_page: int = Query(10, ge=1, le=20, description="Number of items per page"),
    db: AsyncSession = Depends(get_db),
) -> StarListResponseSchema:
    """
    Fetch a paginated list of stars from the database.
    """
    offset = (page - 1) * per_page

    result = await db.execute(select(StarModel).order_by(StarModel.name))
    stars = result.scalars().offset(offset).limit(per_page).all()

    if not stars:
        raise HTTPException(status_code=404, detail="No stars found.")

    star_list = [StarSchema.model_validate(star) for star in stars]

    result = await db.execute(select(StarModel))
    total_items = result.scalars().count()

    total_pages = (total_items + per_page - 1) // per_page

    response = StarListResponseSchema(
        stars=star_list,
        prev_page=(f"/theater/stars/?page={page - 1}&per_page={per_page}" if page > 1 else None),
        next_page=(f"/theater/stars/?page={page + 1}&per_page={per_page}" if page < total_pages else None),
        total_pages=total_pages,
        total_items=total_items,
    )
    return response


@router.post(
    "/stars/",
    response_model=StarDetailSchema,
    summary="Add a new star",
    description=(
        "<h3>This endpoint allows clients to add a new star to the database. "
        "It accepts details such as the name of the star.</h3>"
    ),
    responses={
        201: {
            "description": "Star created successfully.",
        },
        400: {
            "description": "Invalid input.",
            "content": {"application/json": {"example": {"detail": "Invalid input data."}}},
        },
    },
    status_code=status.HTTP_201_CREATED,
    tags=["Stars", "Create"],
)
async def create_star(star_data: StarCreateSchema, db: AsyncSession = Depends(get_db)) -> StarDetailSchema:
    """
    Add a new star to the database asynchronously.
    """
    
    result = await db.execute(select(StarModel).filter(StarModel.name == star_data.name))
    existing_star = result.scalars().first()

    if existing_star:
        raise HTTPException(
            status_code=409,
            detail=f"A star with the name '{star_data.name}' already exists.",
        )
    star = StarModel(name=star_data.name)

    db.add(star)
    await db.commit()
    await db.refresh(star)

    return StarDetailSchema.model_validate(star)


@router.get(
    "/stars/{star_id}/",
    response_model=StarDetailSchema,
    summary="Get star details by ID",
    description=(
        "<h3>Fetch detailed information about a specific star by its unique ID. "
        "This endpoint retrieves all available details for the star, such as "
        "its name and related movies. "
        "If the star with the given ID is not found, a 404 error will be returned.</h3>"
    ),
    responses={
        404: {
            "description": "Star not found.",
            "content": {"application/json": {"example": {"detail": "Star with the given ID was not found."}}},
        }
    },
    tags=["Stats", "ID_find"],
)
async def get_star_by_id(
    star_id: int,
    db: AsyncSession = Depends(get_db),
) -> StarDetailSchema:
    """
    Retrieve detailed information about a specific star by its ID asynchronously.
    """
    result = await db.execute(select(StarModel).filter(StarModel.id == star_id))
    star = result.scalars().first()

    if not star:
        raise HTTPException(status_code=404, detail="Star with the given ID was not found.")

    return StarDetailSchema.model_validate(star)


@router.delete(
    "/stars/{star_id}/",
    summary="Delete a star by ID",
    description=(
        "<h3>Delete a specific star from the database by its unique ID.</h3>"
        "<p>If the star exists, it will be deleted. If it does not exist, "
        "a 404 error will be returned.</p>"
    ),
    responses={
        204: {"description": "Star deleted successfully."},
        404: {
            "description": "Star not found.",
            "content": {"application/json": {"example": {"detail": "Star with the given ID was not found."}}},
        },
    },
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Stars", "Delete"],
)
async def delete_star(
    star_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a specific star by its ID asynchronously.
    """
    result = await db.execute(select(StarModel).filter(StarModel.id == star_id))
    star = result.scalars().first()

    if not star:
        raise HTTPException(status_code=404, detail="Star with the given ID was not found.")

    await db.delete(star)
    await db.commit()

    return {"detail": "Star deleted successfully."}


@router.patch(
    "/stars/{star_id}/",
    summary="Update a star by ID",
    description=(
        "<h3>Update details of a specific star by its unique ID.</h3>"
        "<p>This endpoint updates the details of an existing star. If the star with "
        "the given ID does not exist, a 404 error is returned.</p>"
    ),
    responses={
        200: {
            "description": "Star updated successfully.",
            "content": {"application/json": {"example": {"detail": "Star updated successfully."}}},
        },
        404: {
            "description": "Star not found.",
            "content": {"application/json": {"example": {"detail": "Star with the given ID was not found."}}},
        },
    },
    tags=["Stars", "Update"],
)
async def update_star(
    star_id: int,
    star_data: StarUpdateSchema,
    db: AsyncSession = Depends(get_db),
):
    """
    Update a specific star by its ID asynchronously.
    """
    result = await db.execute(select(StarModel).filter(StarModel.id == star_id))
    star = result.scalars().first()

    if not star:
        raise HTTPException(status_code=404, detail="Star with the given ID was not found.")

    for key, value in star_data.dict(exclude_unset=True).items():
        setattr(star, key, value)

    await db.commit()
    await db.refresh(star)

    return StarDetailSchema.model_validate(star)
