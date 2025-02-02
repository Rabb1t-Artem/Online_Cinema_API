import pytest
from httpx import AsyncClient
from database.models.carts import CartItemModel
from database.models.orders import OrderModel, OrderItemModel
from database.session_test import get_test_db


# Тест для перегляду порожнього кошика (очікуємо 404)
@pytest.mark.asyncio
async def test_view_empty_cart(async_client: AsyncClient, create_test_user):
    user = await create_test_user()
    response = await async_client.get("/cart", params={"user_id": user.id})
    assert response.status_code == 404
    assert response.json()["detail"] == "Cart is empty"


# Тест для додавання фільму до кошика та перевірки помилки при повторному додаванні
@pytest.mark.asyncio
async def test_add_movie_to_cart(async_client: AsyncClient, create_test_user, create_test_movie):
    user = await create_test_user()
    movie = await create_test_movie()

    # Додаємо фільм
    response = await async_client.post(f"/cart/{movie.id}/add", params={"user_id": user.id})
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["movie"]["id"] == movie.id

    # Повторне додавання того ж фільму має повернути 400
    response_dup = await async_client.post(f"/cart/{movie.id}/add", params={"user_id": user.id})
    assert response_dup.status_code == 400
    assert response_dup.json()["detail"] == "Movie is already in the cart"


# Тест для видалення фільму з кошика
@pytest.mark.asyncio
async def test_remove_movie_from_cart(async_client: AsyncClient, create_test_user, create_test_movie):
    user = await create_test_user()
    movie = await create_test_movie()

    # Додаємо фільм до кошика
    add_response = await async_client.post(f"/cart/{movie.id}/add", params={"user_id": user.id})
    assert add_response.status_code == 200

    # Видаляємо фільм
    remove_response = await async_client.delete(f"/cart/{movie.id}/remove", params={"user_id": user.id})
    assert remove_response.status_code == 200
    assert remove_response.json()["message"] == "Movie removed from cart"

    # Повторне видалення має повернути 404
    remove_again_response = await async_client.delete(f"/cart/{movie.id}/remove", params={"user_id": user.id})
    assert remove_again_response.status_code == 404
    assert remove_again_response.json()["detail"] == "Movie is not in the cart"


# Тест для очищення кошика
@pytest.mark.asyncio
async def test_clear_cart(async_client: AsyncClient, create_test_user, create_test_movie):
    user = await create_test_user()
    movie1 = await create_test_movie()
    movie2 = await create_test_movie(name="Another Movie")

    # Додаємо два фільми
    await async_client.post(f"/cart/{movie1.id}/add", params={"user_id": user.id})
    await async_client.post(f"/cart/{movie2.id}/add", params={"user_id": user.id})

    # Очищуємо кошик
    clear_response = await async_client.delete("/cart/clear", params={"user_id": user.id})
    assert clear_response.status_code == 200
    assert clear_response.json()["message"] == "Cart cleared"

    # Перевіряємо, що кошик порожній
    get_response = await async_client.get("/cart", params={"user_id": user.id})
    assert get_response.status_code == 404
    assert get_response.json()["detail"] == "Cart is empty"


# Тест для перегляду кошика адміністратором
@pytest.mark.asyncio
async def test_view_user_cart_admin(async_client: AsyncClient, create_test_user, create_test_movie):
    user = await create_test_user()
    movie = await create_test_movie()

    # Додаємо фільм у кошик
    await async_client.post(f"/cart/{movie.id}/add", params={"user_id": user.id})

    # Перевіряємо, що адміністратор може переглянути кошик користувача
    admin_response = await async_client.get(f"/cart/admin/{user.id}")
    assert admin_response.status_code == 200
    admin_data = admin_response.json()
    assert "cart_items" in admin_data
    assert len(admin_data["cart_items"]) > 0


@pytest.mark.asyncio
async def test_cannot_add_purchased_movie(async_client: AsyncClient, create_test_user, create_test_movie):
    user = await create_test_user()
    movie = await create_test_movie()

    async with get_test_db() as db:
        order = OrderModel(user_id=user.id, status="paid")
        db.add(order)
        await db.commit()
        await db.refresh(order)

        order_item = OrderItemModel(order_id=order.id, movie_id=movie.id)
        db.add(order_item)
        await db.commit()

    response = await async_client.post(f"/cart/{movie.id}/add", params={"user_id": user.id})

    assert response.status_code == 400
    assert response.json()["detail"] == "You have already purchased this movie"
