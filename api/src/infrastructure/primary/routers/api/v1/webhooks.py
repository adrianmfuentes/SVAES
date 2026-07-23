from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request, status
from application.use_cases.main.handle_incoming_webhook import HandleIncomingWebhookUseCase
from core.dependencies import get_webhook_use_case
from core.rate_limit import rate_limit_auth
from domain.exceptions import EntityNotFoundError, InvalidWebhookSignatureError, ValidationError
from . import ERROR_INTERNO

router = APIRouter(tags=["Webhooks"])


@router.post("/api/v1/webhooks/source-control/{project_id}/{connector_id}", status_code=status.HTTP_202_ACCEPTED)
@rate_limit_auth()
async def receive_source_control_webhook(
    request: Request,
    project_id: UUID,
    connector_id: UUID,
    use_case: Annotated[HandleIncomingWebhookUseCase, Depends(get_webhook_use_case)],
):
    """Endpoint público (sin JWT) que recibe webhooks entrantes de un
    conector REPO_CODIGO (GitHub, GitLab, Gitea o Bitbucket) y, si el evento
    representa la creación de un tag/release, crea automáticamente la
    release en SVAES y lanza su verificación.

    La autenticidad de la petición se verifica mediante la firma HMAC (o
    token, según el proveedor) configurada al habilitar el webhook del
    conector - no mediante un JWT, ya que el emisor es el proveedor externo,
    no un usuario de SVAES.

    Atributos:
        - project_id: UUID del proyecto SVAES al que pertenecerá la release creada.
        - connector_id: UUID del conector REPO_CODIGO configurado con este webhook.

    Retorna:
        - 202 Accepted con el ID de la release creada, o `release_id: null` si
          el evento fue aceptado pero no representaba un tag/release nuevo
          (no es un error - por ejemplo, un push a una rama normal).
        - 401 si la firma/token del webhook no es válida.
        - 404 si el conector o el proyecto no existen, o no pertenecen a la misma organización.
        - 422 si el webhook no está habilitado para este conector, o el conector no es REPO_CODIGO.
        - 500 para cualquier otro error inesperado.
    """
    raw_body = await request.body()
    try:
        release_id = await use_case.handle_source_control_event(
            project_id=project_id,
            connector_id=connector_id,
            raw_body=raw_body,
            headers=request.headers,
        )
        return {"release_id": str(release_id) if release_id else None}
    except InvalidWebhookSignatureError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e))
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_INTERNO)
