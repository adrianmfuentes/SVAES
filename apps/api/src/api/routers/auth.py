from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from application.use_cases.auth_use_cases import LoginUseCase, LoginCommand
from api.dependencies import get_login_use_case

class LoginRequest(BaseModel):
    """Request model for the login endpoint.
    Attributes:
        email (str): The user's email address used for authentication.
        password (str): The user's plaintext password used for authentication.
    """
    email: str
    password: str

class TokenResponse(BaseModel):
    """Response model for the login endpoint.
    Attributes:
        access_token (str): The JWT access token issued upon successful authentication.
        token_type (str): The type of the token (default is "bearer").
    """
    access_token: str
    token_type: str = "bearer"

router = APIRouter(
    prefix="/auth", 
    tags=["Auth"]
)

@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest, # The login request containing the user's email and password.
    use_case: Annotated[
        LoginUseCase, # The login use case, responsible for authenticating the user and issuing a token.
        Depends(get_login_use_case) # Dependency injection to provide the login use case instance.
    ]
):
    """Endpoint for user login and token issuance.
    Args:
        request (LoginRequest): The request body containing the user's email and password.
        use_case (LoginUseCase): The use case for handling login logic, injected via FastAPI's dependency injection system.
    Raises:
        HTTPException: If authentication fails, an HTTP 401 Unauthorized error is raised with the error message.
    Returns:
        TokenResponse: A response containing the access token and token type if authentication is successful.
    """
    try:
        command = LoginCommand(email=request.email, password_plain=request.password)
        token = await use_case.execute(command)
        return TokenResponse(access_token=token)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
