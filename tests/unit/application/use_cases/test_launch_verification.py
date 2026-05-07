"""
Test suite para ``LaunchVerificationUseCase``.

``LaunchVerificationUseCase`` es la transición crítica de la máquina de estados
de una release: lleva una release de ``PENDIENTE`` a ``EN_VERIFICACION`` y encola
la tarea de verificación asíncrona en la cola de trabajos.

Diagrama de estados relevante:
    BORRADOR → PENDIENTE → **EN_VERIFICACION** → COMPLETADA
                                ↑
                         (este caso de uso)

Este caso de uso impone dos precondiciones de dominio:
    1. La release debe existir.
    2. La release debe estar en estado ``PENDIENTE`` (no en cualquier otro estado).

El orden de operaciones también es una invariante del dominio: el estado se
persiste **antes** de encolar la tarea, evitando condiciones de carrera en las
que un worker procese una release que aún figura como ``PENDIENTE`` en la base
de datos.

Estrategia de prueba:
    Pruebas unitarias. El repositorio (``IReleaseRepository``) y la cola de tareas
    (``ITaskQueue``) se sustituyen por ``AsyncMock``. El test de orden de llamadas
    utiliza efectos secundarios instrumentados para registrar la secuencia real
    de ejecución.

Invariantes clave verificadas:
    - Lanzar verificación sobre una release inexistente lanza ``EntityNotFoundError``.
    - Cualquier estado distinto de ``PENDIENTE`` lanza ``ReleaseInvalidStateError``.
    - La release se actualiza a ``EN_VERIFICACION`` antes de devolver control.
    - El ID de tarea devuelto por la cola se propaga al llamante.
    - ``repo.update`` se ejecuta antes que ``task_queue.enqueue_verification_task``.
"""

import uuid
import pytest
from unittest.mock import AsyncMock

