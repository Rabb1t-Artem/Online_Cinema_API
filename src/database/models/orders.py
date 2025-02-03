from decimal import Decimal
from typing import List
from datetime import datetime
from sqlalchemy import Integer, ForeignKey, String, DECIMAL, DateTime, func
from sqlalchemy.orm import relationship, Mapped, mapped_column
from .base import Base
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from database.models.accounts import UserModel
    from database.models.movies import MovieModel
    from database.models.payments import PaymentModel, PaymentItemModel
# from . import UserModel
# from . import MovieModel
# from . import PaymentModel, PaymentItemModel


class OrderModel(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), nullable=False)

    user = relationship("UserModel", back_populates="orders")
    items = relationship("OrderItemModel", back_populates="order")
    payments = relationship(
        "PaymentModel", back_populates="order", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return (
            f"<OrderModel(id={self.id}, "
            f"user_id={self.user_id}, "
            f"status={self.status}, "
            f"total_amount={self.total_amount})>"
        )


class OrderItemModel(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"), nullable=False)
    price_at_order: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), nullable=False)

    order = relationship("OrderModel", back_populates="items")
    movie = relationship("MovieModel", back_populates="order_items")
    payment_items = relationship("PaymentItemModel", back_populates="order_item")

    def __repr__(self):
        return (
            f"<OrderItemModel(id={self.id}, "
            f"order_id={self.order_id}, "
            f"movie_id={self.movie_id}, "
            f"price_at_order={self.price_at_order})>"
        )
