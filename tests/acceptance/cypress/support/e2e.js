import './commands';

Cypress.on('uncaught:exception', () => {
  return false;
});

const MOCK_RELEASES = [
  {
    id: 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
    name: 'Release 1.0.0',
    version: '1.0.0',
    verdict: 'VALID',
    status: 'VALIDA',
    organization_id: 'org1',
    organization_name: 'Test Org',
    project_id: 'proj-001',
    project_name: 'Test Project',
    created_at: '2026-01-15T10:30:00Z',
    created_by: 'operator@test.com',
    updated_at: '2026-01-15T10:30:00Z',
    description: 'First release',
  },
  {
    id: 'ffffffff-gggg-hhhh-iiii-jjjjjjjjjjjj',
    name: 'Release 0.9.0',
    version: '0.9.0',
    verdict: 'INVALID',
    status: 'NO_VALIDA',
    organization_id: 'org1',
    organization_name: 'Test Org',
    project_id: 'proj-001',
    project_name: 'Test Project',
    created_at: '2026-01-14T08:00:00Z',
    created_by: 'operator@test.com',
    updated_at: '2026-01-14T08:00:00Z',
    description: 'Failed release',
  },
];

const MOCK_RESULTS = [
  {
    id: 'res-001',
    release_id: 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
    verdict: 'VALID',
    rule_results: [
      { rule_id: 'RV-01', rule_name: 'Check PR', connector: 'GitHub', status: 'PASS', result: 'PASS', message: 'OK' },
    ],
    summary: { PASS: 1 },
    duration_ms: 150,
    executed_at: '2026-01-15T10:31:00Z',
  },
];

const MOCK_METRICS = {
  pass_rate: 95.5,
  total_releases: 42,
  total_verifications: 128,
  valid_releases: 38,
  invalid_releases: 2,
  pending_releases: 2,
};

const MOCK_PROJECTS = [
  { id: 'proj-001', name: 'Test Project' },
];