from application.use_cases.launch_verification import LaunchVerificationUseCase, LaunchVerificationCommand
from domain.entities.release import Release
from domain.entities.enums import ReleaseStatus
from domain.exceptions import EntityNotFoundError, ReleaseInvalidStateError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_release(status: ReleaseStatus = ReleaseStatus.PENDIENTE) -> Release:
    """Construye una ``Release`` de prueba con el estado especificado."""
    return Release(
        project_id=uuid.uuid4(),
        profile_id=uuid.uuid4(),
        version="1.0.0",
        created_by=uuid.uuid4(),
        status=status,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def task_queue():
    """Cola de tareas stub que retorna un ID de tarea predecible."""
    queue = AsyncMock()
    queue.enqueue_verification_task.return_value = "task-abc-123"
    return queue


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestLaunchVerificationUseCase:
    """
    Pruebas unitarias para ``LaunchVerificationUseCase``.

    Cubre las condiciones de error de dominio, el camino feliz completo y la
    garantía de orden de operaciones (persistencia antes de encolar).
    """

    async def test_release_not_found_raises_entity_not_found(self, task_queue):
        """
        Una release inexistente lanza ``EntityNotFoundError`` antes de cualquier operación.

        Given:  Un repositorio que devuelve ``None`` para cualquier ID de release.
        When:   Se ejecuta ``LaunchVerificationUseCase`` con un ID aleatorio.
        Then:   Se lanza ``EntityNotFoundError``, impidiendo que se intente cambiar
                el estado o encolar una tarea para una entidad que no existe.
        """
        repo = AsyncMock()
        repo.get_by_id.return_value = None

        with pytest.raises(EntityNotFoundError):
            await LaunchVerificationUseCase(repo, task_queue).execute(
                LaunchVerificationCommand(release_id=uuid.uuid4(), user_id=uuid.uuid4())
            )

    async def test_release_not_pendiente_raises_invalid_state(self, task_queue):
        """
        Todos los estados distintos de ``PENDIENTE`` producen ``ReleaseInvalidStateError``.

        Given:  Releases en estados ``BORRADOR``, ``EN_VERIFICACION`` y ``COMPLETADA``.
        When:   Se intenta lanzar la verificación para cada una de ellas.
        Then:   Cada intento lanza ``ReleaseInvalidStateError``, aplicando la máquina
                de estados del dominio y previniendo verificaciones duplicadas o
                fuera de orden que podrían corromper el historial de auditoría.
        """
        for bad_status in (
            ReleaseStatus.BORRADOR,
            ReleaseStatus.EN_VERIFICACION,
            ReleaseStatus.COMPLETADA,
        ):
            repo = AsyncMock()
            repo.get_by_id.return_value = _make_release(status=bad_status)

            with pytest.raises(ReleaseInvalidStateError):
                await LaunchVerificationUseCase(repo, task_queue).execute(
                    LaunchVerificationCommand(release_id=uuid.uuid4(), user_id=uuid.uuid4())
                )

    async def test_happy_path_updates_status_to_en_verificacion(self, task_queue):
        """
        Una release en ``PENDIENTE`` transiciona a ``EN_VERIFICACION`` tras la ejecución.

        Given:  Una release con estado ``PENDIENTE`` y un repositorio que persiste el cambio.
        When:   Se ejecuta el caso de uso con éxito.
        Then:   El objeto release devuelto tiene el estado ``EN_VERIFICACION``,
                reflejando la transición de estado perseguida por este caso de uso.
        """
        release = _make_release(ReleaseStatus.PENDIENTE)
        repo = AsyncMock()
        repo.get_by_id.return_value = release
        repo.update.side_effect = lambda r: r

        updated, _ = await LaunchVerificationUseCase(repo, task_queue).execute(
            LaunchVerificationCommand(release_id=release.id, user_id=uuid.uuid4())
        )

        assert updated.status == ReleaseStatus.EN_VERIFICACION

    async def test_happy_path_enqueues_task_and_returns_task_id(self, task_queue):
        """
        El ID de tarea devuelto por la cola se propaga como segundo elemento de la tupla.

        Given:  Una release en estado ``PENDIENTE`` y una cola que retorna ``"task-abc-123"``.
        When:   Se ejecuta el caso de uso correctamente.
        Then:   El segundo elemento de la tupla resultante es ``"task-abc-123"`` y
                ``enqueue_verification_task`` se llama exactamente una vez con el ID
                de la release, garantizando que cada lanzamiento genera una sola tarea.
        """
        release = _make_release(ReleaseStatus.PENDIENTE)
        repo = AsyncMock()
        repo.get_by_id.return_value = release
        repo.update.side_effect = lambda r: r

        _, task_id = await LaunchVerificationUseCase(repo, task_queue).execute(
            LaunchVerificationCommand(release_id=release.id, user_id=uuid.uuid4())
        )

        assert task_id == "task-abc-123"
        task_queue.enqueue_verification_task.assert_called_once_with(release.id)

    async def test_repo_update_called_before_enqueue(self, task_queue):
        """
        La persistencia del cambio de estado ocurre antes del encolado de la tarea.

        Given:  Efectos secundarios instrumentados en ``repo.update`` y
                ``task_queue.enqueue_verification_task`` que registran el orden de llamada.
        When:   Se ejecuta el caso de uso sobre una release en estado ``PENDIENTE``.
        Then:   El orden registrado es ``["update", "enqueue"]``, garantizando que
                ningún worker pueda procesar la tarea antes de que el cambio de estado
                esté confirmado en la base de datos.

        Nota:
            Esta invariante de ordenamiento es crítica para la consistencia: si la
            tarea se encolara primero, un worker podría encontrar la release aún
            en ``PENDIENTE`` y rechazarla o procesarla en estado incorrecto.
        """
        call_order = []
        release = _make_release(ReleaseStatus.PENDIENTE)

        repo = AsyncMock()
        repo.get_by_id.return_value = release

        def mock_update(r):
            call_order.append("update")
            return r

        def mock_enqueue(rid):
            call_order.append("enqueue")
            return "task-id"

        repo.update.side_effect = mock_update
        task_queue.enqueue_verification_task.side_effect = mock_enqueue

        await LaunchVerificationUseCase(repo, task_queue).execute(
            LaunchVerificationCommand(release_id=release.id, user_id=uuid.uuid4())
        )

        assert call_order == ["update", "enqueue"]
