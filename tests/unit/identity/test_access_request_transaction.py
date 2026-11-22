from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio.engine import create_async_engine

from features.identity.application.use_cases.create_access_request import CreateAccessRequest
from features.organizations.application.use_cases.organization_service import OrganizationService
from shared.infrastructure.database.models import Base
from shared.infrastructure.database.models.access_request_model import AccessRequestModel
from shared.infrastructure.database.models.organization_model import OrganizationModel
from shared.infrastructure.database.models.user_membership_model import UserMembershipModel
from shared.infrastructure.database.models.user_model import UserModel
from features.identity.infrastructure.persistence.access_request_repository import SqlAccessRequestRepository
from features.organizations.infrastructure.persistence.organization_repository import SqlOrganizationRepository
from features.identity.infrastructure.persistence.user_membership_repository import SqlUserMembershipRepository
from features.identity.infrastructure.persistence.user_repository import SqlUserRepository
from shared.infrastructure.sql_unit_of_work import SqlUnitOfWork
from shared.infrastructure.system_clock import SystemClock


@pytest.mark.parametrize("fail_before_commit", [True, False])
async def test_access_request_commits_all_records_before_sending_email(fail_before_commit):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    models = [UserModel, OrganizationModel, UserMembershipModel, AccessRequestModel]
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all, tables=[model.__table__ for model in models])

        unit = SqlUnitOfWork(sessions())
        users = SqlUserRepository(unit.session)
        requests = SqlAccessRequestRepository(unit.session)
        mailer = AsyncMock()
        use_case = CreateAccessRequest(
            requests=requests,
            users=users,
            organizations=OrganizationService(
                organization_repository=SqlOrganizationRepository(unit.session),
                project_repository=Mock(),
                user_repository=users,
                user_membership_repository=SqlUserMembershipRepository(unit.session),
                audit_logger=Mock(),
            ),
            password_hasher=Mock(hash_password=Mock(return_value="test-hash")),
            mailer=mailer,
            clock=SystemClock(),
            unit_of_work=unit,
        )

        async def row_counts():
            async with sessions() as session:
                return [await session.scalar(select(func.count()).select_from(model)) for model in models]

        counts_at_activation = []

        async def check_activation_after_commit(*_args):
            counts_at_activation.extend(await row_counts())

        mailer.send_activation_email.side_effect = check_activation_after_commit
        args = ("Ada", "ada@example.test", "Example Team", None)
        if fail_before_commit:
            requests.create = AsyncMock(side_effect=RuntimeError("insert failed"))
            with pytest.raises(RuntimeError, match="insert failed"):
                await use_case.execute(*args)
            assert await row_counts() == [0, 0, 0, 0]
            mailer.send_activation_email.assert_not_called()
        else:
            await use_case.execute(*args)
            assert await row_counts() == [1, 1, 1, 1]
            mailer.send_activation_email.assert_awaited_once()
            assert counts_at_activation == [1, 1, 1, 1]
    finally:
        await engine.dispose()