const MOCK_I18N_ES = {
  'release_new.name_required': 'El nombre es requerido',
  'release_new.version_required': 'La version es requerida',
  'release_new.title': 'Nueva Entrega',
  'release_new.form_title': 'Formulario de Entrega',
  'release_new.back_link': 'Volver a Entregas',
  'release_new.project_label': 'Proyecto',
  'release_new.project_placeholder': 'Seleccionar proyecto',
  'release_new.project_required': 'El proyecto es requerido',
  'release_new.name_label': 'Nombre',
  'release_new.name_placeholder': 'Nombre de la entrega',
  'release_new.version_label': 'Version',
  'release_new.description_label': 'Descripcion',
  'release_new.submit': 'Crear Entrega',
  'release_new.submitting': 'Creando...',
  'release_new.edit_title': 'Editar Entrega',
  'release_new.save': 'Guardar',
  'release_new.saving': 'Guardando...',
  'release_new.no_projects': 'No hay proyectos disponibles.',
  'release_new.error': 'Error al crear la entrega.',
  'common.cancel': 'Cancelar',
  'common.optional': 'opcional',
  'common.beta': 'BETA',
  'common.loading': 'Cargando...',
  'common.description': 'Descripcion',
  'common.dash': '\u2014',
  'common.edit': 'Editar',
  'common.delete': 'Eliminar',
  'common.deleting': 'Eliminando...',
  'common.confirm': 'Confirmar',
  'common.previous': 'Anterior',
  'common.next': 'Siguiente',
  'common.disabled_tooltip.form_invalid': 'Formulario incompleto',
  'common.disabled_tooltip.operation_in_progress': 'Operacion en curso',
  'common.disabled_tooltip.no_verification': 'Sin verificacion',
  'common.disabled_tooltip.verification_in_progress': 'Verificacion en curso',
  'common.disabled_tooltip.first_page': 'Primera pagina',
  'common.disabled_tooltip.last_page': 'Ultima pagina',
  'common.disabled_tooltip.no_connector': 'Seleccione un conector',
  'common.max_chars': 'Maximo {{max}} caracteres',
  'releases.title': 'Entregas',
  'releases.new_release': 'Nueva Entrega',
  'releases.global_view': 'Vista Global',
  'releases.filter_placeholder': 'Filtrar...',
  'releases.filter_all': 'Todas',
  'releases.table_id': 'ID',
  'releases.table_name': 'Nombre',
  'releases.col_org': 'Organizacion',
  'releases.table_verdict': 'Veredicto',
  'releases.table_date': 'Fecha',
  'releases.table_actions': 'Acciones',
  'releases.no_releases_filter': 'Sin resultados.',
  'releases.loading_error': 'Error al cargar entregas.',
  'releases.delete_confirm': '\u00bfEliminar esta entrega?',
  'releases.delete_error': 'Error al eliminar.',
  'verdict.VALID': 'VALIDA',
  'verdict.INVALID': 'NO VALIDA',
  'verdict.WITH_WARNINGS': 'CON ADVERTENCIAS',
  'verdict.NOT_EVALUATED': 'SIN EVALUAR',
  'release_detail.back_releases': '\u2190 Volver a Entregas',
  'release_detail.export_pdf': 'Exportar PDF',
  'release_detail.field_version': 'Version',
  'release_detail.field_status': 'Estado',
  'release_detail.project': 'Proyecto',
  'release_detail.field_org': 'Organizacion',
  'release_detail.field_created': 'Creado',
  'release_detail.field_updated': 'Actualizado',
  'release_detail.verification_title': 'Resultados de Verificacion',
  'release_detail.rule_id': 'ID Regla',
  'release_detail.rule_name': 'Nombre Regla',
  'release_detail.rule_connector': 'Conector',
  'release_detail.rule_result': 'Resultado',
  'release_detail.rule_evidence': 'Evidencia',
  'release_detail.see_more_btn': 'Ver mas',
  'release_detail.summary_label': 'Resumen:',
  'release_detail.col_duration': 'Duracion',
  'release_detail.col_executed': 'Ejecutado',
  'release_detail.col_type': 'Tipo',
  'release_detail.col_ext_ref': 'Ref. Externa',
  'release_detail.history': 'Historial',
  'release_detail.history_verdict': 'Veredicto',
  'release_detail.see_btn': 'Ver',
  'release_detail.empty_desc': 'Sin datos de verificacion.',
  'release_detail.add_artifact_first': 'Agrega artefactos primero.',
  'release_detail.start_verification_btn': 'Iniciar Verificacion',
  'release_detail.artifacts_title': 'Artefactos ({{n}})',
  'release_detail.verify_label': 'Verificar',
  'release_detail.verifying_label': 'Verificando...',
  'release_detail.cancel_verification': 'Cancelar',
  'release_detail.loading_error': 'Error al cargar.',
  'release_detail.no_id_error': 'ID no proporcionado.',
  'release_detail.verify_launched_title': 'Verificacion iniciada',
  'release_detail.verify_launched_desc': 'Recibiras una notificacion cuando termine.',
  'release_detail.verify_channel_web': 'Notificacion web',
  'release_detail.verify_channel_email': 'Correo electronico',
  'release_detail.verify_launched_dismiss': 'Entendido',
  'release_detail.verify_progress_title': 'Verificando...',
  'release_detail.export_error': 'Error al exportar.',
  'release_detail.verify_complete_toast': 'Verificacion completada.',
  'release_detail.verify_failed_toast': 'Verificacion fallida.',
  'shell.logout': 'Cerrar sesion',
  'shell.nav_dashboard': 'Dashboard',
  'shell.nav_releases': 'Entregas',
  'shell.nav_projects': 'Proyectos',
  'shell.nav_connectors': 'Conectores',
  'shell.nav_profiles': 'Perfiles',
  'shell.nav_my_profile': 'Mi Perfil',
  'shell.nav_main': 'Principal',
  'shell.nav_configuration': 'Configuracion',
  'shell.nav_account': 'Cuenta',
  'shell.nav_user_label': 'Navegacion de usuario',
  'shell.toggle_nav': 'Alternar navegacion',
  'a11y.skip_to_main': 'Saltar al contenido',
  'dashboard.title': 'Dashboard',
  'dashboard.pass_rate': 'Tasa de Aprobacion',
  'dashboard.total_releases': 'Total Entregas',
  'dashboard.verifications': 'Verificaciones',
  'dashboard.release_status': 'Estado de Entregas',
  'dashboard.release_valid': 'validas',
  'dashboard.release_invalid': 'no validas',
  'dashboard.release_pending': 'pendientes',
  'a11y.pass_rate_good': 'Buena',
  'a11y.pass_rate_fair': 'Regular',
  'a11y.pass_rate_poor': 'Baja',
  'system.error.loading_metrics': 'Error al cargar metricas.',
  'login.email_label': 'Correo Electronico',
  'login.email_placeholder': 'correo@ejemplo.com',
  'login.email_required': 'El correo es requerido',
  'login.email_invalid': 'Correo invalido',
  'login.password_label': 'Contrasena',
  'login.password_placeholder': 'Tu contrasena',
  'login.password_required': 'La contrasena es requerida',
  'login.submit': 'Iniciar Sesion',
  'login.verifying': 'Verificando...',
  'login.title': 'Iniciar Sesion',
  'login.context_title_line1': 'Sistema de',
  'login.context_title_line2': 'Verificacion',
  'login.context_title_line3': 'Automatizada',
  'login.context_desc': 'Valida entregas de software automaticamente.',
  'login.feature_rules': 'reglas',
  'login.feature_connectors': 'conectores',
  'login.back_home': 'Volver al inicio',
  'login.no_account': '\u00bfNo tienes cuenta?',
  'login.request_access': 'Solicitar acceso',
  'login.forgot_password': '\u00bfOlvidaste tu contrasena?',
  'login.footer_privacy': 'Privacidad',
  'login.footer_legal': 'Aviso Legal',
  'login.error.unexpected': 'Error inesperado.',
  'login.error.no_connection': 'Sin conexion al servidor.',
  'login.error.internal': 'Error interno del servidor.',
  'login.error.invalid_data': 'Datos invalidos.',
  'login.error.wrong_credentials': 'Credenciales incorrectas.',
  'login.error.auth_unavailable': 'Autenticacion no disponible.',
  'login.error.too_many': 'Demasiados intentos.',
  'login.error.server_unreachable': 'Servidor no disponible.',
  'release.import_artifacts': 'Importar Artefactos',
  'release.import_first_artifact': 'Importar primer artefacto',
  'release.no_artifacts': 'Sin artefactos.',
  'release.artifact_connector': 'Conector',
  'release.loading_connectors': 'Cargando conectores...',
  'release.no_connectors': 'No hay conectores disponibles.',
  'release.select_connector': 'Seleccionar conector',
  'release.select_connector_error': 'Seleccione un conector.',
  'release.connector_status_active': 'Activo',
  'release.artifact_type': 'Tipo de artefacto',
  'release.external_ref': 'Referencia externa',
  'release.external_ref_placeholder': 'ID de la tarea/documento/PR',
  'release.description_optional': 'Descripcion',
  'release.description_placeholder': 'Descripcion opcional...',
  'release.import': 'Importar',
  'release.importing': 'Importando...',
  'release.import_error': 'Error al importar.',
  'release.browse_search_placeholder': 'Buscar...',
  'release.browse_manual_label': 'Ingresar referencia manualmente',
  'release.browse_loading': 'Cargando...',
  'release.browse_error': 'Error al cargar.',
  'release.browse_empty': 'Sin resultados.',
  'release.confirm_delete_artifact_title': 'Eliminar artefacto',
  'release.confirm_delete_artifact_message': '\u00bfEstas seguro?',
  'release.artifact_delete_error': 'Error al eliminar.',
  'release.artifact_delete_success': 'Artefacto eliminado.',
  'artifact_type.TAREA': 'TAREA',
  'artifact_type.CODIGO': 'CODIGO',
  'artifact_type.DOCUMENTO': 'DOCUMENTO',
  'connector_type.github': 'GitHub',
  'connector_type.jira': 'Jira',
  'connector_type.confluence': 'Confluence',
  'landing.login_button': 'Iniciar Sesion',
  'landing.tagline': 'Automatiza tus verificaciones',
  'landing.eyebrow_hero': 'ENTREGAS CONFIABLES',
  'landing.heading_line1': 'Verificacion automatizada',
  'landing.heading_line2': 'de entregas de software',
  'landing.heading_line3': 'sin friccion',
  'landing.subtitle': 'SVAES conecta tus herramientas y valida cada entrega contra reglas configurables.',
  'landing.register_button': 'Solicitar Acceso',
  'landing.login_system_button': 'Iniciar Sesion',
  'landing.stat_rules': 'reglas',
  'landing.stat_connectors': 'conectores',
  'landing.stat_traceability': 'trazabilidad',
  'landing.mock_verification': 'VERIFICACION',
  'landing.aria_nav_main': 'Navegacion principal',
  'a11y.skip_to_main': 'Saltar al contenido principal',
  'projects.title': 'Proyectos',
  'projects.new_btn': 'Nuevo Proyecto',
  'shell.role_admin': 'Administrador',
  'shell.role_manager': 'Gestor',
  'shell.role_operator': 'Operador',
};

