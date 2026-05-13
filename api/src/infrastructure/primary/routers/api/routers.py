"""
Este archivo define los routers para la API. 
Aquí se importan los routers de las diferentes versiones de la API y se exportan para su uso en la aplicación principal.
"""
from infrastructure.primary.routers.api.v1.releases import router as releases_router

__all__ = [
    "releases_router"
]