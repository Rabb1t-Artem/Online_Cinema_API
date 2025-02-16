from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from database import get_db
from schemas.orders import (
    OrderResponseSchema,
    OrderItemResponseSchema,
    OrderWithMoviesResponseSchema,
    OrderListResponseSchema,
)
from database.models.orders import OrderModel, OrderItemModel
from database.models.movies import MovieModel
from database.models.carts import CartModel, CartItemModel
from database.models.accounts import UserModel
from config.dependencies import get_current_user
from sqlalchemy.orm import joinedload, selectinload
from security.http import get_token
from security.interfaces import JWTAuthManagerInterface
from config import get_jwt_auth_manager
from fastapi import status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload
from sqlalchemy import func
from typing import Optional
from datetime import datetime
from routes.carts import get_cart_by_user

router = APIRouter(tags=["Orders"])


@router.get("/orders", response_model=OrderListResponseSchema)
async def get_orders(
    page: int = Query(1, ge=1, description="Page number (1-based index)"),
    per_page: int = Query(10, ge=1, le=20, description="Number of items per page"),
    status: Optional[str] = Query(None, description="Filter orders by status (e.g., 'pending', 'paid', 'cancelled')"),
    user_id: Optional[int] = Query(None, description="Filter orders by user ID"),
    order_date: Optional[str] = Query(None, description="Filter orders by a specific date (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
) -> OrderListResponseSchema:

    if current_user.group != "admin" and (status or user_id or order_date):
        raise HTTPException(status_code=403, detail="Access forbidden for non-admin users")

    query = select(OrderModel).options(joinedload(OrderModel.items).selectinload(OrderItemModel.movie))

    if status:
        query = query.filter(OrderModel.status == status)

    if user_id:
        query = query.filter(OrderModel.user_id == user_id)
    else:
        query = query.filter(OrderModel.user_id == current_user.id)

    if order_date:
        try:
            order_date_obj = datetime.strptime(order_date, "%Y-%m-%d")
            query = query.filter(func.date(OrderModel.created_at) == order_date_obj.date())
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    query = query.order_by(OrderModel.created_at.desc())

    # Підрахунок загальної кількості з урахуванням фільтрів
    total_items_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total_items = total_items_result.scalar() or 0

    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    result = await db.execute(query)
    orders = result.unique().scalars().all()

    order_responses = [
        OrderWithMoviesResponseSchema(
            id=order.id,
            user_id=order.user_id,
            created_at=order.created_at.isoformat(),
            status=order.status,
            total_amount=order.total_amount,
            movies=[item.movie.name for item in order.items],
        )
        for order in orders
    ]

    total_pages = (total_items + per_page - 1) // per_page

    prev_page = f"/orders?page={page - 1}&per_page={per_page}" if page > 1 else None
    next_page = f"/orders?page={page + 1}&per_page={per_page}" if page < total_pages else None

    return OrderListResponseSchema(
        orders=order_responses,
        prev_page=prev_page,
        next_page=next_page,
        total_pages=total_pages,
        total_items=total_items,
    )


@router.post("/orders", response_model=OrderResponseSchema, status_code=status.HTTP_201_CREATED)
async def create_order(
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> OrderResponseSchema:
    """
    Create a new order for a user.
    It checks if the cart has movies and if they are available before creating the order.
    """
    async with db.begin():
        # Check for any cancelled orders
        existing_orders = await db.execute(
            select(OrderModel).filter(OrderModel.user_id == current_user.id, OrderModel.status == "pending")
        )
        existing_orders = existing_orders.scalars().all()

        if existing_orders:
            raise HTTPException(status_code=400, detail="You have unpaid order")

        # Get movies in the user's cart
        user_cart = await get_cart_by_user(current_user.id, db)
        user_movies = await db.execute(
            select(MovieModel).where(MovieModel.id.in_([item.movie_id for item in user_cart.cart_items]))
        )
        movies_in_cart = user_movies.scalars().all()
        


        if not movies_in_cart:
            raise HTTPException(status_code=400, detail="Your cart is empty")

        # Calculate the total amount
        total_amount = sum(movie.price for movie in movies_in_cart)

        # Create a new order
    try:
        async with db.begin():  # Переконайтесь, що транзакція виконується всередині контекстного менеджера
            order = OrderModel(user_id=current_user.id, status="pending", total_amount=total_amount)
            db.add(order)
            await db.flush()  # Потрібно для того, щоб отримати ID замовлення після додавання

            # Додати пункти замовлення
            for movie in movies_in_cart:
                order_item = OrderItemModel(order_id=order.id, movie_id=movie.id, price_at_order=movie.price)
                db.add(order_item)

            # Очищення кошика користувача
            for item in user_cart.cart_items:
                await db.delete(item)

            await db.delete(user_cart)  # Видалити сам кошик
            await db.commit()  # Коміт після всіх змін у транзакції

        # Отримати замовлення з усіма пунктами
        order_res = await db.execute(
            select(OrderModel)
            .options(joinedload(OrderModel.items).joinedload(OrderItemModel.movie))
            .filter(OrderModel.id == order.id)
        )
        order = order_res.scalars().first()

        return order

    except SQLAlchemyError as e:
        await db.rollback()  # У випадку помилки відкатуємо транзакцію
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal server error {e}")


@router.get("/orders/{order_id}", response_model=OrderResponseSchema)
async def get_order(order_id: int, db: AsyncSession = Depends(get_db), current_user: UserModel = Depends(get_current_user),):
    """
    Get the details of a specific order.
    Returns a 404 if the order is not found or is cancelled.
    """
    # Get the order
    result = await db.execute(
        select(OrderModel)
        .options(joinedload(OrderModel.items).joinedload(OrderItemModel.movie))
        .filter(OrderModel.id == order_id)
    )
    order = result.scalar_one_or_none()

    if order.user_id != current_user.id and current_user.group != "admin":
        raise HTTPException(status_code=403, detail="Access forbidden")

    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status == "cancelled":
        raise HTTPException(status_code=400, detail="Order is cancelled and cannot be accessed")

    return OrderWithMoviesResponseSchema(
        id=order.id,
        user_id=order.user_id,
        created_at=order.created_at.isoformat(),
        status=order.status,
        total_amount=order.total_amount,
        movies=[item.movie.name for item in order.items],
    )


@router.put("/orders/{order_id}", response_model=OrderResponseSchema)
async def update_order_status(order_id: int, status: str, db: AsyncSession = Depends(get_db), current_user: UserModel = Depends(get_current_user),):
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

    if order.user_id != current_user.id and current_user.group != "admin":
        raise HTTPException(status_code=403, detail="Access forbidden")

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


@router.delete("/orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_order(
    order_id: int, 
    db: AsyncSession = Depends(get_db), 
    current_user: UserModel = Depends(get_current_user)
):
    """
    Delete an order if its status is "pending".
    """

    # Отримуємо замовлення
    result = await db.execute(select(OrderModel).options(joinedload(OrderModel.items)).filter(OrderModel.id == order_id))
    order = result.scalars().first()

    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    # Перевірка прав доступу
    if order.user_id != current_user.id and current_user.group != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access forbidden")

    # Перевірка статусу
    if order.status != "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete a paid or cancelled order")

    # Видалення всіх пов'язаних OrderItemModel, якщо потрібно
    # await db.execute(select(OrderItemModel).filter(OrderItemModel.order_id == order_id))
    # order_items = result.scalars().all()
    for item in order.items:
        await db.delete(item)

    # Видалення самого замовлення
    await db.delete(order)

    # Фіналізація змін
    await db.commit()

    return {"detail": "Order deleted successfully"}


@router.put("/orders/{order_id}/cancel", response_model=OrderResponseSchema)
async def cancel_order(order_id: int, db: AsyncSession = Depends(get_db), current_user: UserModel = Depends(get_current_user),):
    """
    Cancel an order if it is still "pending".
    """
    # Get the order
    result = await db.execute(select(OrderModel).filter(OrderModel.id == order_id))
    order = result.scalar_one_or_none()
    
    if order.user_id != current_user.id and current_user.group != "admin":
        raise HTTPException(status_code=403, detail="Access forbidden")

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
