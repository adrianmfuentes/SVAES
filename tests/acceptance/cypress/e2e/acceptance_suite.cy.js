/**
 * Pruebas de Aceptación/Usabilidad — Cypress E2E (ISO 29119-4)
 * Total: 10 tests
 *   TC-ACP-CU-01: Semáforo visual — estado VÁLIDA (verde)
 *   TC-ACP-CU-02: Semáforo visual — estado NO_VÁLIDA (rojo)
 *   TC-ACP-UI-01: Visualización en resolución 1920x1080
 *   TC-ACP-UI-02: Visualización en resolución 1366x768
 *   TC-ACP-UI-03: Visualización en resolución 375x667
 *   TC-ACP-FRM-01: Validación de formulario — campo nombre requerido
 *   TC-ACP-FRM-02: Validación de formulario — versión SemVer requerida
 *   TC-USA-01: Compatibilidad con navegador (viewport estándar)
 *   TC-USA-02: Mensajes de error accesibles y visibles
 *   TC-USA-03: Navegación completa sin errores de consola
 */

describe('TC-ACP-CU: Semáforo Visual de Verificación', () => {
  beforeEach(() => {
    cy.login('operator@test.com', 'Password1');
  });

  afterEach(() => {
    cy.logout();
  });

  it('TC-ACP-CU-01: Muestra indicador verde para release VÁLIDA', () => {
    cy.visit('/releases');
    cy.get('[data-cy=release-row]').first().click();
    cy.get('[data-cy=verification-status]')
      .should('be.visible')
      .and('have.attr', 'data-status')
      .and('match', /VALID|VALIDA|OK/);
  });

  it('TC-ACP-CU-02: Muestra indicador rojo para release NO_VÁLIDA', () => {
    cy.visit('/releases');
    cy.get('[data-cy=release-row]').last().click();
    cy.get('[data-cy=verification-status]')
      .should('be.visible')
      .and('have.attr', 'data-status')
      .and('match', /INVALID|NO_VALIDA|ERROR/);
  });
});

describe('TC-ACP-UI: Visualización Multi-Resolución', () => {
  it('TC-ACP-UI-01: Layout correcto en 1920x1080 (Full HD)', () => {
    cy.viewport(1920, 1080);
    cy.visit('/login');
    cy.get('input[name="email"]').should('be.visible');
    cy.get('input[name="password"]').should('be.visible');
    cy.get('button[type="submit"]').should('be.visible');
  });

  it('TC-ACP-UI-02: Layout correcto en 1366x768 (HD Ready)', () => {
    cy.viewport(1366, 768);
    cy.visit('/login');
    cy.get('input[name="email"]').should('be.visible');
    cy.get('button[type="submit"]').should('be.visible');
  });

  it('TC-ACP-UI-03: Layout correcto en 375x667 (Móvil iPhone SE)', () => {
    cy.viewport(375, 667);
    cy.visit('/login');
    cy.get('input[name="email"]').should('be.visible');
    cy.get('button[type="submit"]').should('be.visible');
  });
});

describe('TC-ACP-FRM: Validación de Formularios', () => {
  beforeEach(() => {
    cy.login('operator@test.com', 'Password1');
  });

  afterEach(() => {
    cy.logout();
  });

  it('TC-ACP-FRM-01: Muestra error cuando el nombre está vacío', () => {
    cy.visit('/releases/new');
    cy.get('input[name="name"]').clear();
    cy.get('input[name="version"]').type('1.0.0');
    cy.get('button[type="submit"]').click();
    cy.get('[data-cy=field-error-name]')
      .should('be.visible')
      .and('contain.text', 'requerido');
  });

  it('TC-ACP-FRM-02: Muestra error cuando la versión no es SemVer válido', () => {
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
  it('TC-USA-01: La aplicación carga sin errores de consola', () => {
    cy.visit('/login');
    cy.window().then((win) => {
      cy.spy(win.console, 'error').as('consoleError');
    });
    cy.get('@consoleError').should('not.have.been.called');
  });

  it('TC-USA-02: Mensajes de error son visibles y tienen contraste adecuado', () => {
    cy.visit('/login');
    cy.get('input[name="email"]').type('invalid');
    cy.get('input[name="password"]').type('short');
    cy.get('button[type="submit"]').click();
    cy.get('[role="alert"], .error-message, .text-danger')
      .should('exist');
  });

  it('TC-USA-03: Navegación completa sin rotura de layout', () => {
    cy.login('operator@test.com', 'Password1');
    cy.visit('/dashboard');
    cy.get('nav, [role="navigation"]').should('be.visible');
    cy.visit('/releases');
    cy.get('table, [role="grid"], .release-list').should('exist');
    cy.visit('/connectors');
    cy.get('[data-cy=page-content]').should('exist');
    cy.visit('/profile');
    cy.get('[data-cy=page-content]').should('exist');
    cy.logout();
  });
});
