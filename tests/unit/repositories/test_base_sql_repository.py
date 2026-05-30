import pytest
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

pytestmark = pytest.mark.unit


class FakeEntity:
    def __init__(self, id):
        self.id = id


class FakeModel:
    id = None


class TestBaseSqlRepository:
    def test_abstract_methods_raise_not_implemented(self):
        from infrastructure.secondary.database.repositories.base_sql_repository import (
            BaseSqlRepository,
        )

        repo = BaseSqlRepository()
        repo.model_class = FakeModel
        repo.entity_class = FakeEntity

        with pytest.raises(NotImplementedError):
            repo._model_to_entity(None)

        with pytest.raises(NotImplementedError):
            repo._entity_to_model_attrs(None)

    async def test_create_method(self):
        from infrastructure.secondary.database.repositories.base_sql_repository import (
            BaseSqlRepository,
        )

        entity = FakeEntity(uuid4())
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        mock_session.add = MagicMock()

        class TestRepo(BaseSqlRepository):
            model_class = FakeModel
            entity_class = FakeEntity

            def _model_to_entity(self, row):
                return row

            def _entity_to_model_attrs(self, entity):
                return {"extra": "attr"}

        @asynccontextmanager
        async def _scope():
            yield mock_session

        with patch(
            "infrastructure.secondary.database.repositories.base_sql_repository._session_scope",
            new=_scope,
        ):
            repo = TestRepo()
            with patch.object(repo, "model_class", create=True) as mock_model:
                mock_model_instance = MagicMock()
                mock_model.return_value = mock_model_instance

                result = await repo._create(entity)
                assert result is not None
                mock_session.add.assert_called_once()
                mock_session.commit.assert_called_once()

    async def test_get_by_id_returns_entity(self):
        from infrastructure.secondary.database.repositories.base_sql_repository import (
            BaseSqlRepository,
        )

        entity_id = uuid4()
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        row = MagicMock()
        row.id = entity_id

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = row
        mock_session.execute = AsyncMock(return_value=result_mock)

        class TestRepo(BaseSqlRepository):
            model_class = FakeModel
            entity_class = FakeEntity

            def _model_to_entity(self, row):
                return FakeEntity(row.id)

            def _entity_to_model_attrs(self, entity):
                return {"id": entity.id}

        @asynccontextmanager
        async def _scope():
            yield mock_session

        with patch(
            "infrastructure.secondary.database.repositories.base_sql_repository._session_scope",
            new=_scope,
        ):
            with patch(
                "infrastructure.secondary.database.repositories.base_sql_repository.select",
                return_value=MagicMock(),
            ):
                repo = TestRepo()
                result = await repo._get_by_id(entity_id)
                assert result is not None
                assert result.id == entity_id

    async def test_get_by_id_returns_none(self):
        from infrastructure.secondary.database.repositories.base_sql_repository import (
            BaseSqlRepository,
        )

        mock_session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=result_mock)

        class TestRepo(BaseSqlRepository):
            model_class = FakeModel
            entity_class = FakeEntity

            def _model_to_entity(self, row):
                return row

            def _entity_to_model_attrs(self, entity):
                return {}

        @asynccontextmanager
        async def _scope():
            yield mock_session

        with patch(
            "infrastructure.secondary.database.repositories.base_sql_repository._session_scope",
            new=_scope,
        ):
            with patch(
                "infrastructure.secondary.database.repositories.base_sql_repository.select",
                return_value=MagicMock(),
            ):
                repo = TestRepo()
                result = await repo._get_by_id(uuid4())
                assert result is None

    async def test_list_all_returns_entities(self):
        from infrastructure.secondary.database.repositories.base_sql_repository import (
            BaseSqlRepository,
        )

        mock_session = AsyncMock()
        row = MagicMock()
        row.id = uuid4()

        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [row]
        mock_session.execute = AsyncMock(return_value=result_mock)

        class TestRepo(BaseSqlRepository):
            model_class = FakeModel
            entity_class = FakeEntity

            def _model_to_entity(self, row):
                return FakeEntity(row.id)

            def _entity_to_model_attrs(self, entity):
                return {}

        @asynccontextmanager
        async def _scope():
            yield mock_session

        with patch(
            "infrastructure.secondary.database.repositories.base_sql_repository._session_scope",
            new=_scope,
        ):
            with patch(
                "infrastructure.secondary.database.repositories.base_sql_repository.select",
                return_value=MagicMock(),
            ):
                repo = TestRepo()
                results = await repo._list_all()
                assert len(results) == 1

    async def test_delete_removes_entity(self):
        from infrastructure.secondary.database.repositories.base_sql_repository import (
            BaseSqlRepository,
        )

        entity_id = uuid4()
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.delete = AsyncMock()
        model = MagicMock()
        model.id = entity_id
        mock_session.get = AsyncMock(return_value=model)

        class TestRepo(BaseSqlRepository):
            model_class = FakeModel
            entity_class = FakeEntity

            def _model_to_entity(self, row):
                return row

            def _entity_to_model_attrs(self, entity):
                return {}

        @asynccontextmanager
        async def _scope():
            yield mock_session

        with patch(
            "infrastructure.secondary.database.repositories.base_sql_repository._session_scope",
            new=_scope,
        ):
            repo = TestRepo()
            await repo._delete(entity_id)
            mock_session.delete.assert_called_once_with(model)
            mock_session.commit.assert_called_once()

    async def test_delete_not_found_raises_error(self):
        from infrastructure.secondary.database.repositories.base_sql_repository import (
            BaseSqlRepository,
        )

        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=None)

        class TestRepo(BaseSqlRepository):
            model_class = FakeModel
            entity_class = FakeEntity

            def _model_to_entity(self, row):
                return row

            def _entity_to_model_attrs(self, entity):
                return {}

        @asynccontextmanager
        async def _scope():
            yield mock_session

        with patch(
            "infrastructure.secondary.database.repositories.base_sql_repository._session_scope",
            new=_scope,
        ):
            repo = TestRepo()
            with pytest.raises(ValueError, match="FakeEntity not found"):
                await repo._delete(uuid4())
