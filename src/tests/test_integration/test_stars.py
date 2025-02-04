import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from schemas.stars import StarCreateSchema, StarUpdateSchema


@pytest.mark.asyncio
async def test_create_star(async_client: AsyncClient):

    star_data = StarCreateSchema(name="New Star")
    response = await async_client.post("/stars/", json=star_data.dict())
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == star_data.name


@pytest.mark.asyncio
async def test_create_star_conflict(async_client: AsyncClient, db_session: AsyncSession):

    star_data = StarCreateSchema(name="Existing Star")
    response = await async_client.post("/stars/", json=star_data.dict())
    assert response.status_code == 201

    response = await async_client.post("/stars/", json=star_data.dict())

    assert response.status_code == 409
    assert "A star with the name" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_star_by_id(async_client: AsyncClient, db_session: AsyncSession):

    star_data = StarCreateSchema(name="Test Star")
    response = await async_client.post("/stars/", json=star_data.dict())

    assert response.status_code == 201
    star = response.json()

    response = await async_client.get(f"/stars/{star['id']}/")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == star["id"]
    assert data["name"] == star["name"]


@pytest.mark.asyncio
async def test_get_star_by_id_not_found(async_client: AsyncClient):

    response = await async_client.get("/stars/9999/")
    assert response.status_code == 404
    assert response.json()["detail"] == "Star with the given ID was not found."


@pytest.mark.asyncio
async def test_delete_star_not_found(async_client: AsyncClient):

    response = await async_client.delete("/stars/9999/")
    assert response.status_code == 404
    assert response.json()["detail"] == "Star with the given ID was not found."


@pytest.mark.asyncio
async def test_update_star(async_client: AsyncClient, db_session: AsyncSession):

    star_data = StarCreateSchema(name="Original Star")
    response = await async_client.post("/stars/", json=star_data.dict())

    assert response.status_code == 201
    star = response.json()

    update_data = StarUpdateSchema(name="Updated Star")
    response = await async_client.patch(f"/stars/{star['id']}/", json=update_data.dict())

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Star"

    response = await async_client.get(f"/stars/{star['id']}/")
    assert response.status_code == 200
    updated_star = response.json()
    assert updated_star["name"] == "Updated Star"


@pytest.mark.asyncio
async def test_update_star_not_found(async_client: AsyncClient):

    update_data = StarUpdateSchema(name="Updated Star")
    response = await async_client.patch("/stars/9999/", json=update_data.dict())
    assert response.status_code == 404
    assert response.json()["detail"] == "Star with the given ID was not found."
