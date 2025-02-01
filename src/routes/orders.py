from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from database import get_db
from schemas.orders import OrderResponseSchema, OrderItemResponseSchema
from database.models.orders import OrderModel, OrderItemModel
from database.models.movies import MovieModel

router = APIRouter()


@router.post("/create_order", response_model=OrderResponseSchema)
async def create_order(user_id: int, db: AsyncSession = Depends(get_db)):
    """
    Create a new order for a user.
    It checks if the cart has movies and if they are available before creating the order.
    """
    async with db.begin():
        # Check for any cancelled orders
        existing_orders = await db.execute(
            select(OrderModel).filter(OrderModel.user_id == user_id, OrderModel.status != "paid")
        )
        existing_orders = existing_orders.scalars().all()

        if existing_orders and any(order.status == "cancelled" for order in existing_orders):
            raise HTTPException(status_code=400, detail="You have cancelled orders")

        # Get movies in the user's cart
        user_movies = await db.execute(
            select(MovieModel)
            .join(OrderItemModel)
            .join(OrderModel)
            .filter(OrderModel.user_id == user_id, OrderModel.status != "paid")
        )
        movies_in_cart = user_movies.scalars().all()

        if not movies_in_cart:
            raise HTTPException(status_code=400, detail="Your cart is empty")

        # Check for unavailable movies
        unavailable_movies = [movie for movie in movies_in_cart if not movie.is_available]
        if unavailable_movies:
            raise HTTPException(status_code=400, detail="Some movies are unavailable")

        # Check for existing pending orders
        existing_orders = await db.execute(
            select(OrderModel).filter(OrderModel.user_id == user_id, OrderModel.status == "pending")
        )
        pending_orders = existing_orders.scalars().all()
        for order in pending_orders:
            order_movie_ids = [item.movie_id for item in order.items]
            if any(item.movie_id in order_movie_ids for item in movies_in_cart):
                raise HTTPException(
                    status_code=400,
                    detail="Some movies are already in another pending order",
                )

        # Calculate the total amount
        total_amount = sum(movie.price for movie in movies_in_cart)

        # Create a new order
        order = OrderModel(user_id=user_id, status="pending", total_amount=total_amount)
        db.add(order)
        await db.flush()

        # Add order items
        for movie in movies_in_cart:
            order_item = OrderItemModel(order_id=order.id, movie_id=movie.id, price_at_order=movie.price)
            db.add(order_item)

        await db.commit()
        return order


@router.get("/orders/{order_id}", response_model=OrderResponseSchema)
async def get_order(order_id: int, db: AsyncSession = Depends(get_db)):
    """
    Get the details of a specific order.
    Returns a 404 if the order is not found or is cancelled.
    """
    # Get the order
    result = await db.execute(select(OrderModel).filter(OrderModel.id == order_id))
    order = result.scalar_one_or_none()

    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status == "cancelled":
        raise HTTPException(status_code=400, detail="Order is cancelled and cannot be accessed")

    # Get the order items
    order_items = await db.execute(select(OrderItemModel).filter(OrderItemModel.order_id == order_id))
    items = order_items.scalars().all()

    order_items_response = [
        OrderItemResponseSchema(movie_id=item.movie_id, price_at_order=item.price_at_order) for item in items
    ]

    return OrderResponseSchema(
        id=order.id,
        user_id=order.user_id,
        created_at=order.created_at,
        status=order.status,
        total_amount=order.total_amount,
        items=order_items_response,
    )


@router.put("/orders/{order_id}", response_model=OrderResponseSchema)
async def update_order_status(order_id: int, status: str, db: AsyncSession = Depends(get_db)):
    """
    Update the status of an order.
    Valid statuses are "pending", "paid", and "cancelled".
    """
    # Check for valid status
    if status not in ["pending", "paid", "cancelled"]:
        raise HTTPException(status_code=400, detail="Invalid status")

    # Get the order
    result = await db.execute(select(OrderModel).filter(OrderModel.id == order_id))
    order = result.scalar_one_or_none()

    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status in ["paid", "cancelled"]:
        raise HTTPException(status_code=400, detail="Cannot update a paid or cancelled order")

    # Update the order status
    order.status = status

    # Commit changes
    await db.commit()
    await db.refresh(order)

    # Get the order items
    order_items = await db.execute(select(OrderItemModel).filter(OrderItemModel.order_id == order_id))
    items = order_items.scalars().all()

    order_items_response = [
        OrderItemResponseSchema(movie_id=item.movie_id, price_at_order=item.price_at_order) for item in items
    ]

    return OrderResponseSchema(
        id=order.id,
        user_id=order.user_id,
        created_at=order.created_at,
        status=order.status,
        total_amount=order.total_amount,
        items=order_items_response,
    )


@router.delete("/orders/{order_id}", status_code=204)
async def delete_order(order_id: int, db: AsyncSession = Depends(get_db)):
    """
    Delete an order if its status is "pending".
    """
    # Get the order
    result = await db.execute(select(OrderModel).filter(OrderModel.id == order_id))
    order = result.scalar_one_or_none()

    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status != "pending":
        raise HTTPException(status_code=400, detail="Cannot delete a paid or cancelled order")

    # Delete order items
    await db.execute(select(OrderItemModel).filter(OrderItemModel.order_id == order_id))

    db.delete(order)

    await db.commit()
    return {"detail": "Order deleted successfully"}


@router.put("/orders/{order_id}/cancel", response_model=OrderResponseSchema)
async def cancel_order(order_id: int, db: AsyncSession = Depends(get_db)):
    """
    Cancel an order if it is still "pending".
    """
    # Get the order
    result = await db.execute(select(OrderModel).filter(OrderModel.id == order_id))
    order = result.scalar_one_or_none()

    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status != "pending":
        raise HTTPException(status_code=400, detail="Only pending orders can be cancelled")

    # Update the order status to "cancelled"
    order.status = "cancelled"

    # Commit changes
    await db.commit()
    await db.refresh(order)

    # Get the order items
    order_items = await db.execute(select(OrderItemModel).filter(OrderItemModel.order_id == order_id))
    items = order_items.scalars().all()

    order_items_response = [
        OrderItemResponseSchema(movie_id=item.movie_id, price_at_order=item.price_at_order) for item in items
    ]

    return OrderResponseSchema(
        id=order.id,
        user_id=order.user_id,
        created_at=order.created_at,
        status=order.status,
        total_amount=order.total_amount,
        items=order_items_response,
    )
