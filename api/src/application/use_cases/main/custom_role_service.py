from typing import Optional, List
from uuid import UUID, uuid4
from application.ports.input.i_custom_role_service import ICustomRoleService
from application.ports.output.i_custom_role_repository import ICustomRoleRepository
from domain.entities.custom_role import CustomRole
from domain.enums import Permission
from domain.exceptions import EntityNotFoundError, DuplicateEntityError, ValidationError

"""
Este módulo define el servicio de roles personalizados, que es responsable de gestionar los roles personalizados dentro del sistema. Incluye la lógica de
negocio para crear un nuevo rol personalizado, obtener un rol por ID, listar los roles de una organización, actualizar un rol personalizado, y eliminar 
un rol personalizado.
"""
class CustomRoleService(ICustomRoleService):
    def __init__(self, custom_role_repository: ICustomRoleRepository) -> None:
        self._repo = custom_role_repository


    async def create_role(self, organization_id: UUID, name: str, permissions: List[Permission]) -> CustomRole:
        existing = await self._repo.list_by_organization(organization_id)
        if any(r.name == name for r in existing):
            raise DuplicateEntityError(f"Ya existe un rol con el nombre: {name}")

        if not permissions:
            raise ValidationError("El rol debe tener al menos un permiso")

        role = CustomRole(
            organization_id=organization_id,
            name=name,
            permissions=permissions,
        )
        return await self._repo.create(role)


    async def get_role(self, role_id: UUID) -> Optional[CustomRole]:
        return await self._repo.get_by_id(role_id)


    async def list_roles(self, organization_id: UUID) -> List[CustomRole]:
        return await self._repo.list_by_organization(organization_id)


    async def update_role(
        self,
        role_id: UUID,
        name: Optional[str] = None,
        permissions: Optional[List[Permission]] = None,
        is_active: Optional[bool] = None,
    ) -> CustomRole:
        role = await self._repo.get_by_id(role_id)
        if not role:
            raise EntityNotFoundError(f"Rol no encontrado: {role_id}")

        if name:
            role.name = name

        if permissions is not None:
            if not permissions:
                raise ValidationError("El rol debe tener al menos un permiso")
            role.permissions = permissions

        if is_active is not None:
            role.is_active = is_active

        return await self._repo.update(role)


    async def delete_role(self, role_id: UUID) -> None:
        role = await self._repo.get_by_id(role_id)
        if not role:
            raise EntityNotFoundError(f"Rol no encontrado: {role_id}")

        await self._repo.delete(role_id)