def normalize_browse_items(items: list, implementation: str, config: dict) -> list:
    impl = implementation.upper()
    result = []
    for item in items:
        try:
            entry = _map_item(item, impl, config)
            if entry and entry.get("ref"):
                result.append(entry)
        except Exception:
            continue
    return result


_ITEM_MAPPERS = {
    "JIRA": lambda item, config: _map_jira_item(item),
    "JIRA_SM": lambda item, config: _map_jira_item(item),
    "GITHUB": lambda item, config: _map_github_gitea_item(item, config),
    "GITEA": lambda item, config: _map_github_gitea_item(item, config),
    "GITLAB": lambda item, config: _map_gitlab_item(item, config),
    "BITBUCKET": lambda item, config: _map_bitbucket_item(item, config),
    "CONFLUENCE": lambda item, config: {"ref": item.get("id", ""), "title": item.get("title", ""), "subtitle": item.get("type", "")},
    "LINEAR": lambda item, config: _map_linear_item(item),
    "ASANA": lambda item, config: {"ref": item.get("gid", ""), "title": item.get("name", ""), "subtitle": ""},
    "TRELLO": lambda item, config: {"ref": item.get("id", ""), "title": item.get("name", ""), "subtitle": ""},
    "CLICKUP": lambda item, config: _map_status_item(item),
    "PLANE": lambda item, config: _map_status_item(item),
    "TAIGA": lambda item, config: _map_status_item(item),
    "NOTION": lambda item, config: _map_notion_item(item),
    "WIKIJS": lambda item, config: {"ref": str(item.get("id", "")), "title": item.get("title", "") or item.get("name", ""), "subtitle": ""},
    "BOOKSTACK": lambda item, config: {"ref": str(item.get("id", "")), "title": item.get("title", "") or item.get("name", ""), "subtitle": ""},
    "GLPI": lambda item, config: _map_name_status_item(item),
    "ZAMMAD": lambda item, config: _map_name_status_item(item),
    "REDMINE": lambda item, config: _map_name_status_item(item),
}


def _map_jira_item(item: dict) -> dict:
    fields = item.get("fields", {})
    return {
        "ref": item.get("key", ""),
        "title": fields.get("summary", ""),
        "subtitle": (fields.get("status") or {}).get("name", ""),
    }


def _map_github_gitea_item(item: dict, config: dict) -> dict:
    owner = config.get("owner", "")
    repo = config.get("repo", "")
    number = item.get("number", "")
    return {
        "ref": f"{owner}/{repo}/{number}",
        "title": item.get("title", ""),
        "subtitle": item.get("state", ""),
    }


def _map_gitlab_item(item: dict, config: dict) -> dict:
    project_id = config.get("project_id", "")
    return {
        "ref": f"{project_id}/{item.get('iid', '')}",
        "title": item.get("title", ""),
        "subtitle": item.get("state", ""),
    }


def _map_bitbucket_item(item: dict, config: dict) -> dict:
    owner = config.get("owner", "")
    repo = config.get("repo", "")
    pr_id = item.get("id", "")
    return {
        "ref": f"{owner}/{repo}/{pr_id}",
        "title": item.get("title", ""),
        "subtitle": (item.get("state") or "").lower(),
    }


def _map_linear_item(item: dict) -> dict:
    state = item.get("state") or {}
    return {
        "ref": item.get("identifier", ""),
        "title": item.get("title", ""),
        "subtitle": state.get("name", "") if isinstance(state, dict) else "",
    }


def _map_status_item(item: dict) -> dict:
    status = item.get("status", "")
    subtitle = status.get("status", "") if isinstance(status, dict) else str(status)
    return {
        "ref": str(item.get("id", "")),
        "title": item.get("name", "") or item.get("title", ""),
        "subtitle": subtitle,
    }


def _map_notion_item(item: dict) -> dict:
    props = item.get("properties", {})
    title_prop = props.get("Name", props.get("title", {}))
    title_arr = title_prop.get("title", []) if isinstance(title_prop, dict) else []
    title = title_arr[0].get("text", {}).get("content", "") if title_arr else ""
    return {"ref": item.get("id", ""), "title": title, "subtitle": ""}


def _map_name_status_item(item: dict) -> dict:
    return {
        "ref": str(item.get("id", "")),
        "title": item.get("name", "") or item.get("title", "") or item.get("subject", ""),
        "subtitle": str(item.get("status", "")),
    }


def _map_item(item: dict, impl: str, config: dict) -> dict:
    mapper = _ITEM_MAPPERS.get(impl)
    if mapper:
        return mapper(item, config)
    ref = str(item.get("id", "") or item.get("key", "") or item.get("ref", ""))
    title = str(item.get("name", "") or item.get("title", "") or item.get("summary", "") or ref)
    return {"ref": ref, "title": title, "subtitle": ""}