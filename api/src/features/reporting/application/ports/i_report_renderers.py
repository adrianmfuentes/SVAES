from typing import Protocol

from features.projects_releases.domain.release import Release
from features.verification.domain.verification_result import VerificationResult


class IPdfRenderer(Protocol):
    async def render(
        self, path: str, result: VerificationResult, release: Release | None, lang: str,
    ) -> None: ...


class ICsvExporter(Protocol):
    async def export(self, path: str, rows: list[dict[str, str]]) -> None: ...
