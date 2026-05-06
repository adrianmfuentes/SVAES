from fastapi import FastAPI
from api.routers import auth, organizations, projects, profiles, releases, connectors

API_V1_PREFIX = "/api/v1"

app = FastAPI(
    title="SVAES API",
    description="Sistema de Verificación Automática de Entregas de Software",
    version="1.0.0",
)

app.include_router(auth.router, prefix=API_V1_PREFIX)
app.include_router(organizations.router, prefix=API_V1_PREFIX)
app.include_router(projects.router, prefix=API_V1_PREFIX)
app.include_router(profiles.router, prefix=API_V1_PREFIX)
app.include_router(releases.router, prefix=API_V1_PREFIX)
app.include_router(connectors.router, prefix=API_V1_PREFIX)

@app.get("/health", tags=["System"])
def health():
    return {"status": "ok", "message": "El backend está funcionando correctamente"}