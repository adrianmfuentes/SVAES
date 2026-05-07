"""
Test suite para ``CreateOrganizationUseCase`` y ``ListOrganizationsUseCase``.

Las organizaciones son la raíz de la jerarquía de tenants en SVAES: cada proyecto,
release y conector pertenece a una organización. Estos casos de uso encapsulan
la lógica de creación y listado de tenants, delegando la persistencia en
``IOrganizationRepository``.

Estrategia de prueba:
    Pruebas unitarias puras. El repositorio se reemplaza por un ``AsyncMock``
    para verificar exclusivamente la lógica de construcción de entidades y los
    contratos de llamada, sin dependencias de base de datos.

Invariantes clave verificadas:
    - La entidad ``Organization`` se construye con los campos ``name`` y ``slug``
      tal y como los provee el comando.
    - El plan por defecto de una nueva organización es ``"free"``.
    - El listado de organizaciones filtra siempre por ``active_only=True``,
      evitando exponer tenants desactivados.
    - Cuando no existen organizaciones activas, el caso de uso retorna lista vacía
      sin lanzar excepción.
"""

import uuid
import pytest
from unittest.mock import AsyncMock

from application.use_cases.organization_use_cases import (
    CreateOrganizationUseCase,
    CreateOrganizationCommand,
    ListOrganizationsUseCase,
)
from domain.entities.organization import Organization


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_org(name: str = "Acme", slug: str = "acme") -> Organization:
    """Construye una ``Organization`` de prueba con ID aleatorio."""
    return Organization(id=uuid.uuid4(), name=name, slug=slug)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCreateOrganizationUseCase:
    """
    Pruebas unitarias para ``CreateOrganizationUseCase``.

    Verifica que el caso de uso construya correctamente la entidad ``Organization``
    a partir del comando recibido, delega la persistencia al repositorio y respeta
    los valores por defecto del dominio (plan «free»).
    """

    async def test_creates_and_returns_organization(self):
        """
        El caso de uso retorna la organización tal como la devuelve el repositorio.

        Given:  Un repositorio cuyo método ``create`` retorna una instancia de ``Organization``.
        When:   Se ejecuta ``CreateOrganizationUseCase`` con nombre y slug válidos.
        Then:   El resultado es la misma instancia devuelta por el repositorio y
                ``create`` se llama exactamente una vez.
        """
        org = _make_org()
        repo = AsyncMock()
        repo.create.return_value = org

        result = await CreateOrganizationUseCase(repo).execute(
            CreateOrganizationCommand(name="Acme", slug="acme")
        )

        assert result is org
        repo.create.assert_called_once()

    async def test_passes_correct_slug_to_repo(self):
        """
        El slug y el nombre del comando se transfieren fielmente a la entidad persistida.

        Given:  Un repositorio que retorna el argumento recibido sin modificarlo.
        When:   Se ejecuta el caso de uso con ``name="Beta Corp"`` y ``slug="beta-corp"``.
        Then:   La entidad resultante refleja exactamente los valores del comando,
                garantizando que el repositorio almacena el slug canónico esperado.
        """
        repo = AsyncMock()
        repo.create.side_effect = lambda o: o

        result = await CreateOrganizationUseCase(repo).execute(
            CreateOrganizationCommand(name="Beta Corp", slug="beta-corp")
        )

        assert result.slug == "beta-corp"
        assert result.name == "Beta Corp"

    def test_default_plan_is_free(self):
        """
        El plan por defecto de ``CreateOrganizationCommand`` es ``"free"``.

        Given:  Un comando creado sin especificar el campo ``plan``.
        When:   Se accede al atributo ``plan`` del comando.
        Then:   El valor es ``"free"``, conforme al modelo de negocio que asigna
                el nivel gratuito a toda organización recién creada.
        """
        cmd = CreateOrganizationCommand(name="X", slug="x")
        assert cmd.plan == "free"


class TestListOrganizationsUseCase:
    """
    Pruebas unitarias para ``ListOrganizationsUseCase``.

    Verifica que el listado siempre consulte únicamente organizaciones activas
    y que el caso de uso propague el resultado del repositorio sin transformaciones.
    """

    async def test_returns_active_organizations(self):
        """
        El caso de uso devuelve exactamente la lista que retorna el repositorio.

        Given:  Un repositorio que retorna dos organizaciones activas.
        When:   Se ejecuta ``ListOrganizationsUseCase``.
        Then:   La lista resultante coincide con la del repositorio y el método
                ``list_all`` se invoca con ``active_only=True``, garantizando que
                los tenants desactivados no se exponen a los consumidores de la API.
        """
        orgs = [_make_org("A", "a"), _make_org("B", "b")]
        repo = AsyncMock()
        repo.list_all.return_value = orgs

        result = await ListOrganizationsUseCase(repo).execute()

        assert result == orgs
        repo.list_all.assert_called_once_with(active_only=True)

    async def test_returns_empty_list_when_no_orgs(self):
        """
        Cuando no hay organizaciones activas, el caso de uso retorna lista vacía sin error.

        Given:  Un repositorio que devuelve una lista vacía.
        When:   Se ejecuta ``ListOrganizationsUseCase``.
        Then:   El resultado es una lista vacía (``[]``), evitando que la ausencia
                de datos se trate como condición de error en la capa de aplicación.
        """
        repo = AsyncMock()
        repo.list_all.return_value = []

        result = await ListOrganizationsUseCase(repo).execute()

        assert result == []
