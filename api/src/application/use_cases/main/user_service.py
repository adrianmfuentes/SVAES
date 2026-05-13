from typing import Optional, List
from uuid import UUID, uuid4
from application.ports.input.i_user_service import IUserService
from application.ports.output.i_user_repository import IUserRepository
from application.ports.output.i_organization_repository import IOrganizationRepository
from application.ports.output.i_password_hasher import IPasswordHasher
from domain.entities.user import User
from domain.enums import UserRole
from domain.exceptions import EntityNotFoundError, DuplicateEntityError, ValidationError

"""
Este módulo define el servicio de usuario, que es responsable de gestionar los usuarios dentro del sistema. Incluye la lógica de negocio para obtener 
un usuario por ID, actualizar el perfil de un usuario, cambiar la contraseña, listar los usuarios de una organización, invitar a un nuevo usuario a 
una organización, actualizar el rol de un usuario dentro de una organización, y eliminar a un usuario de una organización.
"""
class UserService(IUserService):
    def __init__(
        self,
        user_repository: IUserRepository,
        organization_repository: IOrganizationRepository,
        password_hasher: IPasswordHasher,
    ) -> None:
        self._user_repo = user_repository
        self._org_repo = organization_repository
        self._password_hasher = password_hasher


    async def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        return await self._user_repo.get_by_id(user_id)


    async def update_profile(self, user_id: UUID, display_name: Optional[str] = None) -> User:
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise EntityNotFoundError(f"Usuario no encontrado: {user_id}")

        if display_name:
            user.display_name = display_name

        return await self._user_repo.update(user)


    async def change_password(self, user_id: UUID, current_password: str, new_password: str) -> bool:
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise EntityNotFoundError(f"Usuario no encontrado: {user_id}")

        if not self._password_hasher.verify_password(current_password, user.hashed_password):
            return False

        user.hashed_password = self._password_hasher.hash_password(new_password)
        await self._user_repo.update(user)
        return True


    async def list_organization_users(self, organization_id: UUID, skip: int = 0, limit: int = 50) -> List[User]:
        return await self._user_repo.list_all(organization_id=organization_id, skip=skip, limit=limit)


    async def invite_user(self, organization_id: UUID, email: str, role: UserRole) -> User:
        org = await self._org_repo.get_by_id(organization_id)
        if not org:
            raise EntityNotFoundError(f"Organización no encontrada: {organization_id}")

        existing = await self._user_repo.get_by_email(email)
        if existing:
            raise DuplicateEntityError(f"Ya existe un usuario con email: {email}")

        temp_password = self._password_hasher.hash_password(str(uuid4())[:8])

        user = User(
            id=uuid4(),
            email=email,
            hashed_password=temp_password,
            display_name=email.split("@")[0],
            role=role,
            organization_id=organization_id,
            is_active=False,
        )
        return await self._user_repo.create(user)


    async def update_user_role(self, user_id: UUID, organization_id: UUID, new_role: UserRole) -> User:
        user = await self._user_repo.get_by_id(user_id)
        if not user or user.organization_id != organization_id:
            raise EntityNotFoundError(f"Usuario no encontrado en esta organización: {user_id}")

        org = await self._org_repo.get_by_id(organization_id)
        if not org:
            raise EntityNotFoundError(f"Organización no encontrada: {organization_id}")

        if org.owner_id == user_id:
            raise ValidationError("No se puede cambiar el rol del Owner de la organización")

        user.role = new_role
        return await self._user_repo.update(user)


    async def remove_user_from_organization(self, user_id: UUID, organization_id: UUID) -> None:
        user = await self._user_repo.get_by_id(user_id)
        if not user or user.organization_id != organization_id:
            raise EntityNotFoundError(f"Usuario no encontrado en esta organización: {user_id}")

        org = await self._org_repo.get_by_id(organization_id)
        if not org:
            raise EntityNotFoundError(f"Organización no encontrada: {organization_id}")

        if org.owner_id == user_id:
            raise ValidationError("No se puede eliminar al Owner de la organización")

        user.organization_id = None
        user.role = UserRole.VIEWER
        await self._user_repo.update(user)