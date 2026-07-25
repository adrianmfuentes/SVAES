"""Notificaciones salientes a webhooks de terceros (Slack, MS Teams, genérico).

Reutiliza el mismo patrón que `GenericHttpConnector` (JSON declarativo en
`config_data`, sin código nuevo por proveedor) pero en dirección saliente: en
vez de recuperar artefactos, empuja un mensaje formateado cuando cambia el
veredicto de una release. La firma HMAC del canal `GENERIC` replica
`core/webhook_signature.py` (mismo esquema `sha256=<hex>` que ya usan los
webhooks entrantes de GitHub/Bitbucket) para que el receptor pueda verificar
la autenticidad del payload.
"""
import hashlib
import hmac
import json
import logging
from typing import Any, Dict

import httpx

from infrastructure.secondary.connectors.base_http_connector import assert_safe_outbound_url

TIMEOUT = 15.0

_log = logging.getLogger(__name__)

OUTBOUND_CHANNEL_TYPES = {"SLACK", "MS_TEAMS", "GENERIC"}

_EVENT_LABELS: Dict[str, str] = {
    "RELEASE_VALIDATED": "Release validada",
    "RELEASE_INVALIDATED": "Release no válida",
    "DRIFT_DETECTED": "Drift detectado en verificación programada",
}

_EVENT_EMOJI: Dict[str, str] = {
    "RELEASE_VALIDATED": "✅",
    "RELEASE_INVALIDATED": "❌",
    "DRIFT_DETECTED": "⚠️",
}

_TEAMS_THEME_COLORS: Dict[str, str] = {
    "RELEASE_VALIDATED": "22c55e",
    "RELEASE_INVALIDATED": "ef4444",
    "DRIFT_DETECTED": "f59e0b",
}


def _slack_payload(event_type: str, ctx: Dict[str, Any]) -> Dict[str, Any]:
    label = _EVENT_LABELS.get(event_type, event_type)
    emoji = _EVENT_EMOJI.get(event_type, "")
    lines = [f"{emoji} *{label}*: {ctx.get('release_name')} v{ctx.get('version')}".strip()]
    if ctx.get("project_name"):
        lines.append(f"Proyecto: {ctx['project_name']}")
    lines.append(f"Veredicto: {ctx.get('verdict')}")
    if ctx.get("release_url"):
        lines.append(f"<{ctx['release_url']}|Ver detalle>")
    return {"text": "\n".join(lines)}


def _teams_payload(event_type: str, ctx: Dict[str, Any]) -> Dict[str, Any]:
    label = _EVENT_LABELS.get(event_type, event_type)
    facts = [{"name": "Veredicto", "value": str(ctx.get("verdict"))}]
    if ctx.get("project_name"):
        facts.append({"name": "Proyecto", "value": ctx["project_name"]})
    card: Dict[str, Any] = {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "summary": label,
        "themeColor": _TEAMS_THEME_COLORS.get(event_type, "6b7280"),
        "title": f"{_EVENT_EMOJI.get(event_type, '')} {label}".strip(),
        "text": f"{ctx.get('release_name')} v{ctx.get('version')}",
        "sections": [{"facts": facts}],
    }
    if ctx.get("release_url"):
        card["potentialAction"] = [{
            "@type": "OpenUri",
            "name": "Ver detalle",
            "targets": [{"os": "default", "uri": ctx["release_url"]}],
        }]
    return card


def _generic_payload(event_type: str, ctx: Dict[str, Any]) -> Dict[str, Any]:
    return {"event": event_type, **ctx}


def _sign(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _build_payload(channel_type: str, event_type: str, ctx: Dict[str, Any]) -> Dict[str, Any]:
    if channel_type == "SLACK":
        return _slack_payload(event_type, ctx)
    if channel_type == "MS_TEAMS":
        return _teams_payload(event_type, ctx)
    return _generic_payload(event_type, ctx)


async def send_outbound_notification(channel: Any, event_type: str, ctx: Dict[str, Any]) -> bool:
    """Envía `event_type` (RELEASE_VALIDATED|RELEASE_INVALIDATED|DRIFT_DETECTED) al `channel`.

    Nunca lanza: un webhook de terceros caído no debe interrumpir el resto de las
    notificaciones (email, otros canales). Devuelve True/False para que el
    llamador pueda registrar métricas si lo necesita.
    """
    config = channel.config_data or {}
    url = config.get("webhook_url") or config.get("url")
    if not url:
        _log.warning("Outbound notification skipped: channel %s has no webhook_url", getattr(channel, "id", "?"))
        return False

    try:
        assert_safe_outbound_url(url)
    except Exception:
        _log.warning("Outbound webhook blocked (unsafe URL) for channel %s", getattr(channel, "id", "?"))
        return False

    channel_type = (channel.channel_type or "").upper()
    body = _build_payload(channel_type, event_type, ctx)
    raw = json.dumps(body).encode()

    headers = {"Content-Type": "application/json"}
    secret = config.get("signing_secret")
    if channel_type == "GENERIC" and secret:
        headers["X-SVAES-Signature"] = _sign(secret, raw)

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(url, content=raw, headers=headers)
            response.raise_for_status()
        return True
    except Exception:
        _log.exception(
            "Failed to deliver outbound notification: channel=%s type=%s event=%s",
            getattr(channel, "id", "?"), channel_type, event_type,
        )
        return False
