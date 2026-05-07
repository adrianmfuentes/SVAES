"""
Test suite para ``ManageProfileUseCase``.

Los perfiles de verificación agrupan conjuntos de reglas que determinan los
criterios de aceptación aplicados a una release. ``ManageProfileUseCase``
encapsula la creación de nuevos perfiles bajo una organización específica.

Un perfil es una entidad con identidad propia (ID único autogenerado), lo que
permite reutilizarlo en múltiples releases dentro del mismo tenant sin duplicar
las reglas asociadas.

Estrategia de prueba:
    Pruebas unitarias. El repositorio ``IProfileRepository`` se sustituye por un
    ``AsyncMock`` para aislar la lógica de construcción de entidades y verificar
    el contrato de persistencia sin dependencias de infraestructura.

Invariantes clave verificadas:
    - El perfil resultante refleja el ``organization_id`` y ``name`` del comando.
    - Cada llamada genera un ID único: dos ejecuciones del mismo comando producen
      entidades con IDs distintos.
    - La persistencia se delega al repositorio exactamente una vez por creación.
"""

import uuid
import pytest
from unittest.mock import AsyncMock

from application.use_cases.manage_profile import ManageProfileUseCase, CreateProfileCommand


class TestManageProfileUseCase:
    """
    Pruebas unitarias para ``ManageProfileUseCase``.

    Valida la construcción correcta de perfiles de verificación, la unicidad de
    sus identificadores y la delegación de la persistencia al repositorio.
    """

    async def test_create_profile_with_correct_org_and_name(self):
        """
        El perfil creado refleja exactamente el ``organization_id`` y ``name`` del comando.

        Given:  Un repositorio que retorna el objeto recibido sin modificación y
                un comando con ``organization_id`` y ``name`` explícitos.
        When:   Se invoca ``ManageProfileUseCase.create_profile``.
        Then:   Los atributos ``organization_id`` y ``name`` del perfil resultante
                coinciden con los provistos en el comando, garantizando la asociación
                correcta del perfil con su tenant propietario.
        """
        org_id = uuid.uuid4()
        repo = AsyncMock()
        repo.create.side_effect = lambda p: p

        result = await ManageProfileUseCase(repo).create_profile(
            CreateProfileCommand(organization_id=org_id, name="Prod Checklist")
        )

        assert result.organization_id == org_id
        assert result.name == "Prod Checklist"

    async def test_create_profile_generates_unique_id(self):
        """
        Dos ejecuciones del mismo comando producen perfiles con IDs distintos.

        Given:  Un repositorio que retorna el objeto recibido y un comando idéntico
                aplicado dos veces consecutivas.
        When:   Se invoca ``create_profile`` dos veces con el mismo comando.
        Then:   Los IDs de los dos perfiles resultantes son diferentes, confirmando
                que la entidad genera su propio UUID en cada instanciación sin
                depender de secuencias externas ni de la base de datos.
        """
        repo = AsyncMock()
        repo.create.side_effect = lambda p: p
        org_id = uuid.uuid4()
        cmd = CreateProfileCommand(organization_id=org_id, name="Profile A")

        r1 = await ManageProfileUseCase(repo).create_profile(cmd)
        r2 = await ManageProfileUseCase(repo).create_profile(cmd)

        assert r1.id != r2.id

    async def test_delegates_persistence_to_repo(self):
        """
        La creación del perfil se delega al repositorio exactamente una vez.

        Given:  Un repositorio con ``create`` instrumentado.
        When:   Se invoca ``create_profile`` con un comando válido.
        Then:   ``repo.create`` se llama una sola vez, confirmando que el caso de
                uso no intenta persistir el perfil por múltiples vías ni reintenta
                la operación ante un primer éxito.
        """
        repo = AsyncMock()
        repo.create.side_effect = lambda p: p

        await ManageProfileUseCase(repo).create_profile(
            CreateProfileCommand(organization_id=uuid.uuid4(), name="QA Profile")
        )

        repo.create.assert_called_once()
