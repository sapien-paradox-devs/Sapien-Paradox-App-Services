import logging

import stripe
from django.conf import settings
from django.contrib.auth import login as auth_login
from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.http import HttpRequest

from ..models import Book, Order, User
from ..schemas.payments import CreateCheckoutSessionIn
from . import grants as grants_service
from . import whatsapp as whatsapp_service

logger = logging.getLogger(__name__)


class EmailAlreadyExists(Exception):
    """Signals 409 from the create-checkout-session endpoint."""


class BookNotFound(Exception):
    """Signals 400 from the create-checkout-session endpoint."""


def create_session(payload: CreateCheckoutSessionIn) -> str:
    """Create a Stripe Checkout Session for `payload` and return its hosted URL."""
    if User.objects.filter(email=payload.email).exists():
        raise EmailAlreadyExists()

    try:
        book = Book.objects.get(slug=payload.book_slug)
    except Book.DoesNotExist as exc:
        raise BookNotFound() from exc

    stripe.api_key = settings.STRIPE_API_KEY
    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=[{
            "price_data": {
                "currency": "usd",
                "product_data": {"name": book.title},
                "unit_amount": book.price_cents,
            },
            "quantity": 1,
        }],
        success_url=f"{settings.FRONTEND_URL}/welcome?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{settings.FRONTEND_URL}/?book_id={book.slug}",
        metadata={
            "email": payload.email,
            "password_hash": make_password(payload.password),
            "full_name": payload.full_name,
            "phone": payload.phone,
            "book_slug": payload.book_slug,
            "pace": payload.pace,
        },
    )
    return session.url


def verify_and_parse_event(payload: bytes, signature: str) -> dict:
    """Verify the Stripe-Signature header and return the parsed event dict."""
    return stripe.Webhook.construct_event(
        payload=payload,
        sig_header=signature,
        secret=settings.STRIPE_WEBHOOK_SECRET,
    )


def fulfill_checkout(session: dict) -> Order:
    """Idempotently create User+Order+chapter-1 grant for a completed checkout.

    Per Q5 lock: User+Order+grant are atomic; the chapter-1 WhatsApp send
    runs post-commit and is best-effort (logged on failure, never blocks
    the 200 to Stripe).
    """
    session_id = session["id"]

    existing = Order.objects.filter(stripe_session_id=session_id).first()
    if existing is not None:
        return existing

    metadata = session["metadata"]
    book = Book.objects.get(slug=metadata["book_slug"])
    amount_cents = session.get("amount_total") or book.price_cents

    with transaction.atomic():
        user = User(
            email=metadata["email"],
            full_name=metadata["full_name"],
            phone=metadata["phone"],
            password=metadata["password_hash"],
        )
        user.save()

        order = Order.objects.create(
            user=user,
            book=book,
            pace=metadata["pace"],
            stripe_session_id=session_id,
            amount_cents=amount_cents,
        )

        created_grants = grants_service.create_for_order(order)

    if created_grants:
        try:
            whatsapp_service.send_chapter(created_grants[0])
        except Exception:
            logger.exception("WhatsApp chapter-1 send failed for order %s", order.id)

    return order


def login_from_session(request: HttpRequest, session_id: str) -> User:
    """Look up Order by Stripe session_id and log its user in via Django session."""
    order = Order.objects.select_related("user").get(stripe_session_id=session_id)
    auth_login(request, order.user)
    return order.user
