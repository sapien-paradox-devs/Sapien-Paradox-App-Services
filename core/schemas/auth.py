from ninja import Schema

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

class ErrorOut(Schema):
    detail: str
