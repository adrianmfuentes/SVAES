"""
Test suite para ``CreateProjectUseCase``.

Los proyectos son el segundo nivel de la jerarquía de SVAES: agrupan releases
bajo una organización y definen el contexto lógico de cada ciclo de verificación.
``CreateProjectUseCase`` encapsula la lógica de construcción y persistencia de
nuevos proyectos.

Estrategia de prueba:
    Pruebas unitarias. El repositorio ``IProjectRepository`` se sustituye por
    un ``AsyncMock`` para verificar la composición de la entidad y el contrato
    de persistencia de forma aislada.

Invariantes clave verificadas:
    - La entidad ``Project`` resultante refleja exactamente los campos del comando
      (``organization_id``, ``name``, ``description``).
    - La persistencia se delega al repositorio y el resultado final es el objeto
      devuelto por ``repo.create``.
    - El campo ``description`` tiene valor vacío por defecto, permitiendo crear
      proyectos mínimos sin campos opcionales.
"""

import uuid
import pytest
from unittest.mock import AsyncMock

from application.use_cases.project_use_cases import CreateProjectUseCase, CreateProjectCommand
from domain.entities.project import Project


class TestCreateProjectUseCase:
    """
    Pruebas unitarias para ``CreateProjectUseCase``.

    Valida la construcción correcta de la entidad ``Project`` y la delegación
    de la persistencia al repositorio, incluyendo el comportamiento de valores
    por defecto del comando.
    """

    async def test_creates_project_with_correct_fields(self):
        """
        Los campos del comando se transfieren fielmente a la entidad ``Project`` creada.

        Given:  Un repositorio que retorna el objeto recibido sin modificación y
                un comando con ``organization_id``, ``name`` y ``description`` explícitos.
        When:   Se ejecuta ``CreateProjectUseCase`` con dicho comando.
        Then:   La entidad resultante tiene exactamente los valores provistos en el
                comando, confirmando que el caso de uso no altera los datos de entrada.
        """
        org_id = uuid.uuid4()
        repo = AsyncMock()
        repo.create.side_effect = lambda p: p

        cmd = CreateProjectCommand(organization_id=org_id, name="Backend", description="Core API")
        result = await CreateProjectUseCase(repo).execute(cmd)

        assert result.organization_id == org_id
        assert result.name == "Backend"
        assert result.description == "Core API"

    async def test_delegates_persistence_to_repo(self):
        """
        El caso de uso persiste la entidad a través del repositorio y retorna su resultado.

        Given:  Un repositorio que devuelve una instancia de ``Project`` predefinida.
        When:   Se ejecuta el caso de uso con un comando coherente con dicha instancia.
        Then:   El objeto retornado es exactamente la instancia del repositorio
                y ``repo.create`` se llama exactamente una vez, asegurando que no
                existe lógica de reintento ni creación duplicada.
        """
        repo = AsyncMock()
        saved = Project(organization_id=uuid.uuid4(), name="X", description="")
        repo.create.return_value = saved

        result = await CreateProjectUseCase(repo).execute(
            CreateProjectCommand(organization_id=saved.organization_id, name="X")
        )

        assert result is saved
        repo.create.assert_called_once()

    def test_default_description_is_empty(self):
        """
        Omitir ``description`` en el comando produce una descripción vacía, no un error.

        Given:  Un ``CreateProjectCommand`` construido sin el campo ``description``.
        When:   Se accede al atributo ``description`` del comando.
        Then:   El valor es la cadena vacía ``""``, permitiendo registrar proyectos
                con información mínima sin violar ninguna restricción del dominio.
        """
        cmd = CreateProjectCommand(organization_id=uuid.uuid4(), name="Minimal")
        assert cmd.description == ""
