from fastapi import APIRouter

from .user_profile import router as user_profile_router
from .user_management import router as user_management_router


router = APIRouter()
router.include_router(user_profile_router)
router.include_router(user_management_router)
