from uuid import UUID
from sqlalchemy.orm import Session
from domain.entities.user import User, UserRole
from domain.ports.i_user_repository import IUserRepository
from infrastructure.database.models.user import UserModel

class SqlUserRepository(IUserRepository):
    def __init__(self, session: Session):
        self.session = session

    def save(self, user: User) -> User:
        model = self.session.get(UserModel, user.id)
        if model is None:
            model = UserModel(
                id=user.id,
                email=user.email,
                password_hash=user.hashed_password,
                display_name=user.email,
                is_active=True,
            )
            self.session.add(model)
        else:
            model.email = user.email
            model.password_hash = user.hashed_password
        self.session.flush()
        return user

    def find_by_id(self, user_id: UUID) -> User | None:
        model = self.session.get(UserModel, user_id)
        return self._to_entity(model) if model else None

    def find_by_email(self, email: str) -> User | None:
        model = self.session.query(UserModel).filter_by(email=email).first()
        return self._to_entity(model) if model else None

    def find_by_organization(self, organization_id: UUID) -> list[User]:
        models = (
            self.session.query(UserModel)
            .join(UserModel.memberships)
            .filter_by(organization_id=organization_id)
            .all()
        )
        return [self._to_entity(m) for m in models]

    def _to_entity(self, model: UserModel) -> User:
        return User(
            id=model.id,
            email=model.email,
            hashed_password=model.password_hash,
            role=UserRole.VIEWER,  # El rol real viene de user_membership
            organization_id=model.memberships[0].organization_id if model.memberships else None,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )