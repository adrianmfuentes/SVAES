# Unit Tests

Isolated component tests. All dependencies (repos, HTTP, task queue) are mocked via `unittest.mock.AsyncMock`. No database or external services needed.

Coverage target: **>= 80%** of `api/src/`.

## Structure

```
unit/
├── core/
│   ├── test_credential_encryptor.py   # FernetCredentialEncryptor: encrypt, decrypt, encrypt_bytes, decrypt_bytes
│   └── test_pseudonymizer.py          # pseudonymize: PII key hashing, nested dicts/lists, edge cases
├── connectors/
│   ├── conftest.py                    # mock_httpx_client, connector_config, shared connector fixtures
│   ├── test_gitlab.py                 # GitLabConnector: headers, URLs, fetch/list_artifact(), HTTP errors
│   ├── test_jira.py                   # JiraConnector: Atlassian auth, JQL, fetch/list_artifact(), errors
│   ├── test_trello.py                 # TrelloConnector: board/card/list operations, API integration
│   ├── test_plane.py                  # PlaneConnector: workspace operations, issue fetching
│   ├── test_linear.py                 # LinearConnector: GraphQL API, team/issue queries
│   ├── test_jira_sm.py                # JiraServiceManagementConnector: ITSM operations
│   ├── test_redmine.py                # RedmineConnector: REST API, issue/project operations
│   ├── test_gitea.py                  # GiteaConnector: repository operations, PR/release handling
│   └── test_wikijs.py                 # WikiJSConnector: wiki page/document operations
├── api/
│   ├── conftest.py                    # 14 mock repos, task queue, connector registry, test IDs
│   ├── test_authenticate_user.py      # AuthenticateUserUseCase: auth success/failure, token creation, inactive user
│   ├── test_auth_service.py           # AuthService: register, login, logout, token refresh, profile
│   ├── test_connector_registry.py     # ConnectorRegistry: register, get_by_type, get_by_implementation, list_all
│   ├── test_connector_service.py      # ConnectorService: CRUD, encryption, connection testing, status toggle
│   ├── test_create_organization.py    # CreateOrganizationUseCase: create org, duplicate slug check
│   ├── test_organization_service.py   # OrganizationService: CRUD, projects, ownership transfer, restoration
│   ├── test_manage_artifacts.py       # ManageArtifactsUseCase: add, list, remove artifacts
│   ├── test_artifact_service.py       # ArtifactService: artifact lifecycle management
│   ├── test_notification_service.py   # NotificationService: channels, user preferences, subscribe/unsubscribe
│   ├── test_password_hasher.py        # BcryptPasswordHasher: hash, verify, needs_rehash
│   ├── test_profile_service.py        # ProfileService: CRUD, rules, reorder, duplication, default management
│   ├── test_manage_profile.py         # ManageProfileUseCase: profile creation, editing, validation
│   ├── test_rate_limit_middleware.py  # Rate limiter: module-level Limiter instance
│   ├── test_releases.py              # CreateReleaseUseCase: CRUD, states, artifacts, deletion, SemVer
│   ├── test_releases_router.py       # ReleaseRouter: HTTP endpoints, request validation, RBAC
│   ├── test_update_release.py        # UpdateReleaseUseCase: update fields, SemVer validation
│   ├── test_user_service.py          # UserService: CRUD, roles, invitations, activation, account deletion
│   ├── test_custom_role_service.py   # CustomRoleService: role CRUD, permissions management
│   ├── test_custom_roles_router.py   # CustomRolesRouter: HTTP endpoints, role assignment validation
│   ├── test_template_service.py      # TemplateService: template CRUD, versioning, inheritance
│   ├── test_templates_router.py      # TemplatesRouter: HTTP endpoints, template assignment
│   ├── test_export_service.py        # ExportService: report generation, CSV/JSON exports
│   ├── test_verification_service.py  # VerificationService: launch, poll, results retrieval
│   ├── test_launch_verification.py   # LaunchVerificationUseCase: 202/409/500, rule validation
│   ├── test_get_verification_history.py # GetVerificationHistoryUseCase: pagination, filtering
│   ├── test_verification_worker.py   # VerificationWorker: Celery task execution, engine communication
│   ├── test_celery_task_queue.py     # CeleryTaskQueue: enqueue, retry, failure handling
│   ├── test_manage_api_keys.py       # ManageApiKeysUseCase: create, revoke, list, permissions
│   ├── test_organizations_router.py  # OrganizationsRouter: HTTP endpoints, RBAC enforcement
│   ├── test_users_router.py          # UsersRouter: HTTP endpoints, role management
│   ├── test_api_keys_router.py       # ApiKeysRouter: HTTP endpoints, key lifecycle
│   ├── test_notifications_router.py  # NotificationsRouter: HTTP endpoints, channel configuration
│   └── test_toggle_connector_status.py # ToggleConnectorStatusUseCase: activate, deactivate, error states
└── repositories/
    ├── conftest.py                    # In-memory SQLite session, repository instances
    ├── test_base_sql_repository.py    # BaseSQLRepository: generic CRUD, pagination, filtering
    ├── test_user_repository.py        # UserRepository: CRUD, role queries, soft delete
    ├── test_release_repository.py     # ReleaseRepository: CRUD, state transitions, project scoping
    ├── test_project_repository.py     # ProjectRepository: CRUD, org scoping, archive/restore
    ├── test_organization_repository.py # OrganizationRepository: CRUD, slug uniqueness, member queries
    ├── test_connector_repository.py   # ConnectorRepository: CRUD, type filtering, status toggling
    ├── test_profile_repository.py     # ProfileRepository: CRUD, rule management, default profile
    ├── test_rule_repository.py        # RuleRepository: CRUD, catalog listing, search
    ├── test_artifact_repository.py    # ArtifactRepository: CRUD, release scoping, type filtering
    ├── test_verification_result_repository.py # VerificationResultRepository: CRUD, history queries
    ├── test_template_repository.py    # TemplateRepository: CRUD, org scoping, versioning
    ├── test_api_key_repository.py     # ApiKeyRepository: CRUD, expiry, revocation
    ├── test_notification_repository.py # NotificationRepository: channels, preferences, subscriptions
    ├── test_custom_role_repository.py # CustomRoleRepository: CRUD, permission sets
    └── test_verification_engine_interface.py # VerificationEngineInterface: HTTP client, retry, timeout
```

Rust inline unit tests live under `engine/src/` (rules RV-01 to RV-10 + aggregator) with `#[cfg(test)]`.

## Fixtures

### api/conftest.py

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

### repositories/conftest.py

| Fixture | Description |
|---------|-------------|
| `db_session` | In-memory SQLite session with all tables created |
| Repository instances | Real `UserRepository`, `ReleaseRepository`, `ProjectRepository`, etc. backed by SQLite |

### connectors/conftest.py

| Fixture | Description |
|---------|-------------|
| `mock_httpx_client` | Mock HTTPX async client for connector HTTP calls |
| `connector_config` | Sample connector configuration (URL, credentials, type) |

## Run

```bash
# All unit tests
pytest tests/unit/ -v -m unit

# Specific module
pytest tests/unit/api/test_releases.py -v

# With coverage
pytest tests/unit/ --cov=api/src --cov-report=term --cov-report=xml

# Rust inline tests
cargo test --lib
```

## Total: 59 test files across 4 directories (core, connectors, api, repositories)
