# Acceptance Tests

End-to-end tests with Cypress against the Angular frontend.

## Structure

```
acceptance/
├── cypress.config.js          # Cypress config
└── cypress/
    ├── e2e/
    │   ├── cu01_verificar.cy.js   # STUB — CU-01: release verification
    │   └── form_validation.cy.js  # STUB — form validation
    └── support/
        ├── e2e.js                 # Global config
        └── commands.js            # cy.login(), cy.logout()
```

## Config

| Setting | Value |
|---------|-------|
| Base URL | `http://localhost:4200` |
| Viewport | 1280 x 720 |
| Default timeout | 10 s |
| Video recording | Off |

## Custom commands

| Command | Description |
|---------|-------------|
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
