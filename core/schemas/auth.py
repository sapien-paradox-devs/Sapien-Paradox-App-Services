from ninja import Schema
from typing import Optional

class LoginIn(Schema):
    email: str
    password: str

class UserOut(Schema):
    id: int
    email: str
    full_name: str
    phone: str
    role: str

class AuthResponse(Schema):
    user: UserOut
