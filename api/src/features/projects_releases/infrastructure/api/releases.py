from fastapi import APIRouter

from .release_crud import router as release_crud_router
from .release_artifacts import router as release_artifacts_router
from .release_verification import router as release_verification_router


router = APIRouter()
router.include_router(release_crud_router)
router.include_router(release_artifacts_router)
router.include_router(release_verification_router)
