module.exports = {
  e2e: {
    baseUrl: 'http://localhost:4200',
    specPattern: 'tests/acceptance/cypress/e2e/**/*.cy.js',
    supportFile: 'tests/acceptance/cypress/support/e2e.js',
    video: false,
    screenshotOnRunFailure: true,
    defaultCommandTimeout: 10000,
    viewportWidth: 1280,
    viewportHeight: 720,
  },
};
