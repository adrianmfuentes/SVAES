from fastapi import APIRouter

from .organization_crud import router as organization_crud_router
from .organization_projects import router as organization_projects_router
from .organization_administration import router as organization_administration_router


router = APIRouter()
router.include_router(organization_crud_router)
router.include_router(organization_projects_router)
router.include_router(organization_administration_router)
