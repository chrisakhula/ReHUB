from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.audit.service import audit
from app.core.database import get_db
from app.core.permissions import current_user
from app.schemas.identity import (
    ChangePasswordIn,
    LoginIn,
    ResetPasswordIn,
    ResetRequestIn,
    UserOut,
    user_out,
)
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=UserOut)
def login(
    data: LoginIn,
    request: Request,
    response: Response,
    db: Session = Depends(get_db, scope="function"),
):
    return user_out(AuthService(db, request).login(data, response))


@router.post("/refresh", response_model=UserOut)
def refresh(request: Request, response: Response, db: Session = Depends(get_db, scope="function")):
    return user_out(AuthService(db, request).refresh(response))


@router.get("/me", response_model=UserOut)
def me(user=Depends(current_user)):
    return user_out(user)


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db, scope="function"),
    user=Depends(current_user),
):
    request.state.auth_session.revoked = True
    audit(db, request, "auth.logout", "user", user, user.id)
    clear_cookies(response)
    return {"message": "Signed out"}


def clear_cookies(response):
    for name in ("access_token", "refresh_token"):
        response.delete_cookie(name, path="/api/v1")
    response.delete_cookie("csrf_token", path="/")


@router.post("/change-password")
def change_password(
    data: ChangePasswordIn,
    request: Request,
    response: Response,
    db: Session = Depends(get_db, scope="function"),
    user=Depends(current_user),
):
    AuthService(db, request).change_password(user, data)
    clear_cookies(response)
    return {"message": "Password updated. Please sign in again."}


@router.post("/request-reset")
def request_reset(
    data: ResetRequestIn, request: Request, db: Session = Depends(get_db, scope="function")
):
    AuthService(db, request).request_reset(data.email)
    return {
        "message": (
            "If the account is eligible, a reset link will be sent. "
            "Contact your administrator if it does not arrive."
        )
    }


@router.post("/reset-password")
def reset_password(
    data: ResetPasswordIn, request: Request, db: Session = Depends(get_db, scope="function")
):
    AuthService(db, request).reset_password(data)
    return {"message": "Password updated. Please sign in."}
