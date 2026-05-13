import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from api.rate_limit import limiter
from api.schemas.verification_rule import RuleCreateRequest, RuleUpdateRequest, RuleResponse
from api.src.application.use_cases.verification_rule import (
    CreateRuleCommand,
    CreateRuleUseCase,
    DeleteRuleUseCase,
    GetRuleUseCase,
    ListRulesUseCase,
    UpdateRuleCommand,
    UpdateRuleUseCase,
)
from api.dependencies import (
    get_create_rule_use_case,
    get_delete_rule_use_case,
    get_get_rule_use_case,
    get_list_rules_use_case,
    get_update_rule_use_case,
    require_min_role,
)
from api.src.domain.enums import UserRole
from domain.entities.user import User
from domain.exceptions import EntityNotFoundError

router = APIRouter(prefix="/profiles/{profile_id}/rules", tags=["Verification Rules"])


@router.post("", response_model=RuleResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def create_rule(
    req: Request,
    profile_id: uuid.UUID,
    request: RuleCreateRequest,
    use_case: Annotated[CreateRuleUseCase, Depends(get_create_rule_use_case)],
    _current_user: Annotated[User, require_min_role(UserRole.MANAGER)],
):
    try:
        return await use_case.execute(
            CreateRuleCommand(
                profile_id=profile_id,
                rule_template=request.rule_template,
                severity=request.severity,
                params=request.params,
                connector_instance_id=request.connector_instance_id,
                display_order=request.display_order,
            )
        )
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.get("", response_model=list[RuleResponse])
async def list_rules(
    profile_id: uuid.UUID,
    use_case: Annotated[ListRulesUseCase, Depends(get_list_rules_use_case)],
    _current_user: Annotated[User, require_min_role(UserRole.VIEWER)],
):
    try:
        return await use_case.execute(profile_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/{rule_id}", response_model=RuleResponse)
async def get_rule(
    profile_id: uuid.UUID,
    rule_id: uuid.UUID,
    use_case: Annotated[GetRuleUseCase, Depends(get_get_rule_use_case)],
    _current_user: Annotated[User, require_min_role(UserRole.VIEWER)],
):
    try:
        return await use_case.execute(profile_id=profile_id, rule_id=rule_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch("/{rule_id}", response_model=RuleResponse)
async def update_rule(
    profile_id: uuid.UUID,
    rule_id: uuid.UUID,
    request: RuleUpdateRequest,
    use_case: Annotated[UpdateRuleUseCase, Depends(get_update_rule_use_case)],
    _current_user: Annotated[User, require_min_role(UserRole.MANAGER)],
):
    try:
        return await use_case.execute(
            UpdateRuleCommand(
                rule_id=rule_id,
                profile_id=profile_id,
                rule_template=request.rule_template,
                severity=request.severity,
                params=request.params,
                connector_instance_id=request.connector_instance_id,
                display_order=request.display_order,
                is_active=request.is_active,
            )
        )
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(
    profile_id: uuid.UUID,
    rule_id: uuid.UUID,
    use_case: Annotated[DeleteRuleUseCase, Depends(get_delete_rule_use_case)],
    _current_user: Annotated[User, require_min_role(UserRole.MANAGER)],
):
    try:
        await use_case.execute(profile_id=profile_id, rule_id=rule_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
