"""Extrae eventos de creación de tag/release de los payloads de webhook de
cada proveedor REPO_CODIGO soportado (GitHub, GitLab, Gitea, Bitbucket).

Solo se procesan eventos que representan una etiqueta/versión nueva - pushes
a ramas normales, comentarios, PRs, etc. se ignoran devolviendo `None`, para
que el llamador pueda responder 200 sin crear ninguna release (evita que el
proveedor reintente indefinidamente un evento que deliberadamente no nos
interesa).
"""
from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class TagPushEvent:
    tag_name: str
    # Referencia externa a pasar al conector para resolver el artefacto
    # (hoy coincide con el nombre del tag, pero se mantiene separado por si
    # algún proveedor necesita un formato de referencia distinto).
    external_ref: str


def parse_github_event(event_header: Optional[str], payload: dict) -> Optional[TagPushEvent]:
    if event_header == "create" and payload.get("ref_type") == "tag":
        tag = payload.get("ref")
        if tag:
            return TagPushEvent(tag_name=tag, external_ref=tag)
    if event_header == "release" and payload.get("action") == "published":
        tag = (payload.get("release") or {}).get("tag_name")
        if tag:
            return TagPushEvent(tag_name=tag, external_ref=tag)
    return None


def parse_gitlab_event(event_header: Optional[str], payload: dict) -> Optional[TagPushEvent]:
    if event_header == "Tag Push Hook":
        ref = payload.get("ref") or ""
        # checkout_sha es None cuando el evento es un borrado de tag.
        if ref.startswith("refs/tags/") and payload.get("checkout_sha"):
            tag = ref[len("refs/tags/"):]
            if tag:
                return TagPushEvent(tag_name=tag, external_ref=tag)
    return None


def parse_gitea_event(event_header: Optional[str], payload: dict) -> Optional[TagPushEvent]:
    if event_header == "create" and payload.get("ref_type") == "tag":
        tag = payload.get("ref")
        if tag:
            return TagPushEvent(tag_name=tag, external_ref=tag)
    return None


def parse_bitbucket_event(event_header: Optional[str], payload: dict) -> Optional[TagPushEvent]:
    if event_header == "repo:push":
        for change in (payload.get("push") or {}).get("changes", []):
            new_ref = change.get("new") or {}
            if new_ref.get("type") == "tag":
                tag = new_ref.get("name")
                if tag:
                    return TagPushEvent(tag_name=tag, external_ref=tag)
    return None


_EVENT_HEADER_NAMES: dict[str, str] = {
    "GITHUB": "X-GitHub-Event",
    "GITLAB": "X-Gitlab-Event",
    "GITEA": "X-Gitea-Event",
    "BITBUCKET": "X-Event-Key",
}

_PARSERS: dict[str, Callable[[Optional[str], dict], Optional[TagPushEvent]]] = {
    "GITHUB": parse_github_event,
    "GITLAB": parse_gitlab_event,
    "GITEA": parse_gitea_event,
    "BITBUCKET": parse_bitbucket_event,
}


def event_header_name(connector_implementation: str) -> Optional[str]:
    return _EVENT_HEADER_NAMES.get(connector_implementation.upper())


def parse_tag_push_event(
    connector_implementation: str, event_header: Optional[str], payload: dict
) -> Optional[TagPushEvent]:
    parser = _PARSERS.get(connector_implementation.upper())
    if not parser:
        return None
    return parser(event_header, payload)


def version_from_tag_name(tag_name: str) -> str:
    """Normaliza un nombre de tag tipo git ('v1.2.3') a una versión SemVer
    ('1.2.3'). Los tags que no siguen ninguna de las dos convenciones se
    devuelven sin modificar y fallarán la validación SemVer de la release
    más adelante, con un mensaje de error claro para el usuario."""
    if tag_name[:1] in ("v", "V") and tag_name[1:2].isdigit():
        return tag_name[1:]
    return tag_name
