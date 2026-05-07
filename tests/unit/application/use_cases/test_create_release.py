"""
Test suite para ``CreateReleaseUseCase``.

Una release representa un artefacto de software candidato a ser verificado.
``CreateReleaseUseCase`` crea la entidad con el estado inicial correcto
(``BORRADOR``) y la persiste asociada a un proyecto y un perfil de verificación.

El ciclo de vida de una release sigue una máquina de estados estricta:
    BORRADOR → PENDIENTE → EN_VERIFICACION → COMPLETADA

Este caso de uso ocupa la primera transición: instanciar la release en ``BORRADOR``
antes de que el operador la envíe a verificación.

Estrategia de prueba:
    Pruebas unitarias. Tanto el repositorio de releases (``IReleaseRepository``)
    como el repositorio de organizaciones (``IOrganizationRepository``) se sustituyen
    por ``AsyncMock`` para aislar la lógica de construcción del dominio.

Invariantes clave verificadas:
    - Toda release se crea en estado ``BORRADOR``, sin excepción.
    - Los identificadores de proyecto, perfil, versión y creador se preservan
      tal como los provee el comando.
    - La persistencia se delega exactamente una vez al repositorio de releases.
"""

import uuid
import pytest
from unittest.mock import AsyncMock

from application.use_cases.create_release import CreateReleaseUseCase, CreateReleaseCommand
from domain.entities.enums import ReleaseStatus


class TestCreateReleaseUseCase:
    """
    Pruebas unitarias para ``CreateReleaseUseCase``.

    Verifica que toda release se instancie en estado ``BORRADOR`` con los campos
    correctos y que la persistencia se delegue al repositorio correspondiente.
    """

    def _make_command(self, **kwargs) -> CreateReleaseCommand:
        """
        Construye un ``CreateReleaseCommand`` con valores de prueba por defecto.

        Acepta overrides por clave para facilitar la variación de escenarios
        sin repetir la inicialización completa en cada test.
        """
        defaults = {
            "project_id": uuid.uuid4(),
            "profile_id": uuid.uuid4(),
            "version": "1.0.0",
            "created_by": uuid.uuid4(),
            "description": "Initial release",
        }
        return CreateReleaseCommand(**{**defaults, **kwargs})

    async def test_release_created_with_borrador_status(self):
        """
        Toda release recién creada adopta el estado inicial ``BORRADOR``.

        Given:  Un repositorio de releases configurado para retornar el objeto recibido.
        When:   Se ejecuta ``CreateReleaseUseCase`` con un comando estándar.
        Then:   El estado de la release resultante es ``ReleaseStatus.BORRADOR``,
                conforme al primer eslabón de la máquina de estados del dominio.
        """
        release_repo = AsyncMock()
        org_repo = AsyncMock()
        release_repo.create.side_effect = lambda r: r

        result = await CreateReleaseUseCase(release_repo, org_repo).execute(
            self._make_command()
        )

        assert result.status == ReleaseStatus.BORRADOR

    async def test_release_has_correct_project_and_profile(self):
        """
        Los identificadores de proyecto y perfil se transfieren sin modificación.

        Given:  Un comando con ``project_id`` y ``profile_id`` específicos.
        When:   Se ejecuta el caso de uso.
        Then:   La release resultante referencia exactamente los IDs proporcionados,
                garantizando la trazabilidad correcta dentro del grafo de entidades.
        """
        project_id = uuid.uuid4()
        profile_id = uuid.uuid4()
        release_repo = AsyncMock()
        org_repo = AsyncMock()
        release_repo.create.side_effect = lambda r: r

        result = await CreateReleaseUseCase(release_repo, org_repo).execute(
            self._make_command(project_id=project_id, profile_id=profile_id)
        )

        assert result.project_id == project_id
        assert result.profile_id == profile_id

    async def test_release_has_correct_version_and_creator(self):
        """
        La versión semántica y el identificador del creador se preservan en la entidad.

        Given:  Un comando con ``version="2.5.1"`` y un ``created_by`` específico.
        When:   Se ejecuta el caso de uso.
        Then:   La release resultante expone los valores exactos del comando,
                asegurando la auditoría correcta de quién creó qué versión.
        """
        creator_id = uuid.uuid4()
        release_repo = AsyncMock()
        org_repo = AsyncMock()
        release_repo.create.side_effect = lambda r: r

        result = await CreateReleaseUseCase(release_repo, org_repo).execute(
            self._make_command(version="2.5.1", created_by=creator_id)
        )

        assert result.version == "2.5.1"
        assert result.created_by == creator_id

    async def test_delegates_persistence_to_release_repo(self):
        """
        La entidad se persiste a través de ``IReleaseRepository.create`` exactamente una vez.

        Given:  Un repositorio de releases con ``create`` instrumentado.
        When:   Se ejecuta el caso de uso con un comando válido.
        Then:   ``release_repo.create`` se invoca una sola vez, evitando inserciones
                duplicadas y confirmando que la responsabilidad de persistencia
                no recae en el caso de uso sino en el repositorio.
        """
        release_repo = AsyncMock()
        org_repo = AsyncMock()
        release_repo.create.side_effect = lambda r: r

        await CreateReleaseUseCase(release_repo, org_repo).execute(self._make_command())

        release_repo.create.assert_called_once()
