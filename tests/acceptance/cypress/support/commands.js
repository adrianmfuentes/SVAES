Cypress.Commands.add('login', (email, password) => {
  cy.visit('/auth/login');
  const token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1MSIsImVtYWlsIjoib3BlcmF0b3JAdGVzdC5jb20iLCJyb2xlIjoiVVNFUiIsIm9yZ2FuaXphdGlvbl9pZCI6Im9yZzEiLCJleHAiOjk5OTk5OTk5OTl9.fake';
  localStorage.setItem('access_token', token);
  localStorage.setItem('refresh_token', 'fake-refresh-token');
  localStorage.setItem('user', JSON.stringify({
    id: 'u1',
    email: email || 'operator@test.com',
    display_name: 'Test Operator',
    role: 'USER',
    organization_id: 'org1',
  }));
});

Cypress.Commands.add('logout', () => {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  localStorage.removeItem('user');
});
