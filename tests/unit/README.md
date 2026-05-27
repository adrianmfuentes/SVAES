# Unit Tests

Isolated component tests. All dependencies (repos, HTTP, task queue) are mocked via `unittest.mock.AsyncMock`. No database or external services needed.

## Structure

```
unit/
├── connectors/
│   ├── conftest.py       # mock_httpx_client, connector_config, gitlab/jira connectors
│   ├── test_gitlab.py    # GitLabConnector: headers, URLs, fetch/list_artifact(), HTTP errors
│   └── test_jira.py      # JiraConnector: Atlassian auth, JQL, fetch/list_artifact(), errors
└── api/
    ├── conftest.py       # 14 mock repos, task queue, connector registry, test IDs
    └── test_releases.py  # CreateReleaseUseCase: CRUD, states, artifacts, deletion, SemVer
```

Rust inline unit tests live under `engine/src/` (rules RV-01 to RV-10 + aggregator) with `#[cfg(test)]`.

## Fixtures (api/conftest.py)

| Fixture | Description |
|---------|-------------|
| `mock_user_repository` | User repository mock |
| `mock_release_repository` | Release repository mock |
| `mock_project_repository` | Project repository mock |
| `mock_connector_repository` | Connector repository mock |
| `mock_organization_repository` | Organization repository mock |
| `mock_profile_repository` | Profile repository mock |
| `mock_artifact_repository` | Artifact repository mock |
| `mock_verification_result_repository` | Verification result repository mock |
| `mock_rule_repository` | Rule repository mock |
| `mock_custom_role_repository` | Custom role repository mock |
| `mock_api_key_repository` | API key repository mock |
| `mock_template_repository` | Template repository mock |
| `mock_notification_repository` | Notification repository mock |
| `mock_task_queue` | Async task queue mock |
| `mock_connector_registry` | Connector registry mock |
| `test_user_id` / `test_org_id` | UUID4 test IDs |

## Run

```bash
pytest tests/unit/ -v -m unit
pytest tests/unit/api/test_releases.py -v

# Rust inline
cargo test --lib
```