beforeEach(() => {
  cy.intercept('GET', '/assets/i18n/es.json', {
    statusCode: 200,
    body: MOCK_I18N_ES,
  }).as('i18n');

  cy.intercept({ method: 'GET', pathname: '/api/v1/releases' }, (req) => {
    req.reply({ statusCode: 200, body: MOCK_RELEASES });
  }).as('getReleases');

  cy.intercept({ method: 'GET', pathname: '/api/v1/releases/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee' }, {
    statusCode: 200,
    body: MOCK_RELEASES[0],
  }).as('getReleaseDetail1');

  cy.intercept({ method: 'GET', pathname: '/api/v1/releases/ffffffff-gggg-hhhh-iiii-jjjjjjjjjjjj' }, {
    statusCode: 200,
    body: MOCK_RELEASES[1],
  }).as('getReleaseDetail2');

  cy.intercept({ method: 'GET', pathname: '/api/v1/releases/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee/artifacts' }, {
    statusCode: 200,
    body: [],
  }).as('getArtifacts1');

  cy.intercept({ method: 'GET', pathname: '/api/v1/releases/ffffffff-gggg-hhhh-iiii-jjjjjjjjjjjj/artifacts' }, {
    statusCode: 200,
    body: [],
  }).as('getArtifacts2');

  cy.intercept({ method: 'GET', pathname: '/api/v1/releases/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee/results' }, {
    statusCode: 200,
    body: MOCK_RESULTS,
  }).as('getResults1');

  cy.intercept({ method: 'GET', pathname: '/api/v1/releases/ffffffff-gggg-hhhh-iiii-jjjjjjjjjjjj/results' }, {
    statusCode: 200,
    body: [{
      id: 'res-002',
      release_id: 'ffffffff-gggg-hhhh-iiii-jjjjjjjjjjjj',
      verdict: 'INVALID',
      rule_results: [],
      summary: {},
      duration_ms: 200,
      executed_at: '2026-01-14T08:01:00Z',
    }],
  }).as('getResults2');

  cy.intercept({ method: 'GET', pathname: '/api/v1/projects' }, {
    statusCode: 200,
    body: MOCK_PROJECTS,
  }).as('getProjects');

  cy.intercept({ method: 'GET', url: '/api/v1/projects/*/releases' }, {
    statusCode: 200,
    body: MOCK_RELEASES,
  }).as('getProjectReleases');

  cy.intercept({ method: 'GET', pathname: '/api/v1/dashboard/metrics' }, {
    statusCode: 200,
    body: MOCK_METRICS,
  }).as('getMetrics');

  cy.intercept({ method: 'GET', pathname: '/api/v1/organizations/org1/connectors' }, {
    statusCode: 200,
    body: [],
  }).as('getConnectors');

  cy.intercept({ method: 'GET', pathname: '/api/v1/organizations/org1/projects' }, {
    statusCode: 200,
    body: MOCK_PROJECTS,
  }).as('getOrgProjects');

  cy.intercept({ method: 'GET', pathname: '/api/v1/users/me' }, {
    statusCode: 200,
    body: {
      id: 'u1',
      email: 'operator@test.com',
      display_name: 'Test Operator',
      role: 'USER',
      totp_enabled: false,
    },
  }).as('getUserMe');

  cy.intercept({ method: 'GET', pathname: '/api/v1/users/u1/api-keys' }, {
    statusCode: 200,
    body: [],
  }).as('getApiKeys');

  cy.intercept({ method: 'GET', pathname: '/api/v1/organizations/org1' }, {
    statusCode: 200,
    body: { id: 'org1', name: 'Test Org', slug: 'test-org', owner_id: 'u1' },
  }).as('getOrgDetail');

  cy.intercept({ method: 'GET', pathname: '/api/v1/organizations/org1/users' }, {
    statusCode: 200,
    body: [],
  }).as('getOrgUsers');

  cy.intercept('POST', '/api/v1/**', {
    statusCode: 200,
    body: { id: 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee', status: 'VALIDA' },
  }).as('postAny');

  cy.intercept('PATCH', '/api/v1/**', {
    statusCode: 200,
    body: { id: 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee' },
  }).as('patchAny');

  cy.intercept('DELETE', '/api/v1/**', {
    statusCode: 200,
    body: {},
  }).as('deleteAny');
});
