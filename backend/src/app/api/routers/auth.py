from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import AuthServiceDep
from app.api.rate_limit import rate_limit
from app.api.schemas import TokenOut, UserOut, UserRegister

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit("login"))],
)
def register(payload: UserRegister, auth: AuthServiceDep) -> UserOut:
    user = auth.register(payload.email, payload.password, payload.full_name)
    return UserOut.model_validate(user)


@router.post("/login", dependencies=[Depends(rate_limit("login"))])
def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    auth: AuthServiceDep,
) -> TokenOut:
    """OAuth2 password flow: send `username` (the email) and `password` as form fields."""
    return TokenOut(access_token=auth.login(form.username, form.password))
