"""
Test suite para ``GetVerificationHistoryUseCase``.

Este caso de uso proporciona el historial de verificación de una release: dado
un identificador de release, devuelve un resumen estructurado con el veredicto
final, la duración de la verificación y las reglas evaluadas.

Es un caso de uso de consulta (query) dentro del patrón CQRS implícito de la
capa de aplicación: no modifica estado, sólo agrega y proyecta datos asociados
a una release ya completada.

Estrategia de prueba:
    Pruebas unitarias. El repositorio de releases se reemplaza por un ``AsyncMock``
    que permite controlar el estado de la entidad devuelta en cada escenario.

Invariantes clave verificadas:
    - Consultar el historial de una release inexistente lanza ``EntityNotFoundError``.
    - El resultado es un diccionario que incluye el ID de la release como cadena.
    - El diccionario contiene las claves ``verdict``, ``duration_ms`` y
      ``rules_evaluated``, definiendo el contrato de respuesta de la API.
"""

import uuid
import pytest
from unittest.mock import AsyncMock

from application.use_cases.get_verification_history import GetVerificationHistoryUseCase
from domain.entities.release import Release
from domain.entities.enums import ReleaseStatus
from domain.exceptions import EntityNotFoundError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_release() -> Release:
    """Construye una ``Release`` de prueba en estado ``COMPLETADA``."""
    return Release(
        project_id=uuid.uuid4(),
        profile_id=uuid.uuid4(),
        version="1.0.0",
        created_by=uuid.uuid4(),
        status=ReleaseStatus.COMPLETADA,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestGetVerificationHistoryUseCase:
    """
    Pruebas unitarias para ``GetVerificationHistoryUseCase``.

    Verifica el comportamiento ante releases inexistentes y la estructura del
    diccionario de respuesta para releases encontradas.
    """

    async def test_release_not_found_raises_entity_not_found(self):
        """
        Consultar el historial de una release inexistente lanza ``EntityNotFoundError``.

        Given:  Un repositorio que devuelve ``None`` para cualquier ID de release.
        When:   Se ejecuta ``GetVerificationHistoryUseCase`` con un UUID aleatorio.
        Then:   Se lanza ``EntityNotFoundError``, informando al llamante de forma
                explícita que el recurso solicitado no existe, en lugar de devolver
                un resultado vacío que podría interpretarse ambiguamente.
        """
        repo = AsyncMock()
        repo.get_by_id.return_value = None

        with pytest.raises(EntityNotFoundError):
            await GetVerificationHistoryUseCase(repo).execute(uuid.uuid4())

    async def test_returns_dict_with_release_id(self):
        """
        El historial incluye el ID de la release serializado como cadena de texto.

        Given:  Un repositorio que devuelve una release en estado ``COMPLETADA``.
        When:   Se ejecuta el caso de uso con el ID de dicha release.
        Then:   El diccionario resultante contiene la clave ``"release_id"`` con
                el valor ``str(release.id)``, proporcionando la referencia cruzada
                necesaria para que los consumidores de la API identifiquen el recurso.
        """
        release = _make_release()
        repo = AsyncMock()
        repo.get_by_id.return_value = release

        result = await GetVerificationHistoryUseCase(repo).execute(release.id)

        assert result["release_id"] == str(release.id)

    async def test_result_contains_expected_keys(self):
        """
        El historial expone las claves de contrato definidas por el dominio.

        Given:  Un repositorio que devuelve una release válida.
        When:   Se ejecuta el caso de uso.
        Then:   El diccionario resultante contiene las claves ``"verdict"``,
                ``"duration_ms"`` y ``"rules_evaluated"``, que forman el contrato
                mínimo de respuesta consumido por los routers de la API y los
                clientes externos.
        """
        release = _make_release()
        repo = AsyncMock()
        repo.get_by_id.return_value = release

        result = await GetVerificationHistoryUseCase(repo).execute(release.id)

        assert "verdict" in result
        assert "duration_ms" in result
        assert "rules_evaluated" in result
