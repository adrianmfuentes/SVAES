from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from application.use_cases.auth_use_cases import LoginUseCase, LoginCommand


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    use_case: Annotated[LoginUseCase, Depends()],
):
    try:
        command = LoginCommand(email=request.email, password_plain=request.password)
        token = await use_case.execute(command)
        return TokenResponse(access_token=token)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
