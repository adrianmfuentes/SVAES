"""Public HTTP dependencies and service factories."""

from bootstrap.authentication import (
    CurrentUser as CurrentUser,
    get_current_user as get_current_user,
    get_current_user_api_key_only as get_current_user_api_key_only,
    get_current_user_id as get_current_user_id,
    get_current_user_or_api_key as get_current_user_or_api_key,
    get_current_user_role as get_current_user_role,
)
from bootstrap.authorization import (
    ProjectAccess as ProjectAccess,
    require_api_key_access as require_api_key_access,
    require_connector_access as require_connector_access,
    require_custom_role_access as require_custom_role_access,
    require_notification_channel_access as require_notification_channel_access,
    require_org_access as require_org_access,
    require_permission as require_permission,
    require_profile_access as require_profile_access,
    require_project_access as require_project_access,
    require_release_access as require_release_access,
    require_role as require_role,
    require_rule_access as require_rule_access,
)
from bootstrap.repositories import (
    get_api_key_repository as get_api_key_repository,
    get_artifact_repository as get_artifact_repository,
    get_connector_registry as get_connector_registry,
    get_connector_repository as get_connector_repository,
    get_custom_role_repository as get_custom_role_repository,
    get_notification_repository as get_notification_repository,
    get_organization_repository as get_organization_repository,
    get_profile_repository as get_profile_repository,
    get_project_repository as get_project_repository,
    get_release_repository as get_release_repository,
    get_rule_repository as get_rule_repository,
    get_task_queue as get_task_queue,
    get_template_repository as get_template_repository,
    get_user_membership_repository as get_user_membership_repository,
    get_user_repository as get_user_repository,
    get_verification_result_repository as get_verification_result_repository,
)
from features.admin.container import (
    get_rules_service as get_rules_service,
)
from features.connectors.container import (
    get_connector_service as get_connector_service,
    get_webhook_use_case as get_webhook_use_case,
)
from features.identity.container import (
    get_auth_service as get_auth_service,
    get_create_access_request as get_create_access_request,
    get_custom_role_service as get_custom_role_service,
    get_jwt_handler as get_jwt_handler,
    get_password_hasher as get_password_hasher,
    get_settings_dependency as get_settings_dependency,
    get_user_service as get_user_service,
)
from features.notifications.container import (
    get_notification_service as get_notification_service,
)
from features.organizations.container import (
    get_create_organization as get_create_organization,
    get_organization_service as get_organization_service,
)
from features.projects_releases.container import (
    get_artifact_service as get_artifact_service,
    get_release_service as get_release_service,
)
from features.reporting.container import (
    get_export_service as get_export_service,
)
from features.verification.container import (
    get_profile_service as get_profile_service,
    get_task_service as get_task_service,
    get_template_service as get_template_service,
    get_verification_service as get_verification_service,
)
