import os

from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

import stripe

# from fastapi_mail import FastMail, MessageSchema, ConnectionConfig

from schemas.payments import Payment, PaymentItem
from database.models.accounts import UserModel
from database.models.orders import OrderModel
from database.models.payments import PaymentModel, PaymentStatus
from config.dependencies import get_current_user
from database import get_db
from config import settings as settings

router = APIRouter()

# stripe.api_key = settings.BaseAppSettings.STRIPE_SECRET_KEY
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# conf = ConnectionConfig(
#     MAIL_USERNAME=settings.BaseAppSettings.EMAIL_HOST_USER,
#     MAIL_PASSWORD=settings.BaseAppSettings.EMAIL_HOST_PASSWORD,
#     MAIL_FROM=settings.BaseAppSettings.EMAIL_HOST_USER,
#     MAIL_PORT=settings.BaseAppSettings.EMAIL_PORT,
#     MAIL_SERVER=settings.BaseAppSettings.EMAIL_HOST,
#     MAIL_TLS=settings.BaseAppSettings.EMAIL_USE_TLS,
#     MAIL_SSL=False,
#     USE_CREDENTIALS=True,
# )


async def create_stripe_payment_intent(amount: Decimal):
    """
    Creates a Stripe payment intent with the given amount.
    :param amount: The payment amount in USD.
    :return: The Stripe payment intent object.
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


# async def send_payment_email(user_email: str, amount: float):
#     """
#     Sends a payment confirmation email to the user.
#     :param user_email: The email address of the recipient.
#     :param amount: The payment amount.
#     """
#     message = MessageSchema(
#         subject="Payment Confirmation",
#         recipients=[user_email],
#         body=f"Your payment of ${amount} was successful!",
#         subtype="plain",
#     )
#     fm = FastMail(conf)
#     await fm.send_message(message)


# async def send_refund_email(user_email: str, amount: float):
#     """
#     Sends a refund confirmation email to the user.
#     :param user_email: The email address of the recipient.
#     :param amount: The refunded amount.
#     """
#     message = MessageSchema(
#         subject="Refund Processed",
#         recipients=[user_email],
#         body=f"Your refund of ${amount} has been processed successfully.",
#         subtype="plain",
#     )
#     fm = FastMail(conf)
#     await fm.send_message(message)


# async def send_cancellation_email(user_email: str, amount: float):
#     """
#     Sends a payment cancellation email to the user.
#     :param user_email: The email address of the recipient.
#     :param amount: The canceled payment amount.
#     """
#     message = MessageSchema(
#         subject="Payment Canceled",
#         recipients=[user_email],
#         body=f"Your payment of ${amount} has been canceled.",
#         subtype="plain",
#     )
#     fm = FastMail(conf)
#     await fm.send_message(message)


@router.post("/payments/", response_model=Payment)
async def create_payment(
    payment: Payment,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """
    Creates a new payment and sends a confirmation email to the user.
    :param payment: The payment details.
    :param db: The database session.
    :param current_user: The currently authenticated user.
    :return: The created payment object.
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
    payment_status = stripe_response.get("status")

    if payment_status == "succeeded":
        new_payment_status = PaymentStatus.successful
    elif payment_status == "canceled":
        new_payment_status = PaymentStatus.canceled
    else:
        raise HTTPException(status_code=400, detail="Payment failed or requires action.")

    new_payment = PaymentModel(
        user_id=current_user.id,
        order_id=payment.order_id,
        amount=payment.amount,
        status=new_payment_status,
        external_payment_id=stripe_response.get("id"),
    )
    db.add(new_payment)
    await db.commit()
    await db.refresh(new_payment)

    for item in payment.payment_items:
        payment_item = PaymentItem(
            payment_id=new_payment.id,
            order_item_id=item.order_item_id,
            price_at_payment=item.price_at_payment,
        )
        db.add(payment_item)
    await db.commit()

    if new_payment_status == PaymentStatus.successful:
        await send_payment_email(current_user.email, payment.amount)
    elif new_payment_status == PaymentStatus.canceled:
        await send_cancellation_email(current_user.email, payment.amount)

    return new_payment


@router.post("/payments/{payment_id}/refund/")
async def refund_payment(
    payment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """
    Processes a refund for a successful payment.
    :param payment_id: The ID of the payment to refund.
    :param db: The database session.
    :param current_user: The currently authenticated user.
    :param background_tasks: Background tasks handler for sending emails.
    :return: A message indicating the refund status.
    """
    result = await db.execute(
        select(PaymentModel).filter(PaymentModel.id == payment_id, PaymentModel.user_id == current_user.id)
    )
    payment = result.scalars().first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    if payment.status != PaymentStatus.successful:
        raise HTTPException(status_code=400, detail="Only successful payments can be refunded")
    try:
        refund = stripe.Refund.create(payment_intent=payment.external_payment_id)
        if refund.status == "succeeded":
            payment.status = PaymentStatus.refunded
            await db.commit()
            background_tasks.add_task(send_refund_email, current_user.email, payment.amount)
            return {"message": "Refund successful"}
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=500, detail=f"Stripe refund error: {str(e)}")


@router.get("/payments/history/", response_model=List[Payment])
async def get_payment_history(db: AsyncSession = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    """
    Retrieves the payment history for the currently authenticated user.
    :param db: The database session.
    :param current_user: The currently authenticated user.
    :return: A list of past payments.
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
    Retrieve the payment history for administrators with optional filters.

    :param user_id: Filter payments by user ID.
    :param start_date: Filter payments created after this date (inclusive).
    :param end_date: Filter payments created before this date (inclusive).
    :param status: Filter payments by status.
    :param db: Database session dependency.
    :return: List of payments matching the filters.
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
    request: Request, db: AsyncSession = Depends(get_db), background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Handle incoming Stripe webhook events.

    :param request: The incoming HTTP request containing the webhook payload.
    :param db: Database session dependency.
    :param background_tasks: Background task handler for sending emails.
    :return: JSON response indicating success or failure.
    """
    payload = await request.body()
    sig_header = request.headers.get("Stripe-Signature")
    if sig_header is None:
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header")
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
    except (ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(status_code=400, detail="Invalid webhook request")

    if event["type"] == "payment_intent.succeeded":
        """
        Handle successful payment intent events.
        """
        payment_intent = event["data"]["object"]
        external_payment_id = payment_intent["id"]
        result = await db.execute(select(PaymentModel).filter(PaymentModel.external_payment_id == external_payment_id))
        payment = result.scalars().first()
        if payment:
            payment.status = PaymentStatus.successful
            await db.commit()
            background_tasks.add_task(send_payment_email, payment.user.email, payment.amount)
    elif event["type"] == "charge.refunded":
        """
        Handle charge refunded events.
        """
        charge = event["data"]["object"]
        external_payment_id = charge["payment_intent"]
        result = await db.execute(select(PaymentModel).filter(PaymentModel.external_payment_id == external_payment_id))
        payment = result.scalars().first()
        if payment:
            payment.status = PaymentStatus.refunded
            await db.commit()
            background_tasks.add_task(send_refund_email, payment.user.email, payment.amount)
    elif event["type"] == "payment_intent.canceled":
        """
        Handle canceled payment intent events.
        """
        payment_intent = event["data"]["object"]
        external_payment_id = payment_intent["id"]
        result = await db.execute(select(PaymentModel).filter(PaymentModel.external_payment_id == external_payment_id))
        payment = result.scalars().first()
        if payment:
            payment.status = PaymentStatus.canceled
            await db.commit()
            background_tasks.add_task(send_cancellation_email, payment.user.email, payment.amount)
    return {"status": "success"}
