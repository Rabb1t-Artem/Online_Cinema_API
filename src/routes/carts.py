import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy import delete
from datetime import datetime, timezone
from security.http import get_token
from security.token_manager import JWTAuthManager
from config import get_jwt_auth_manager
from config.dependencies import get_current_user

from database.models.orders import OrderItemModel, OrderModel
from database import get_db
from database.models.carts import CartModel, CartItemModel
from database.models.movies import MovieModel
from schemas.carts import CartResponseSchema, CartItemResponseSchema
from database.models.accounts import UserModel

cart_router = APIRouter(prefix="/cart", tags=["Cart"])


async def get_cart_by_user(user_id: int, db: AsyncSession) -> CartModel:
    """Retrieve the user's cart or create a new one if it does not exist."""
    result = await db.execute(
        select(CartModel).options(joinedload(CartModel.cart_items).selectinload(CartItemModel.movie).joinedload(MovieModel.genres))
        .filter(CartModel.user_id == user_id
        )
    )
    cart = result.scalars().first()

    if not cart:
        cart = CartModel(user_id=user_id)
        db.add(cart)
        await db.commit()
        await db.refresh(cart)

    return cart


@cart_router.get("/", response_model=CartResponseSchema)
async def view_cart(
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> CartResponseSchema:
    """Get the contents of the user's cart."""
    cart = await get_cart_by_user(current_user.id, db)

    if not cart.cart_items:
        raise HTTPException(status_code=404, detail="Cart is empty")

    return CartResponseSchema.model_validate(cart)


@cart_router.post("/{movie_id}/add", response_model=CartItemResponseSchema)
async def add_movie(movie_id: int, db: AsyncSession = Depends(get_db), current_user: UserModel = Depends(get_current_user)) -> CartItemResponseSchema:
    """Add a movie to the user's cart, ensuring it's not already purchased."""
    try:
        cart = await get_cart_by_user(current_user.id, db)

        movie_result = await db.execute(select(MovieModel).options(joinedload(MovieModel.genres)).filter_by(id=movie_id))
        movie = movie_result.scalars().first()
        if not movie:
            raise HTTPException(status_code=404, detail="Movie not found")

        existing_item = await db.execute(select(CartItemModel).filter_by(cart_id=cart.id, movie_id=movie_id))
        if existing_item.scalars().first():
            raise HTTPException(status_code=400, detail="Movie is already in the cart")

        purchased_movie = await db.execute(
            select(OrderItemModel)
            .join(OrderModel)
            .filter(OrderModel.user_id == current_user.id)
            .filter(OrderItemModel.movie_id == movie_id)
            .filter(OrderModel.status == "paid")
        )
        if purchased_movie.scalars().first():
            raise HTTPException(status_code=400, detail="You have already purchased this movie")

        # async with db.begin():
        cart_item = CartItemModel(
            cart_id=cart.id, movie_id=movie_id, added_at=datetime.now(timezone.utc).replace(tzinfo=None)
        )
        db.add(cart_item)
        # await db.flush()
        await db.commit()
        await db.refresh(cart_item)

        return CartItemResponseSchema(id=cart_item.id, cart_id=cart_item.cart_id, movie=movie, added_at=cart_item.added_at)

    except HTTPException as http_error:
        raise http_error
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@cart_router.delete("/{movie_id}/remove")
async def remove_movie(movie_id: int, db: AsyncSession = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    """Remove a movie from the user's cart and log the event."""

    try:
        cart = await get_cart_by_user(current_user.id, db)

        cart_item = await db.execute(select(CartItemModel).filter_by(cart_id=cart.id, movie_id=movie_id))
        cart_item = cart_item.scalars().first()

        if not cart_item:
            raise HTTPException(status_code=404, detail="Movie is not in the cart")

        # async with db.begin():
        await db.execute(delete(CartItemModel).where(CartItemModel.id == cart_item.id))
        await db.commit()

        print(f"Moderator Alert: User {current_user.id} removed movie {movie_id} from their cart.")

        return {"message": "Movie removed from cart"}

    except HTTPException as http_error:
        raise http_error
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@cart_router.delete("/clear")
async def empty_cart(db: AsyncSession = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    """Clear all items from the user's cart."""
    try:
        cart = await get_cart_by_user(current_user.id, db)

        if not cart.cart_items:
            raise HTTPException(status_code=400, detail="Cart is already empty")

        async with db.begin():
            await db.execute(delete(CartItemModel).where(CartItemModel.cart_id == cart.id))

        return {"message": "Cart cleared"}

    except HTTPException as http_error:
        raise http_error
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@cart_router.get("/admin/{user_id}", response_model=CartResponseSchema)
async def view_user_cart(user_id: int, db: AsyncSession = Depends(get_db)) -> CartResponseSchema:
    """Admin route to view a user's cart."""
    try:
        cart = await get_cart_by_user(user_id, db)
        if not cart.cart_items:
            raise HTTPException(status_code=404, detail="Cart is empty")

        return CartResponseSchema.model_validate(cart)

    except HTTPException as http_error:
        raise http_error
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
