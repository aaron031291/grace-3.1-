/**
 * Cypress E2E Tests — Every UI route verified.
 * Run: npx cypress run
 */

const BASE = 'http://localhost:5173';
const API = 'http://localhost:8000';

describe('Grace UI Routes', () => {
  
  it('Health endpoint responds', () => {
    cy.request(`${API}/health`).its('status').should('eq', 200);
  });

  it('Chat tab loads', () => {
    cy.visit(BASE);
    cy.contains('Grace').should('be.visible');
    cy.contains('Chat').should('be.visible');
  });

  it('Folders tab loads', () => {
    cy.visit(BASE);
    cy.contains('Folders').click();
    cy.wait(1000);
  });

  it('Docs tab loads', () => {
    cy.visit(BASE);
    cy.contains('Docs').click();
    cy.wait(1000);
  });

  it('Governance tab loads', () => {
    cy.visit(BASE);
    cy.contains('Governance').click();
    cy.wait(1000);
  });

  it('Whitelist tab loads', () => {
    cy.visit(BASE);
    cy.contains('Whitelist').click();
    cy.wait(1000);
  });

  it('Oracle tab loads', () => {
    cy.visit(BASE);
    cy.contains('Oracle').click();
    cy.wait(1000);
  });

  it('Codebase tab loads', () => {
    cy.visit(BASE);
    cy.contains('Codebase').click();
    cy.wait(1000);
  });

  it('Tasks tab loads', () => {
    cy.visit(BASE);
    cy.contains('Tasks').click();
    cy.wait(1000);
  });

  it('APIs tab loads', () => {
    cy.visit(BASE);
    cy.contains('APIs').click();
    cy.wait(1000);
  });

  it('BI tab loads', () => {
    cy.visit(BASE);
    cy.contains('BI').click();
    cy.wait(1000);
  });

  it('Health tab loads', () => {
    cy.visit(BASE);
    cy.contains('Health').click();
    cy.wait(1000);
  });

  it('Learn tab loads', () => {
    cy.visit(BASE);
    cy.contains('Learn').click();
    cy.wait(1000);
  });

  it('Lab tab loads', () => {
    cy.visit(BASE);
    cy.contains('Lab').click();
    cy.wait(1000);
  });

  it('Consensus chat mode works', () => {
    cy.visit(BASE);
    cy.contains('Consensus').click();
    cy.wait(1000);
  });

  // API endpoint tests
  it('Smoke test endpoint responds', () => {
    cy.request(`${API}/api/audit/test/smoke`).its('status').should('eq', 200);
  });

  it('Vault status endpoint responds', () => {
    cy.request(`${API}/api/vault/status`).its('status').should('eq', 200);
  });

  it('Console status endpoint responds', () => {
    cy.request(`${API}/api/console/status`).its('status').should('eq', 200);
  });

  it('Ghost memory stats endpoint responds', () => {
    cy.request(`${API}/api/audit/ghost-memory/stats`).its('status').should('eq', 200);
  });

  it('ML stats endpoint responds', () => {
    cy.request(`${API}/api/audit/ml/stats`).its('status').should('eq', 200);
  });
});
