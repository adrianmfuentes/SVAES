import asyncio
import json
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from api.rate_limit import limiter
from domain.entities.user import User
from api.src.domain.enums import ReleaseStatus, UserRole
from domain.exceptions import EntityNotFoundError, ReleaseInvalidStateError
from api.schemas.release import ReleaseCreate, ReleaseUpdate, ReleaseResponse, VerificationTaskResponse
from api.schemas.connector import VerificationResultResponse
from api.src.application.use_cases.main.launch_verification import LaunchVerificationUseCase, LaunchVerificationCommand
from api.src.application.use_cases.main.create_release import (
    CreateReleaseUseCase,
    CreateReleaseCommand,
    GetReleaseUseCase,
    ListReleasesUseCase,
    UpdateReleaseUseCase,
    UpdateReleaseCommand,
    DeleteReleaseUseCase,
)
from api.src.application.use_cases.main.get_verification_history import GetVerificationHistoryUseCase
from api.dependencies import (
    get_launch_verification_use_case,
    get_create_release_use_case,
    get_get_release_use_case,
    get_list_releases_use_case,
    get_update_release_use_case,
    get_delete_release_use_case,
    get_verification_history_use_case,
    get_current_user,
    require_min_role,
    get_task_queue,
)

router = APIRouter(prefix="/releases", tags=["Releases"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ReleaseResponse)
async def create_release(
    request: ReleaseCreate,
    use_case: Annotated[CreateReleaseUseCase, Depends(get_create_release_use_case)],
    current_user: Annotated[User, Depends(require_min_role(UserRole.OPERATOR))],
):
    command = CreateReleaseCommand(
        project_id=request.project_id,
        profile_id=request.profile_id,
        version=request.version,
        description=request.description,
        created_by=current_user.id,
    )
    return await use_case.execute(command)


@router.get("", response_model=list[ReleaseResponse])
async def list_releases(
    use_case: Annotated[ListReleasesUseCase, Depends(get_list_releases_use_case)],
    _current_user: Annotated[User, Depends(get_current_user)],
    project_id: Annotated[uuid.UUID, Query()],
    skip: Annotated[int, Query(default=0, ge=0)],
    limit: Annotated[int, Query(default=50, ge=1, le=200)],
):
    return await use_case.execute(project_id, skip=skip, limit=limit)


@router.get("/{release_id}", response_model=ReleaseResponse)
async def get_release(
    release_id: uuid.UUID,
    use_case: Annotated[GetReleaseUseCase, Depends(get_get_release_use_case)],
    _current_user: Annotated[User, Depends(get_current_user)],
):
    try:
        return await use_case.execute(release_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch("/{release_id}", response_model=ReleaseResponse)
async def update_release(
    release_id: uuid.UUID,
    request: ReleaseUpdate,
    use_case: Annotated[UpdateReleaseUseCase, Depends(get_update_release_use_case)],
    _current_user: Annotated[User, Depends(require_min_role(UserRole.OPERATOR))],
):
    try:
        command = UpdateReleaseCommand(release_id=release_id, description=request.description)
        return await use_case.execute(command)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ReleaseInvalidStateError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.delete("/{release_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_release(
    release_id: uuid.UUID,
    use_case: Annotated[DeleteReleaseUseCase, Depends(get_delete_release_use_case)],
    _current_user: Annotated[User, Depends(require_min_role(UserRole.MANAGER))],
):
    try:
        await use_case.execute(release_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ReleaseInvalidStateError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.get("/{release_id}/results", response_model=list[VerificationResultResponse])
async def get_results(
    release_id: uuid.UUID,
    use_case: Annotated[GetVerificationHistoryUseCase, Depends(get_verification_history_use_case)],
    _current_user: Annotated[User, Depends(require_min_role(UserRole.VIEWER))],
):
    try:
        results = await use_case.execute(release_id)
        return [
            VerificationResultResponse(
                id=r.id,
                release_id=r.release_id,
                verdict=r.verdict.value,
                rule_results=r.rule_results,
                profile_snapshot=r.profile_snapshot,
                executed_at=r.executed_at,
                duration_ms=r.duration_ms,
            )
            for r in results
        ]
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/{release_id}/verify",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=VerificationTaskResponse,
)
@limiter.limit("10/minute")
async def verify_release(
    request: Request,
    release_id: uuid.UUID,
    use_case: Annotated[LaunchVerificationUseCase, Depends(get_launch_verification_use_case)],
    current_user: Annotated[User, Depends(require_min_role(UserRole.OPERATOR))],
):
    command = LaunchVerificationCommand(release_id=release_id, user_id=current_user.id)

    try:
        _, task_id = await use_case.execute(command)
        return VerificationTaskResponse(
            message="Verification successfully queued",
            task_id=task_id,
        )
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ReleaseInvalidStateError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except (ValueError, RuntimeError) as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e


@router.get("/{release_id}/verify/stream")
async def stream_verification_results(
    release_id: uuid.UUID,
    use_case: Annotated[GetVerificationHistoryUseCase, Depends(get_verification_history_use_case)],
    _current_user: Annotated[User, Depends(require_min_role(UserRole.VIEWER))],
):
    """SSE stream — polls the verification results until a terminal verdict is available."""

    async def _event_generator():
        seen_ids: set[str] = set()
        for _ in range(60):  # max 5 min at 5s intervals
            try:
                results = await use_case.execute(release_id)
            except EntityNotFoundError:
                yield f"event: error\ndata: {json.dumps({'detail': 'Release not found'})}\n\n"
                return

            for r in results:
                rid = str(r.id)
                if rid not in seen_ids:
                    seen_ids.add(rid)
                    payload = {
                        "id": rid,
                        "verdict": r.verdict.value,
                        "executed_at": r.executed_at.isoformat(),
                        "duration_ms": r.duration_ms,
                    }
                    yield f"data: {json.dumps(payload)}\n\n"

            if results:
                yield "event: done\ndata: {}\n\n"
                return

            await asyncio.sleep(5)

        yield "event: timeout\ndata: {}\n\n"

    return StreamingResponse(_event_generator(), media_type="text/event-stream")


class CancelVerificationCommand(BaseModel):
    task_id: str


async def _handle_verification_result(websocket: WebSocket, result, seen_ids: set[str]) -> bool:
    """Process a single verification result. Returns True if should break."""
    rid = str(result.id)
    if rid in seen_ids:
        return False
    
    seen_ids.add(rid)
    await websocket.send_json({
        "type": "result",
        "id": rid,
        "verdict": result.verdict.value,
        "executed_at": result.executed_at.isoformat(),
        "duration_ms": result.duration_ms,
    })
    return True


async def _handle_cancel_message(websocket: WebSocket, msg: dict) -> None:
    """Handle cancel message from client."""
    task_id = msg.get("task_id")
    if not task_id:
        return
    queue = get_task_queue()
    await queue.cancel_task(task_id)
    await websocket.send_json({"type": "cancelled", "task_id": task_id})


async def _handle_ping_message(websocket: WebSocket) -> None:
    """Handle ping message from client."""
    await websocket.send_json({"type": "pong"})


async def _handle_websocket_message(websocket: WebSocket, msg: dict) -> None:
    """Route and handle incoming WebSocket message."""
    msg_type = msg.get("type")
    if msg_type == "cancel":
        await _handle_cancel_message(websocket, msg)
    elif msg_type == "ping":
        await _handle_ping_message(websocket)
    else:
        await websocket.send_json({"type": "error", "detail": "Unknown message type"})


@router.websocket("/{release_id}/ws")
async def websocket_verification(
    websocket: WebSocket,
    release_id: uuid.UUID,
    use_case: Annotated[GetVerificationHistoryUseCase, Depends(get_verification_history_use_case)],
    _current_user: Annotated[User, Depends(get_current_user)],
):
    """Bidirectional WebSocket channel for real-time verification events and cancellation commands.

    Client -> Server messages (JSON):
        - {"type": "cancel", "task_id": "<uuid>"}  — requests cancellation of a running task
        - {"type": "ping"}                          — keepalive / round-trip check

    Server -> Client messages (JSON):
        - {"type": "result", "id": "<uuid>", "verdict": "VALID", "executed_at": "...", "duration_ms": 1234}
        - {"type": "cancelled", "task_id": "<uuid>"}
        - {"type": "pong"}
        - {"type": "error", "detail": "..."}
    """
    await websocket.accept()

    async def _result_publisher():
        seen_ids: set[str] = set()
        async def _fetch_results():
            try:
                return await use_case.execute(release_id)
            except EntityNotFoundError:
                await websocket.send_json({"type": "error", "detail": "Release not found"})
                return None

        try:
            for _ in range(240):
                results = await _fetch_results()
                if results is None:
                    break

                for r in results:
                    await _handle_verification_result(websocket, r, seen_ids)

                if seen_ids:
                    break

                await asyncio.sleep(5)

            await websocket.send_json({"type": "done"})
        except WebSocketDisconnect:
            # client disconnected, just stop
            pass

    async def _message_reader():
        try:
            while True:
                msg = await websocket.receive_json()
                await _handle_websocket_message(websocket, msg)
        except WebSocketDisconnect:
            pass

    await asyncio.gather(_result_publisher(), _message_reader())
