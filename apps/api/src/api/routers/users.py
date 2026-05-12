import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from api.rate_limit import limiter
from api.schemas.user import ChangePasswordRequest, UserCreate, UserUpdate, UserResponse
from application.use_cases.user_use_cases import (
    ChangePasswordCommand,
    ChangePasswordUseCase,
    CreateUserUseCase,
    CreateUserCommand,
    GetUserUseCase,
    ListUsersUseCase,
    UpdateUserUseCase,
    UpdateUserCommand,
    DeleteUserUseCase,
)
from api.dependencies import (
    get_change_password_use_case,
    get_create_user_use_case,
    get_get_user_use_case,
    get_list_users_use_case,
    get_update_user_use_case,
    get_delete_user_use_case,
    get_current_user,
    require_min_role,
)
from domain.entities.user import User
from domain.entities.enums import UserRole
from domain.exceptions import EntityNotFoundError, DuplicateEntityError

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: Annotated[User, Depends(get_current_user)]):
    return current_user


@router.patch("/me/password", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("5/minute")
async def change_my_password(
    request: Request,
    body: ChangePasswordRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    use_case: Annotated[ChangePasswordUseCase, Depends(get_change_password_use_case)],
):
    try:
        await use_case.execute(
            ChangePasswordCommand(
                user_id=current_user.id,
                current_password=body.current_password,
                new_password=body.new_password,
            )
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("", status_code=status.HTTP_201_CREATED, response_model=UserResponse)
async def create_user(
    request: UserCreate,
    use_case: Annotated[CreateUserUseCase, Depends(get_create_user_use_case)],
    _current_user: Annotated[User, require_min_role(UserRole.ADMIN)],
):
    try:
        command = CreateUserCommand(
            email=request.email,
            password_plain=request.password,
            role=request.role,
        )
        return await use_case.execute(command)
    except DuplicateEntityError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.get("", response_model=list[UserResponse])
async def list_users(
    use_case: Annotated[ListUsersUseCase, Depends(get_list_users_use_case)],
    _current_user: Annotated[User, require_min_role(UserRole.ADMIN)],
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
):
    return await use_case.execute(skip=skip, limit=limit)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: uuid.UUID,
    use_case: Annotated[GetUserUseCase, Depends(get_get_user_use_case)],
    _current_user: Annotated[User, require_min_role(UserRole.ADMIN)],
):
    try:
        return await use_case.execute(user_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID,
    request: UserUpdate,
    use_case: Annotated[UpdateUserUseCase, Depends(get_update_user_use_case)],
    _current_user: Annotated[User, require_min_role(UserRole.ADMIN)],
):
    try:
        command = UpdateUserCommand(
            user_id=user_id,
            email=request.email,
            role=request.role,
        )
        return await use_case.execute(command)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: uuid.UUID,
    use_case: Annotated[DeleteUserUseCase, Depends(get_delete_user_use_case)],
    _current_user: Annotated[User, require_min_role(UserRole.ADMIN)],
):
    try:
        await use_case.execute(user_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
