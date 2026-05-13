from typing import List
from uuid import UUID
from application.ports.output.i_verification_result_repository import IVerificationResultRepository
from domain.entities.verification_result import VerificationResult
from domain.exceptions import ValidationError

"""
Este módulo define el caso de uso para obtener el historial de verificaciones de una release. Incluye la lógica de negocio para validar la entrada y
obtener los resultados de verificación asociados a una release específica. El historial de verificaciones es una lista de resultados que muestran el 
estado de cada regla de verificación ejecutada durante el proceso de verificación de una release, incluyendo información sobre si cada regla pasó o falló, 
la severidad de cada regla, y cualquier mensaje o dato adicional relevante para entender el resultado de la verificación.
"""
class GetVerificationHistoryUseCase:
    def __init__(
        self,
        verification_result_repository: IVerificationResultRepository,
    ) -> None:
        self._verification_repo = verification_result_repository


    async def execute(self, release_id: UUID) -> List[VerificationResult]:
        if not release_id:
            raise ValidationError("release_id es requerido")
        return await self._verification_repo.find_by_release(release_id)