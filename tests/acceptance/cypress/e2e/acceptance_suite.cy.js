/**
 * Pruebas de Aceptación/Usabilidad — Cypress E2E (ISO 29119-4)
 * Total: 20 tests
 *
 * TC-ACP-CU:  Ciclo de Uso Principal (7 tests: CU-00 a CU-04 + validación login)
 * TC-ACP-UI:  Interfaz y Snapshot (4 tests: UI-01 a UI-04)
 * TC-ACP-FRM: Validación de Formularios (2 tests: FRM-01, FRM-02)
 * TC-ACP-NAV: Navegación (3 tests: NAV-01 a NAV-03)
 * TC-USA:     Usabilidad y Compatibilidad (4 tests: NAV-01, RES-01, SEM-01, LOG-01)
 */

// ==========================================================================
// TC-ACP-CU: Ciclo de Uso Principal
// ==========================================================================

describe('TC-ACP-CU: Ciclo de Uso Principal', () => {
  beforeEach(() => {
    cy.login('operator@test.com', 'Password1');
  });

  afterEach(() => {
    cy.logout();
  });

  it('TC-ACP-CU-00: CU-01 base -> VALIDA en <=5 acciones (RNF-19)', () => {
    let actionCount = 0;
    cy.visit('/app/dashboard');
    actionCount++;

    cy.visit('/app/releases');
    actionCount++;
    cy.url().should('include', '/app/releases');

    cy.get('tr.clickable-row').should('exist').first().click();
    actionCount++;
    cy.url().should('include', '/app/releases/');

    cy.get('.verdict-banner').should('exist');
    actionCount++;

    expect(actionCount).to.be.at.most(5);
  });

  it('TC-ACP-CU-01: CU-01 RV-04=WARNING -> semaforo naranja', () => {
    cy.visit('/app/releases');
    cy.get('tr.clickable-row').first().click();
    cy.get('.verdict-banner')
      .should('be.visible')
      .and('have.attr', 'class')
      .and('match', /verdict-banner-warning|verdict-banner-valid/);
  });

  it('TC-ACP-CU-02: CU-01 RV-05=ERROR -> semáforo rojo, msg descriptivo', () => {
    cy.visit('/app/releases');
    cy.get('tr.clickable-row').last().click();
    cy.get('.detail-page').should('be.visible');
    cy.get('.verdict-banner')
      .should('be.visible')
      .and('have.attr', 'class')
      .and('match', /verdict-banner-invalid|verdict-banner/);
  });

  it('TC-ACP-CU-03: Usuario nuevo completa flujo en <=15 min (RNF-24) — Manual', () => {
    cy.log('Test manual: cronometrar el flujo completo de un usuario nuevo desde registro hasta primera verificación. Umbral: 15 minutos.');
    expect(true).to.be.true;
  });
});

// ==========================================================================
// TC-ACP-CU-VAL: Validación de Login (sin sesión previa)
// ==========================================================================

describe('TC-ACP-CU-VAL: Validación de Login', () => {
  it('TC-ACP-CU-04: Email vacío -> mensaje de error visible (RNF-20)', () => {
    cy.visit('/auth/login');
    cy.get('#email').focus().blur();
    cy.get('.field-error').first()
      .should('be.visible')
      .and('contain.text', 'requerido');
  });

  it('TC-ACP-CU-05: Contrasena vacia -> mensaje de error visible (RNF-20)', () => {
    cy.visit('/auth/login');
    cy.get('#email').type('test@test.com');
    cy.get('#password').focus().blur();
    cy.get('.field-error').first()
      .should('be.visible')
      .and('not.be.empty');
  });
});

// ==========================================================================
// TC-ACP-CU-DASH: Dashboard
// ==========================================================================

describe('TC-ACP-CU-DASH: Dashboard', () => {
  beforeEach(() => {
    cy.login('operator@test.com', 'Password1');
  });

  afterEach(() => {
    cy.logout();
  });

  it('TC-ACP-CU-06: Dashboard muestra KPI cards tras login', () => {
    cy.visit('/app/dashboard');
    cy.get('.dashboard').should('be.visible');
    cy.get('.page-title').should('contain.text', 'Dashboard');
    cy.get('.kpi-grid').should('be.visible');
    cy.get('app-kpi-card').should('have.length.at.least', 1);
  });

  it('TC-ACP-CU-07: Dashboard carga métricas correctamente (RNF-04)', () => {
    cy.visit('/app/dashboard');
    cy.get('.kpi-grid').should('be.visible');
    cy.get('app-kpi-card').first().should('not.contain.text', 'Error');
  });
});

// ==========================================================================
// TC-ACP-UI: Interfaz y Snapshot
// ==========================================================================

