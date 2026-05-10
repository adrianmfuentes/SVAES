from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from api.rate_limit import limiter
from api.schemas.auth import LoginRequest, TokenResponse
from application.use_cases.auth_use_cases import LoginUseCase, LoginCommand
from api.dependencies import get_login_use_case

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(
    request: Request,
    body: LoginRequest,
    use_case: Annotated[LoginUseCase, Depends(get_login_use_case)],
):
    try:
        command = LoginCommand(email=body.email, password_plain=body.password)
        token = await use_case.execute(command)
        return TokenResponse(access_token=token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
