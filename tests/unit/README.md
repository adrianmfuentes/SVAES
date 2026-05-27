# Unit Tests

Isolated component tests. All dependencies (repos, HTTP, task queue) are mocked via `unittest.mock.AsyncMock`. No database or external services needed.

Coverage: **80%** of `api/src/`.

## Structure

```
unit/
├── core/
│   ├── test_credential_encryptor.py   # FernetCredentialEncryptor: encrypt, decrypt, encrypt_bytes, decrypt_bytes
│   └── test_pseudonymizer.py          # pseudonymize: PII key hashing, nested dicts/lists, edge cases
├── connectors/
│   ├── conftest.py                    # mock_httpx_client, connector_config, gitlab/jira connectors
│   ├── test_gitlab.py                 # GitLabConnector: headers, URLs, fetch/list_artifact(), HTTP errors
│   └── test_jira.py                   # JiraConnector: Atlassian auth, JQL, fetch/list_artifact(), errors
└── api/
    ├── conftest.py                    # 14 mock repos, task queue, connector registry, test IDs
    ├── test_authenticate_user.py      # AuthenticateUserUseCase: auth success/failure, token creation, inactive user
    ├── test_connector_registry.py     # ConnectorRegistry: register, get_by_type, get_by_implementation, list_all
    ├── test_connector_service.py      # ConnectorService: CRUD, encryption, connection testing, status toggle
    ├── test_create_organization.py    # CreateOrganizationUseCase: create org, duplicate slug check
    ├── test_manage_artifacts.py       # ManageArtifactsUseCase: add, list, remove artifacts
    ├── test_notification_service.py   # NotificationService: channels, user preferences, subscribe/unsubscribe
    ├── test_organization_service.py   # OrganizationService: CRUD, projects, ownership transfer, restoration
    ├── test_password_hasher.py        # BcryptPasswordHasher: hash, verify, needs_rehash
    ├── test_profile_service.py        # ProfileService: CRUD, rules, reorder, duplication, default management
    ├── test_rate_limit.py             # Rate limiter: module-level Limiter instance
    ├── test_releases.py               # CreateReleaseUseCase: CRUD, states, artifacts, deletion, SemVer
    ├── test_toggle_connector_status.py # ToggleConnectorStatusUseCase: activate, deactivate, error states
    ├── test_update_release.py         # UpdateReleaseUseCase: update fields, SemVer validation
    └── test_user_service.py           # UserService: CRUD, roles, invitations, activation, account deletion
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
pytest tests/unit/ --cov=api/src --cov-report=xml

# Rust inline
cargo test --lib
```
