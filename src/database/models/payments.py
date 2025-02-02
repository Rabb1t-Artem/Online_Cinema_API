from decimal import Decimal
from datetime import datetime
from typing import List
import enum

from sqlalchemy import Integer, ForeignKey, DateTime, Numeric, Enum, String, func
from sqlalchemy.orm import relationship, Mapped, mapped_column

from database import Base
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from database.models.orders import OrderModel, OrderItemModel
    from database.models.accounts import UserModel


class PaymentStatus(enum.Enum):
    successful = "successful"
    canceled = "canceled"
    refunded = "refunded"


class PaymentItemModel(Base):
    __tablename__ = "payment_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id", ondelete="CASCADE"), nullable=False)
    order_item_id: Mapped[int] = mapped_column(ForeignKey("order_items.id", ondelete="CASCADE"), nullable=False)
    price_at_payment: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    payment: Mapped["PaymentModel"] = relationship("PaymentModel", back_populates="items")
    order_item: Mapped["OrderItemModel"] = relationship("OrderItemModel", back_populates="payment_items")

    def __repr__(self):
        return (
            f"<PaymentItemModel(id={self.id}, "
            f"payment_id={self.payment_id}, "
            f"order_item_id={self.order_item_id}, "
            f"price_at_payment={self.price_at_payment})>"
        )


class PaymentModel(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus), nullable=False, default=PaymentStatus.successful
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    external_payment_id: Mapped[str] = mapped_column(String(255), nullable=True)

    order: Mapped["OrderModel"] = relationship("OrderModel", back_populates="payments")
    user: Mapped["UserModel"] = relationship("UserModel", back_populates="payments")
    payment_items: Mapped[List["PaymentItemModel"]] = relationship("PaymentItemModel", back_populates="payment")

    def __repr__(self):
        return f"<PaymentModel(id={self.id}, order_id={self.order_id}, amount={self.amount}, status={self.status})>"
