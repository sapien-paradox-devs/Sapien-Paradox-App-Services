import stripe
from django.http import HttpRequest
from ninja import Router

from ..schemas.auth import ErrorOut
from ..schemas.payments import CreateCheckoutSessionIn, CreateCheckoutSessionOut
from ..services import payments as payments_service

router = Router()


@router.post(
    "/create-checkout-session",
    response={200: CreateCheckoutSessionOut, 400: ErrorOut, 409: ErrorOut},
)
def create_checkout_session(request: HttpRequest, data: CreateCheckoutSessionIn):
    try:
        url = payments_service.create_session(data)
    except payments_service.EmailAlreadyExists:
        return 409, {"detail": "email already in use"}
    except payments_service.BookNotFound:
        return 400, {"detail": "unknown book"}
    return 200, {"checkout_url": url}


@router.post("/webhook", response={200: dict, 400: ErrorOut})
def stripe_webhook(request: HttpRequest):
    payload = request.body
    signature = request.headers.get("Stripe-Signature", "")

    try:
        event = payments_service.verify_and_parse_event(payload, signature)
    except (stripe.SignatureVerificationError, ValueError):
        return 400, {"detail": "invalid signature"}

    if event["type"] == "checkout.session.completed":
        payments_service.fulfill_checkout(event["data"]["object"])

    return 200, {}
