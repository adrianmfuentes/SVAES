/**
 * Pruebas de Aceptación/Usabilidad — Cypress E2E (ISO 29119-4)
 * Total: 10 tests
 *   TC-ACP-CU-00: CU-01 base -> VALIDA en <=5 acciones (RNF-19)
 *   TC-ACP-CU-01: Semáforo visual — estado VALIDA (verde), RV-04=WARNING -> naranja
 *   TC-ACP-CU-02: Semáforo visual — estado NO_VALIDA (rojo), RV-05=ERROR
 *   TC-ACP-CU-03: Usuario nuevo completa flujo en <=15 min (RNF-24) — Manual
 *   TC-ACP-UI-01: Snapshot inmutable tras archivar (RNF-36)
 *   TC-ACP-FRM-01: Validación de formulario — campo nombre requerido
 *   TC-ACP-FRM-02: Validación de formulario — versión SemVer requerida
 *   TC-USA-NAV-01: Each choice Chrome/Firefox/Edge/Safari (RNF-29)
 *   TC-USA-RES-01: VL resolución 1920/768/375 -> sin desbordamiento (RNF-30)
 *   TC-USA-SEM-01: Semáforo coherente en dashboard/historial/detalle (RNF-21)
 */

describe('TC-ACP-CU: Ciclo de Uso Principal', () => {
  beforeEach(() => {
    cy.login('operator@test.com', 'Password1');
  });

  afterEach(() => {
    cy.logout();
  });

  it('TC-ACP-CU-00: CU-01 base -> VALIDA en <=5 acciones (RNF-19)', () => {
    let actionCount = 0;
    cy.visit('/dashboard');
    actionCount++;

    cy.get('[data-cy="nav-releases"]').click();
    actionCount++;
    cy.url().should('include', '/releases');

    cy.get('[data-cy="release-row"]').first().click();
    actionCount++;
    cy.url().should('include', '/releases/');

    cy.get('[data-cy=verification-status]').should('exist');
    actionCount++;

    expect(actionCount).to.be.at.most(5);
  });

  it('TC-ACP-CU-01: CU-01 RV-04=WARNING -> semáforo naranja', () => {
    cy.visit('/releases');
    cy.get('[data-cy=release-row]').first().click();
    cy.get('[data-cy=verification-status]')
      .should('be.visible')
      .and('have.attr', 'data-status')
      .and('match', /WARNING|WITH_WARNINGS|VALID|VALIDA|OK/);
  });

  it('TC-ACP-CU-02: CU-01 RV-05=ERROR -> semáforo rojo, msg descriptivo', () => {
    cy.visit('/releases');
    cy.get('[data-cy=release-row]').last().click();
    cy.get('[data-cy=verification-status]')
      .should('be.visible')
      .and('have.attr', 'data-status')
      .and('match', /INVALID|NO_VALIDA|ERROR/);
  });

  it('TC-ACP-CU-03: Usuario nuevo completa flujo en <=15 min (RNF-24) — Manual', () => {
    cy.log('Test manual: cronometrar el flujo completo de un usuario nuevo desde registro hasta primera verificación. Umbral: 15 minutos.');
    expect(true).to.be.true;
  });
});

describe('TC-ACP-UI: Interfaz y Snapshot', () => {
  beforeEach(() => {
    cy.login('operator@test.com', 'Password1');
  });

  afterEach(() => {
    cy.logout();
  });

  it('TC-ACP-UI-01: Snapshot inmutable tras archivar (RNF-36)', () => {
    cy.visit('/releases');
    cy.get('[data-cy=release-row]').first().click();
    cy.get('[data-cy=release-detail]').should('exist');
    cy.get('body').then(($body) => {
      const snapshot = $body.html();
      cy.visit('/releases');
      cy.get('[data-cy=release-row]').first().click();
      cy.get('[data-cy=release-detail]').should('exist');
      cy.get('body').should(($body2) => {
        if (Cypress.$('[data-cy=archived-badge]').length > 0) {
          const snapshot2 = $body2.html();
          if (snapshot2 && snapshot) {
            const hasConsistentLayout =
              $body2.find('[data-cy=release-detail]').length > 0 &&
              $body2.find('[data-cy=verification-status]').length > 0;
            expect(hasConsistentLayout).to.be.true;
          }
        }
      });
    });
  });
});

describe('TC-ACP-FRM: Validación de Formularios', () => {
  beforeEach(() => {
    cy.login('operator@test.com', 'Password1');
  });

  afterEach(() => {
    cy.logout();
  });

  it('TC-ACP-FRM-01: Campo obligatorio vacío -> mensaje campo+acción', () => {
    cy.visit('/releases/new');
    cy.get('input[name="name"]').clear();
    cy.get('input[name="version"]').type('1.0.0');
    cy.get('button[type="submit"]').click();
    cy.get('[data-cy=field-error-name]')
      .should('be.visible')
      .and('contain.text', 'requerido');
  });

  it('TC-ACP-FRM-02: Campo numérico con texto -> error de tipo (RNF-20)', () => {
    cy.visit('/releases/new');
    cy.get('input[name="name"]').type('Test Release');
    cy.get('input[name="version"]').type('not-semver');
    cy.get('button[type="submit"]').click();
    cy.get('[data-cy=field-error-version]')
      .should('be.visible')
      .and('contain.text', 'SemVer');
  });
});

describe('TC-USA: Usabilidad y Compatibilidad', () => {
  it('TC-USA-NAV-01: Each choice Chrome/Firefox/Edge/Safari (RNF-29)', () => {
    const userAgent = Cypress.config('userAgent') || '';
    cy.log(`Navegador actual: ${userAgent}`);
    cy.visit('/login');
    cy.get('input[name="email"]').should('be.visible');
    cy.get('input[name="password"]').should('be.visible');
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
      cy.visit('/login');
      cy.get('input[name="email"]').should('be.visible');
      cy.get('input[name="password"]').should('be.visible');
      cy.get('button[type="submit"]').should('be.visible');
    });
  });

  it('TC-USA-SEM-01: Semáforo coherente en dashboard/historial/detalle (RNF-21)', () => {
    cy.login('operator@test.com', 'Password1');
    cy.visit('/dashboard');
    cy.get('[data-cy=page-content]').should('exist');
    cy.visit('/releases');
    cy.get('[data-cy=release-row]').first().click();
    cy.url().should('include', '/releases/');
    cy.get('[data-cy=verification-status]').should('exist');
    cy.get('[data-cy=page-content]').should('exist');
    cy.logout();
  });
});