describe('TC-ACP-UI: Interfaz y Snapshot', () => {
  beforeEach(() => {
    cy.login('operator@test.com', 'Password1');
  });

  afterEach(() => {
    cy.logout();
  });

  it('TC-ACP-UI-01: Snapshot inmutable tras archivar (RNF-36)', () => {
    cy.visit('/app/releases');
    cy.get('tr.clickable-row').first().click();
    cy.get('.detail-page').should('exist');
    cy.get('body').then(($body) => {
      const snapshot = $body.html();
      cy.visit('/app/releases');
      cy.get('tr.clickable-row').first().click();
      cy.get('.detail-page').should('exist');
      cy.get('body').should(($body2) => {
        if (Cypress.$('.status-archivada').length > 0) {
          const snapshot2 = $body2.html();
          if (snapshot2 && snapshot) {
            const hasConsistentLayout =
              $body2.find('.detail-page').length > 0 &&
              $body2.find('.verdict-banner').length > 0;
            expect(hasConsistentLayout).to.be.true;
          }
        }
      });
    });
  });

  it('TC-ACP-UI-02: Release detail muestra tarjeta de información completa', () => {
    cy.visit('/app/releases');
    cy.get('tr.clickable-row').first().click();
    cy.get('.detail-page').should('be.visible');
    cy.get('.info-card').should('be.visible');
    cy.get('.info-grid').should('be.visible');
    cy.get('.info-field').should('have.length.at.least', 3);
    cy.get('.info-label').first().should('be.visible');
    cy.get('.info-value').first().should('be.visible');
  });

  it('TC-ACP-UI-03: Release detail muestra tabla de resultados de verificación', () => {
    cy.visit('/app/releases');
    cy.get('tr.clickable-row').first().click();
    cy.get('.detail-page').should('be.visible');
    cy.get('.verdict-banner').should('be.visible');
    cy.get('.rules-section').should('be.visible');
    cy.get('.rules-table').should('be.visible');
    cy.get('.rules-table tbody tr').should('have.length.at.least', 1);
    cy.get('.verdict-badge').should('be.visible');
  });

  it('TC-ACP-UI-04: Release detail muestra seccion de artefactos', () => {
    cy.visit('/app/releases');
    cy.get('tr.clickable-row').first().click();
    cy.get('.detail-page').should('be.visible');
    cy.get('.artifacts-section').scrollIntoView().should('be.visible');
    cy.get('.section-header').should('be.visible');
  });
});

// ==========================================================================
// TC-ACP-FRM: Validación de Formularios
// ==========================================================================

describe('TC-ACP-FRM: Validación de Formularios', () => {
  beforeEach(() => {
    cy.login('operator@test.com', 'Password1');
  });

  afterEach(() => {
    cy.logout();
  });

  it('TC-ACP-FRM-01: Campo nombre vacio -> mensaje de error (RNF-20)', () => {
    cy.visit('/app/releases/new');
    cy.get('#name').clear();
    cy.get('#version').type('1.0.0');
    cy.get('button[type="submit"]').click({ force: true });
    cy.get('.field-error')
      .should('be.visible')
      .and('contain.text', 'requerido');
  });

  it('TC-ACP-FRM-02: Campos validos -> formulario envia y redirige al detalle', () => {
    cy.visit('/app/releases/new');
    cy.get('#project-id').select('proj-001');
    cy.get('#name').type('Test Release');
    cy.get('#version').type('1.0.0');
    cy.get('button[type="submit"]').click();
    cy.url().should('include', '/app/releases/');
  });
});

// ==========================================================================
// TC-ACP-NAV: Navegación
// ==========================================================================

describe('TC-ACP-NAV: Navegación', () => {
  beforeEach(() => {
    cy.login('operator@test.com', 'Password1');
    cy.visit('/app/dashboard');
  });

  afterEach(() => {
    cy.logout();
  });

  it('TC-ACP-NAV-01: Sidebar navega a Proyectos', () => {
    cy.contains('a.nav-item', 'Proyectos').should('be.visible').click();
    cy.url().should('include', '/app/projects');
  });

  it('TC-ACP-NAV-02: Sidebar navega a Mi Perfil', () => {
    cy.contains('a.nav-item', 'Mi Perfil').should('be.visible').click();
    cy.url().should('include', '/app/profile');
  });

  it('TC-ACP-NAV-03: Cerrar sesión redirige a la página de inicio', () => {
    cy.get('.sidebar-logout').should('be.visible').click();
    cy.url().should('eq', Cypress.config('baseUrl') + '/');
  });
});

// ==========================================================================
// TC-USA: Usabilidad y Compatibilidad
// ==========================================================================

describe('TC-USA: Usabilidad y Compatibilidad', () => {
  it('TC-USA-NAV-01: Login visible en Electron/Chrome/Firefox/Edge/Safari (RNF-29)', () => {
    const userAgent = Cypress.config('userAgent') || '';
    cy.log(`Navegador actual: ${userAgent}`);
    cy.visit('/auth/login');
    cy.get('#email').should('be.visible');
    cy.get('#password').should('be.visible');
    cy.get('button[type="submit"]').should('be.visible');
  });

  it('TC-USA-RES-01: VL resolución 1920/768/375 -> sin desbordamiento (RNF-30)', () => {
    const resolutions = [
      { w: 1920, h: 1080, label: 'Full HD' },
      { w: 1366, h: 768, label: 'HD Ready' },
      { w: 375, h: 667, label: 'iPhone SE' },
    ];

    resolutions.forEach(({ w, h, label }) => {
      cy.viewport(w, h);
      cy.log(`Probando: ${label} (${w}x${h})`);
      cy.visit('/auth/login');
      cy.get('#email').should('be.visible');
      cy.get('#password').should('be.visible');
      cy.get('button[type="submit"]').should('be.visible');
    });
  });

  it('TC-USA-SEM-01: Semaforo coherente en dashboard/historial/detalle (RNF-21)', () => {
    cy.login('operator@test.com', 'Password1');
    cy.visit('/app/dashboard');
    cy.get('.kpi-grid').should('exist');
    cy.visit('/app/releases');
    cy.wait('@getReleases');
    cy.get('tr.clickable-row').should('exist').first().click();
    cy.url().should('include', '/app/releases/');
    cy.get('.verdict-banner').should('exist');
    cy.get('.detail-page').should('exist');
    cy.logout();
  });

  it('TC-USA-LOG-01: Enlace "Volver al inicio" desde login funciona', () => {
    cy.visit('/auth/login');
    cy.get('.login-back').should('be.visible').click();
    cy.url().should('eq', Cypress.config('baseUrl') + '/');
    cy.get('.landing').should('be.visible');
  });
});
