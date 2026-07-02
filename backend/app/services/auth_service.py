"""Authentication service — registration & login (design doc Section 3.1)."""
from __future__ import annotations

from fastapi import HTTPException, status

from app.core.security import Role, create_access_token, hash_password, verify_password
from app.models import User
from app.repositories.user_repo import UserRepository
from app.schemas import LoginRequest, RegisterRequest, TokenResponse


class AuthService:
    def __init__(self, db) -> None:
        self.users = UserRepository(db)

    def register(self, payload: RegisterRequest) -> User:
        if payload.role_name not in Role.ALL:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unknown role '{payload.role_name}'.")
        if self.users.get_by_email(payload.email):
            raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered.")
        # Self-service registration may omit a password; default to the demo
        # password so the account can still be logged into later.
        password = payload.password or "Password123"
        user = User(
            email=payload.email,
            full_name=payload.full_name,
            hashed_password=hash_password(password),
            role_name=payload.role_name,
            department=payload.department,
        )
        return self.users.create(user)

    def login(self, payload: LoginRequest) -> TokenResponse:
        user = self.users.get_by_email(payload.email)
        if not user or not verify_password(payload.password, user.hashed_password):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials.")
        token = create_access_token(subject=user.email, role=user.role_name, extra={"uid": user.id})
        return TokenResponse(
            access_token=token, role=user.role_name,
            full_name=user.full_name, email=user.email,
        )
