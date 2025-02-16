import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.models.movies import MovieModel, CertificationModel


@pytest.mark.asyncio
async def test_get_movie_list_empty(async_client: AsyncClient):
    response = await async_client.get("/movies/")
    assert response.status_code == 404
    assert response.json()["detail"] == "No movies found."


@pytest.mark.asyncio
async def test_create_movie(async_client: AsyncClient, db_session: AsyncSession):

    movie_data = {
        "name": "Inception",
        "year": 2010,
        "time": 148,
        "imdb": 8.8,
        "votes": 2000000,
        "meta_score": 74,
        "gross": 829895144,
        "description": "A thief who enters the dreams of others.",
        "price": 10.99,
        "directors": [{"id": 1, "name": "John"}],
        "certification_id": {"id": 1, "name": "PG-13"},
        "genres": [{"id": 1, "name": "horror"}, {"id": 2, "name": "horror"}],
        "stars": [{"id": 1, "name": "Anton"}, {"id": 2, "name": "Mike"}],
    }
    response = await async_client.post("/movies/", json=movie_data)
    assert response.status_code == 201, response.json()
    data = response.json()
    print(response.json())
    assert data["name"] == "Inception"
    assert data["year"] == 2010

    movie = await db_session.execute(select(MovieModel).filter(MovieModel.name == "Inception"))
    movie = movie.scalars().first()
    assert movie is not None


@pytest.mark.asyncio
async def test_get_movie_by_id(async_client: AsyncClient, db_session: AsyncSession):
    certification = CertificationModel(name="PG-13")
    db_session.add(certification)
    await db_session.commit()
    await db_session.refresh(certification)

    movie = MovieModel(
        name="Avatar",
        year=2009,
        time=162,
        imdb=7.8,
        votes=1500000,
        meta_score=83,
        gross=2787965087,
        description="A marine on an alien planet.",
        price=12.99,
        certification_id=certification.id,
    )
    db_session.add(movie)
    await db_session.commit()
    await db_session.refresh(movie)

    response = await async_client.get(f"/movies/{movie.id}/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Avatar"
    assert data["year"] == 2009


@pytest.mark.asyncio
async def test_delete_movie(async_client: AsyncClient, db_session: AsyncSession):
    certification = CertificationModel(name="R")
    db_session.add(certification)
    await db_session.commit()
    await db_session.refresh(certification)

    movie = MovieModel(
        name="The Matrix",
        year=1999,
        time=136,
        imdb=8.7,
        votes=1600000,
        meta_score=73,
        gross=463517383,
        description="A hacker learns about the true nature of reality.",
        price=9.99,
        certification_id=certification.id,
    )
    db_session.add(movie)
    await db_session.commit()
    await db_session.refresh(movie)

    response = await async_client.delete(f"/movies/{movie.id}/")
    assert response.status_code == 204

    deleted_movie = await db_session.execute(select(MovieModel).filter(MovieModel.id == movie.id))
    deleted_movie = deleted_movie.scalars().first()
    assert deleted_movie is None
