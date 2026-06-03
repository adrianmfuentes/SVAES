# Acceptance Tests — Plan de Pruebas

End-to-end tests with Cypress against the Angular frontend. Follow ISO 29119-4 structured test case IDs.

## Structure

```
acceptance/
├── cypress.config.js                 # Cypress config
└── cypress/
    ├── e2e/
    │   └── acceptance_suite.cy.js    # TC-ACP-CU, TC-ACP-UI, TC-ACP-FRM, TC-USA (10 tests)
    └── support/
        ├── e2e.js                    # Global config (imports commands, suppresses uncaught exceptions)
        └── commands.js               # cy.login(email, password), cy.logout()
```

## Test Case Catalog

### TC-ACP-CU: Visual Traffic Light (2 cases)

| ID | Description |
|---|---|
| TC-ACP-CU-01 | Green indicator for VALIDA release |
| TC-ACP-CU-02 | Red indicator for NO_VALIDA release |

### TC-ACP-UI: Multi-Resolution Layout (3 cases)

| ID | Resolution |
|---|---|
| TC-ACP-UI-01 | 1920x1080 (Full HD) |
| TC-ACP-UI-02 | 1366x768 (HD Ready) |
| TC-ACP-UI-03 | 375x667 (iPhone SE) |

### TC-ACP-FRM: Form Validation (2 cases)

| ID | Description |
|---|---|
| TC-ACP-FRM-01 | Name field required → error visible |
| TC-ACP-FRM-02 | Invalid SemVer → error visible |

### TC-USA: Usability & Compatibility (3 cases)

| ID | Description |
|---|---|
| TC-USA-01 | Application loads without console errors |
| TC-USA-02 | Error messages visible with adequate contrast |
| TC-USA-03 | Full navigation (dashboard, releases, connectors, profile) without layout break |

## Config

| Setting | Value |
|---|---|
| Base URL | `http://localhost:4200` |
| Viewport | 1280 x 720 |
| Default timeout | 10 s |
| Video recording | Off |

## Custom commands

| Command | Description |
|---|---|
| `cy.login(email, password)` | Log in via login form |
| `cy.logout()` | Log out current user |

## Run

```bash
# Interactive
npx cypress open --config-file tests/acceptance/cypress.config.js

# Headless
npx cypress run --config-file tests/acceptance/cypress.config.js
```

## Prerequisites

1. Angular frontend running: `cd web && pnpm start`
2. API backend running at `http://localhost:8000`
3. Cypress installed: `npm install cypress`

## Total: 10 acceptance test cases
