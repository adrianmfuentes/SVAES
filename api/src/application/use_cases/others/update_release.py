import re
from uuid import UUID
from application.ports.output.i_release_repository import IReleaseRepository
from domain.entities.release import Release
from domain.exceptions import ValidationError

"""
Este módulo define el caso de uso para actualizar una release, que es responsable de validar los datos de entrada y actualizar la información de una 
release existente en el sistema.
"""
class UpdateReleaseUseCase:
    def __init__(self, release_repository: IReleaseRepository) -> None:
        self._release_repo = release_repository

    async def execute(
        self,
        release_id: UUID,
        name: str,
        version: str,
        description: str = "",
    ) -> Release:
        if not self._is_valid_semver(version):
            raise ValidationError("La versión debe cumplir SemVer 2.0.0")

        release = await self._release_repo.get_by_id(release_id)
        if not release:
            raise ValidationError("No se encontró el release para actualizar.")

        release.name = name
        release.version = version
        release.description = description
        return await self._release_repo.update(release)

    def _is_valid_semver(self, version: str) -> bool:
        parts = version.split("-", 1)
        core = parts[0]
        pre = parts[1] if len(parts) > 1 else ""
        if "+" in pre and "-" not in pre.split("+", 1)[0]:
            pre, build = pre.split("+", 1)
        elif "+" in core:
            core, build = core.split("+", 1)
            pre = ""
        else:
            build = ""

        if not re.match(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$", core):
            return False

        ident = r"[0-9A-Za-z-]+"
        if pre and not re.match(rf"^{ident}(\.{ident})*$", pre):
            return False
        if build and not re.match(rf"^{ident}(\.{ident})*$", build):
            return False
        return True