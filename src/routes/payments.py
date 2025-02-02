from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

import stripe

from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from schemas.payments import Payment, PaymentItem
from database.models.accounts import UserModel
from database.models.orders import OrderModel
from database.models.payments import PaymentModel, PaymentStatus
from config.dependencies import get_db, get_current_user
from config import settings

router = APIRouter()

stripe.api_key = settings.STRIPE_SECRET_KEY

conf = ConnectionConfig(
    MAIL_USERNAME=settings.BaseAppSettings.EMAIL_HOST_USER,
    MAIL_PASSWORD=settings.BaseAppSettings.EMAIL_HOST_PASSWORD,
    MAIL_FROM=settings.BaseAppSettings.EMAIL_HOST_USER,
    MAIL_PORT=settings.BaseAppSettings.EMAIL_PORT,
    MAIL_SERVER=settings.BaseAppSettings.EMAIL_HOST,
    MAIL_TLS=settings.BaseAppSettings.EMAIL_USE_TLS,
    MAIL_SSL=False,
    USE_CREDENTIALS=True,
)


async def create_stripe_payment_intent(amount: Decimal):
    """
    Creates a Stripe payment intent.
    """
    try:
        intent = stripe.PaymentIntent.create(
            amount=int(amount * 100),
            currency="usd",
            payment_method_types=["card"],
        )
        return intent
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")


async def send_payment_email(user_email: str, amount: float):
    """
    Sends a payment confirmation email.
    """
    message = MessageSchema(
        subject="Payment Confirmation",
        recipients=[user_email],
        body=f"Your payment of ${amount} was successful!",
        subtype="plain",
    )
    fm = FastMail(conf)
    await fm.send_message(message)


@router.post("/payments/", response_model=Payment)
async def create_payment(
    payment: Payment,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """
    Creates a new payment and sends a confirmation email.
    """
    result = await db.execute(select(OrderModel).filter(OrderModel.id == payment.order_id))
    order = result.scalars().first()
    if not order or order.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Order not found")

    if payment.amount != order.total_amount:
        raise HTTPException(status_code=400, detail="Amount does not match order total")

    if payment.payment_method not in ["card", "paypal"]:
        raise HTTPException(status_code=400, detail="Unsupported payment method")

    stripe_response = await create_stripe_payment_intent(payment.amount)
    if stripe_response.get("status") == "requires_payment_method":
        new_payment = PaymentModel(
            user_id=current_user.id,
            order_id=payment.order_id,
            amount=payment.amount,
            status=PaymentStatus.successful,
            external_payment_id=stripe_response.get("id"),
        )
        db.add(new_payment)
        await db.commit()
        await db.refresh(new_payment)

        # Add PaymentItems
        for item in payment.payment_items:
            payment_item = PaymentItem(
                payment_id=new_payment.id,
                order_item_id=item.order_item_id,
                price_at_payment=item.price_at_payment,
            )
            db.add(payment_item)
        await db.commit()

        # Send payment confirmation email
        await send_payment_email(current_user.email, payment.amount)

        return new_payment
    else:
        raise HTTPException(status_code=400, detail="Payment failed. Try a different method.")


@router.get("/payments/history/", response_model=List[Payment])
async def get_payment_history(db: AsyncSession = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    """
    Retrieves the payment history for the current user.
    """
    result = await db.execute(
        select(PaymentModel).filter(PaymentModel.user_id == current_user.id).order_by(PaymentModel.created_at.desc())
    )
    return result.scalars().all()


@router.get("/admin/payments/", response_model=List[Payment])
async def get_admin_payment_history(
    user_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    status: Optional[PaymentStatus] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves the payment history for administrators with optional filtering.
    """
    query = select(PaymentModel)
    if user_id:
        query = query.filter(PaymentModel.user_id == user_id)
    if start_date and end_date:
        query = query.filter(PaymentModel.created_at.between(start_date, end_date))
    if status:
        query = query.filter(PaymentModel.status == status)

    result = await db.execute(query)
    return result.scalars().all()


@router.post("/stripe/webhook/")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Handles Stripe webhook events and sends a payment confirmation email.
    """
    payload = await request.body()
    sig_header = request.headers.get("Stripe-Signature")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
    except (ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(status_code=400, detail="Invalid webhook request")

    if event["type"] == "payment_intent.succeeded":
        payment_intent = event["data"]["object"]
        external_payment_id = payment_intent["id"]

        result = await db.execute(select(PaymentModel).filter(PaymentModel.external_payment_id == external_payment_id))
        payment = result.scalars().first()

        if payment:
            payment.status = PaymentStatus.successful
            order_result = await db.execute(select(OrderModel).filter(OrderModel.id == payment.order_id))
            order = order_result.scalars().first()
            if order:
                order.status = "Paid"
                await db.commit()

            background_tasks.add_task(send_payment_email, payment.user.email, payment.amount)

    elif event["type"] == "payment_intent.payment_failed":
        payment_intent = event["data"]["object"]
        external_payment_id = payment_intent["id"]

        result = await db.execute(select(PaymentModel).filter(PaymentModel.external_payment_id == external_payment_id))
        payment = result.scalars().first()

        if payment:
            payment.status = PaymentStatus.canceled
            await db.commit()

    return {"status": "success"}
