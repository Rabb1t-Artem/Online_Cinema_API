import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.models.movies import GenreModel, MovieModel, CertificationModel


@pytest.mark.asyncio
async def test_create_genre(async_client: AsyncClient, db_session: AsyncSession):
    genre_data = {"name": "Action"}
    response = await async_client.post("/genres/", json=genre_data)
    assert response.status_code == 201, response.json()
    data = response.json()
    assert data["name"] == "Action"

    genre = await db_session.execute(select(GenreModel).filter(GenreModel.name == "Action"))
    genre = genre.scalars().first()
    assert genre is not None


@pytest.mark.asyncio
async def test_get_genre_list_empty(async_client: AsyncClient):
    response = await async_client.get("/genres")
    assert response.status_code == 404
    assert response.json()["detail"] == "No genres found."


@pytest.mark.asyncio
async def test_get_genre_by_id(async_client: AsyncClient, db_session: AsyncSession):

    genre = GenreModel(name="Comedy")
    db_session.add(genre)
    await db_session.commit()
    await db_session.refresh(genre)

    response = await async_client.get(f"/genres/{genre.id}/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Comedy"


@pytest.mark.asyncio
async def test_delete_genre(async_client: AsyncClient, db_session: AsyncSession):
    genre = GenreModel(name="Drama")
    db_session.add(genre)
    await db_session.commit()
    await db_session.refresh(genre)

    response = await async_client.delete(f"/genres/{genre.id}/")
    assert response.status_code == 204

    deleted_genre = await db_session.execute(select(GenreModel).filter(GenreModel.id == genre.id))
    deleted_genre = deleted_genre.scalars().first()
    assert deleted_genre is None


@pytest.mark.asyncio
async def test_update_genre(async_client: AsyncClient, db_session: AsyncSession):
    genre = GenreModel(name="Thriller")
    db_session.add(genre)
    await db_session.commit()
    await db_session.refresh(genre)

    updated_data = {"name": "Suspense"}
    response = await async_client.patch(f"/genres/{genre.id}/", json=updated_data)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Suspense"

    await db_session.commit()
    await db_session.refresh(genre)

    updated_genre = await db_session.execute(select(GenreModel).filter(GenreModel.id == genre.id))
    updated_genre = updated_genre.scalars().first()
    assert updated_genre.name == "Suspense"


@pytest.mark.asyncio
async def test_get_movies_by_genre(async_client: AsyncClient, db_session: AsyncSession):
    genre = GenreModel(name="Action")
    db_session.add(genre)
    await db_session.commit()
    await db_session.refresh(genre)

    certification = CertificationModel(name="PG-13")
    db_session.add(certification)
    await db_session.commit()

    movie = MovieModel(
        name="The Avengers",
        year=2012,
        time=143,
        imdb=8.0,
        votes=1000000,
        description="Action packed superhero movie.",
        price=14.99,
        certification_id=certification.id,
        genres=[genre],
    )
    db_session.add(movie)
    await db_session.commit()

    response = await async_client.get(f"/genres/{genre.id}/movies/")
    assert response.status_code == 200
    movies = response.json()
    assert len(movies) > 0
    assert movies[0]["name"] == "The Avengers"
