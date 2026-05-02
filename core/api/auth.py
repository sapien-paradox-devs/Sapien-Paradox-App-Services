from django.contrib.auth import authenticate, login, logout
from ninja import Router
from ..models import Order
from ..schemas.auth import LoginIn, AuthResponse, ErrorOut
from ..schemas.payments import SessionFromCheckoutIn
from ..services import payments as payments_service
from django.http import HttpRequest

router = Router()

@router.post("/login", response={200: AuthResponse, 401: ErrorOut})
def login_view(request: HttpRequest, data: LoginIn):
    user = authenticate(request, email=data.email, password=data.password)
    if user is not None:
        login(request, user)
        return 200, {
            "user": user
        }
    return 401, {"detail": "invalid credentials"}

@router.post("/logout", response={204: None})
def logout_view(request: HttpRequest):
    logout(request)
    return 204, None

@router.post("/session-from-checkout", response={200: AuthResponse, 404: ErrorOut})
def session_from_checkout(request: HttpRequest, data: SessionFromCheckoutIn):
    try:
        user = payments_service.login_from_session(request, data.session_id)
    except Order.DoesNotExist:
        return 404, {"detail": "order not found"}
    return 200, {"user": user}
