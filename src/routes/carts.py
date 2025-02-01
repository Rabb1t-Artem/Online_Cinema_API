# routes/carts.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from datetime import datetime

from database.session import get_db
from database.models.carts import CartModel, CartItemModel
from database.models.movies import MovieModel
from schemas.carts import CartResponseSchema, CartItemResponseSchema

cart_router = APIRouter(prefix="/cart", tags=["Cart"])


async def get_cart_by_user(user_id: int, db: AsyncSession) -> CartModel:
    result = await db.execute(
        select(CartModel)
        .filter(CartModel.user_id == user_id)
        .options(joinedload(CartModel.cart_items).joinedload(CartItemModel.movie))
    )
    cart = result.scalars().first()

    if not cart:
        cart = CartModel(user_id=user_id)
        db.add(cart)
        await db.commit()
        await db.refresh(cart)

    return cart


@cart_router.get("/", response_model=CartResponseSchema)
async def view_cart(user_id: int, db: AsyncSession = Depends(get_db)):
    cart = await get_cart_by_user(user_id, db)
    return cart


@cart_router.post("/{movie_id}/add", response_model=CartItemResponseSchema)
async def add_movie(user_id: int, movie_id: int, db: AsyncSession = Depends(get_db)):
    cart = await get_cart_by_user(user_id, db)

    movie = await db.get(MovieModel, movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    existing_item = await db.execute(select(CartItemModel).filter_by(cart_id=cart.id, movie_id=movie_id))
    if existing_item.scalars().first():
        raise HTTPException(status_code=400, detail="Movie is already in the cart")

    cart_item = CartItemModel(cart_id=cart.id, movie_id=movie_id, added_at=datetime.utcnow())
    db.add(cart_item)
    await db.commit()
    await db.refresh(cart_item)

    return cart_item


@cart_router.delete("/{movie_id}/remove")
async def remove_movie(user_id: int, movie_id: int, db: AsyncSession = Depends(get_db)):
    cart = await get_cart_by_user(user_id, db)

    cart_item = await db.execute(select(CartItemModel).filter_by(cart_id=cart.id, movie_id=movie_id))
    cart_item = cart_item.scalars().first()

    if not cart_item:
        raise HTTPException(status_code=404, detail="Movie is not in the cart")

    await db.delete(cart_item)
    await db.commit()
    return {"message": "Movie removed from cart"}


@cart_router.delete("/clear")
async def empty_cart(user_id: int, db: AsyncSession = Depends(get_db)):
    cart = await get_cart_by_user(user_id, db)

    if not cart.cart_items:
        raise HTTPException(status_code=400, detail="Cart is already empty")

    await db.execute(select(CartItemModel).filter_by(cart_id=cart.id).delete())
    await db.commit()
    return {"message": "Cart cleared"}


@cart_router.post("/checkout")
async def purchase_cart(user_id: int, db: AsyncSession = Depends(get_db)):
    cart = await get_cart_by_user(user_id, db)

    if not cart.cart_items:
        raise HTTPException(status_code=400, detail="Cart is empty, nothing to purchase")

    purchased_movies = [item.movie_id for item in cart.cart_items]

    await db.execute(select(CartItemModel).filter_by(cart_id=cart.id).delete())
    await db.commit()

    return {"message": "Checkout successful", "purchased_movies": purchased_movies}
