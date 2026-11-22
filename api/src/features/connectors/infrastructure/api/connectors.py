from fastapi import APIRouter

from .connector_catalog import router as connector_catalog_router
from .connector_management import router as connector_management_router


router = APIRouter()
router.include_router(connector_catalog_router)
router.include_router(connector_management_router)
