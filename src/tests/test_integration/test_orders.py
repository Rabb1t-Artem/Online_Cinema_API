import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.orders import OrderModel, OrderItemModel
from database.models.carts import CartModel, CartItemModel


@pytest.mark.asyncio
async def test_create_order(async_client: AsyncClient, create_test_user, create_test_movie, db_session: AsyncSession):
    """
    Test the creation of a new order.
    Ensures that an order can be created only if the cart contains movies.
    """
    user = await create_test_user()
    movie = await create_test_movie()

    # Add a movie to the cart
    async with db_session.begin():
        cart = CartModel(user_id=user.id)
        db_session.add(cart)
        await db_session.commit()
        await db_session.refresh(cart)

        cart_item = CartItemModel(cart_id=cart.id, movie_id=movie.id)
        db_session.add(cart_item)
        await db_session.commit()

    # Create an order
    response = await async_client.post("/orders", headers={"Authorization": f"Bearer fake-token"})

    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["status"] == "pending"
    assert data["total_amount"] == movie.price


@pytest.mark.asyncio
async def test_get_order_by_id(async_client: AsyncClient, create_test_user, create_test_movie,
                               db_session: AsyncSession):
    """
    Test retrieving an order by its ID.
    Ensures that users can retrieve order details correctly.
    """
    user = await create_test_user()
    movie = await create_test_movie()

    # Manually create an order
    async with db_session.begin():
        order = OrderModel(user_id=user.id, status="pending", total_amount=movie.price)
        db_session.add(order)
        await db_session.commit()
        await db_session.refresh(order)

        order_item = OrderItemModel(order_id=order.id, movie_id=movie.id, price_at_order=movie.price)
        db_session.add(order_item)
        await db_session.commit()

    # Fetch the order
    response = await async_client.get(f"/orders/{order.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == order.id
    assert data["status"] == "pending"
    assert data["total_amount"] == movie.price


@pytest.mark.asyncio
async def test_get_orders_list_admin(async_client: AsyncClient, create_test_user, db_session: AsyncSession):
    """
    Test retrieving the list of all orders (Admin only).
    Ensures that only admins can access the full order list.
    """
    user = await create_test_user()

    async with db_session.begin():
        order = OrderModel(user_id=user.id, status="pending", total_amount=100.0)
        db_session.add(order)
        await db_session.commit()

    response = await async_client.get("/orders?page=1&per_page=10",
                                      headers={"Authorization": "Bearer fake-admin-token"})

    assert response.status_code == 200
    data = response.json()
    assert len(data["orders"]) > 0


@pytest.mark.asyncio
async def test_update_order_status(async_client: AsyncClient, create_test_user, db_session: AsyncSession):
    """
    Test updating an order's status.
    Ensures that a pending order can be updated to 'paid'.
    """
    user = await create_test_user()

    async with db_session.begin():
        order = OrderModel(user_id=user.id, status="pending", total_amount=100.0)
        db_session.add(order)
        await db_session.commit()
        await db_session.refresh(order)

    response = await async_client.put(f"/orders/{order.id}", params={"status": "paid"})

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "paid"


@pytest.mark.asyncio
async def test_delete_order(async_client: AsyncClient, create_test_user, db_session: AsyncSession):
    """
    Test deleting an order.
    Ensures that only 'pending' orders can be deleted.
    """
    user = await create_test_user()

    async with db_session.begin():
        order = OrderModel(user_id=user.id, status="pending", total_amount=100.0)
        db_session.add(order)
        await db_session.commit()
        await db_session.refresh(order)

    response = await async_client.delete(f"/orders/{order.id}")

    assert response.status_code == 204


@pytest.mark.asyncio
async def test_cancel_order(async_client: AsyncClient, create_test_user, db_session: AsyncSession):
    """
    Test canceling an order.
    Ensures that only 'pending' orders can be canceled.
    """
    user = await create_test_user()

    async with db_session.begin():
        order = OrderModel(user_id=user.id, status="pending", total_amount=100.0)
        db_session.add(order)
        await db_session.commit()
        await db_session.refresh(order)

    response = await async_client.put(f"/orders/{order.id}/cancel")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "cancelled"
