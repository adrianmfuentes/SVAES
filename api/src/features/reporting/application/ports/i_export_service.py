from abc import ABC, abstractmethod
from uuid import UUID

class IExportService(ABC):

    @abstractmethod
    async def export_verification_to_pdf(self, release_id: UUID, result_id: UUID, lang: str = "es") -> str:
        pass

    @abstractmethod
    async def export_project_results_to_csv(self, project_id: UUID) -> str:
        pass