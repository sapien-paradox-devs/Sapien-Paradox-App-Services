from ninja import Schema

from ..models import Order


class CreateCheckoutSessionIn(Schema):
    email: str
    password: str
    full_name: str
    phone: str
    book_slug: str
    pace: str


class CreateCheckoutSessionOut(Schema):
    checkout_url: str


class SessionFromCheckoutIn(Schema):
    session_id: str
