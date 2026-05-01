from django.contrib.auth import authenticate, login, logout
from ninja import Router
from ..schemas.auth import LoginIn, AuthResponse, UserOut, ErrorOut
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
