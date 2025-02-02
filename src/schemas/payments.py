from pydantic import BaseModel
from decimal import Decimal
from typing import List, Optional
from datetime import datetime
from enum import Enum


class PaymentStatusEnum(str, Enum):
    successful = "successful"
    canceled = "canceled"
    refunded = "refunded"


class PaymentItemBase(BaseModel):
    order_item_id: int
    price_at_payment: Decimal


class PaymentItemCreate(PaymentItemBase):
    pass


class PaymentItemResponse(PaymentItemBase):
    id: int
    payment_id: int

    class Config:
        orm_mode = True


class PaymentBase(BaseModel):
    user_id: int
    order_id: int
    amount: Decimal
    status: PaymentStatusEnum = PaymentStatusEnum.successful


class PaymentCreate(PaymentBase):
    pass


class PaymentResponse(PaymentBase):
    id: int
    created_at: datetime
    external_payment_id: Optional[str] = None
    items: List[PaymentItemResponse] = []

    class Config:
        orm_mode = True


class PaymentIntentResponse(BaseModel):
    id: str
    client_secret: str
    status: str

    class Config:
        orm_mode = True


class PaymentHistoryResponse(BaseModel):
    id: int
    user_id: int
    order_id: int
    amount: Decimal
    status: PaymentStatusEnum
    created_at: datetime

    class Config:
        orm_mode = True


class AdminPaymentHistoryResponse(BaseModel):
    id: int
    user_id: int
    order_id: int
    amount: Decimal
    status: PaymentStatusEnum
    created_at: datetime
    external_payment_id: Optional[str] = None

    class Config:
        orm_mode = True


class PaymentStatusUpdate(BaseModel):
    status: PaymentStatusEnum
