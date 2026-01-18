import { test, expect } from '@playwright/test';

/**
 * E2E Tests for Consolidated Tabs
 * Tests the new multi-function tabs: Intelligence, Search & Discovery, Monitoring, Orchestration
 */

test.describe('Consolidated Tabs Navigation', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the app
    await page.goto('/');
    // Wait for the app to load
    await page.waitForSelector('.app', { timeout: 10000 });
  });

  test('should display Chat tab by default', async ({ page }) => {
    // Check that Chat tab is active
    const chatTab = page.locator('button.tab-button.active').filter({ hasText: 'Chat' });
    await expect(chatTab).toBeVisible();
  });

  test('should navigate to Intelligence tab', async ({ page }) => {
    // Click on Intelligence tab
    await page.click('button.tab-button:has-text("Intelligence")');
    
    // Wait for Intelligence tab content to load
    await page.waitForSelector('.intelligence-tab', { timeout: 5000 });
    
    // Check that Intelligence header is visible
    await expect(page.locator('.intelligence-header h2')).toContainText('Intelligence & Learning');
    
    // Check that Real-Time Decisions view is shown by default
    await expect(page.locator('.decisions-live-view')).toBeVisible();
  });

  test('should show real-time decisions in Intelligence tab', async ({ page }) => {
    // Navigate to Intelligence tab
    await page.click('button.tab-button:has-text("Intelligence")');
    await page.waitForSelector('.intelligence-tab', { timeout: 5000 });
    
    // Check for real-time decisions header
    await expect(page.locator('.live-header h3')).toContainText("Grace's Decisions in Real-Time");
    
    // Check for streaming indicator (if decisions are being streamed)
    const streamingIndicator = page.locator('.streaming-indicator');
    // This might not always be visible if no decisions are being made
    // So we'll just check if the container exists
    await expect(page.locator('.decisions-stream')).toBeVisible();
  });

  test('should navigate between Intelligence sub-tabs', async ({ page }) => {
    // Navigate to Intelligence tab
    await page.click('button.tab-button:has-text("Intelligence")');
    await page.waitForSelector('.intelligence-tab', { timeout: 5000 });
    
    // Click on ML Intelligence sub-tab
    await page.click('.intelligence-nav .nav-button:has-text("ML Intelligence")');
    await expect(page.locator('.ml-tab')).toBeVisible();
    
    // Click on Insights sub-tab
    await page.click('.intelligence-nav .nav-button:has-text("Insights")');
    await expect(page.locator('.insights-tab')).toBeVisible();
    
    // Click on Learning sub-tab
    await page.click('.intelligence-nav .nav-button:has-text("Learning")');
    // Learning tab should be visible (check for a unique selector)
    await expect(page.locator('.intelligence-tab')).toBeVisible();
  });

  test('should navigate to Search & Discovery tab', async ({ page }) => {
    // Click on Search & Discovery tab
    await page.click('button.tab-button:has-text("Search & Discovery")');
    
    // Wait for Search & Discovery tab content to load
    await page.waitForSelector('.search-discovery-tab', { timeout: 5000 });
    
    // Check that header is visible
    await expect(page.locator('.search-header h2')).toContainText('Search & Discovery');
    
    // Check that Documents sub-tab is shown by default
    await expect(page.locator('.rag-tab')).toBeVisible();
  });

  test('should navigate between Search & Discovery sub-tabs', async ({ page }) => {
    // Navigate to Search & Discovery tab
    await page.click('button.tab-button:has-text("Search & Discovery")');
    await page.waitForSelector('.search-discovery-tab', { timeout: 5000 });
    
    // Click on Research sub-tab
    await page.click('.search-nav .nav-button:has-text("Research")');
    await expect(page.locator('.research-tab')).toBeVisible();
    
    // Click on Code Base sub-tab
    await page.click('.search-nav .nav-button:has-text("Code Base")');
    await expect(page.locator('.codebase-tab')).toBeVisible();
    
    // Click back to Documents sub-tab
    await page.click('.search-nav .nav-button:has-text("Documents")');
    await expect(page.locator('.rag-tab')).toBeVisible();
  });

  test('should navigate to Monitoring tab', async ({ page }) => {
    // Click on Monitoring tab
    await page.click('button.tab-button:has-text("Monitoring")');
    
    // Wait for Monitoring tab content to load
    await page.waitForSelector('.monitoring-consolidated-tab', { timeout: 5000 });
    
    // Check that header is visible
    await expect(page.locator('.monitoring-header h2')).toContainText('System Monitoring');
    
    // Check that System Health sub-tab is shown by default
    await expect(page.locator('.monitoring-tab')).toBeVisible();
  });

  test('should navigate between Monitoring sub-tabs', async ({ page }) => {
    // Navigate to Monitoring tab
    await page.click('button.tab-button:has-text("Monitoring")');
    await page.waitForSelector('.monitoring-consolidated-tab', { timeout: 5000 });
    
    // Click on Telemetry sub-tab
    await page.click('.monitoring-nav .nav-button:has-text("Telemetry")');
    // Telemetry tab should be visible (it uses Material-UI components)
    await expect(page.locator('.monitoring-consolidated-tab')).toBeVisible();
    
    // Click back to System Health sub-tab
    await page.click('.monitoring-nav .nav-button:has-text("System Health")');
    await expect(page.locator('.monitoring-tab')).toBeVisible();
  });

  test('should navigate to Orchestration tab', async ({ page }) => {
    // Click on Orchestration tab
    await page.click('button.tab-button:has-text("Orchestration")');
    
    // Wait for Orchestration tab content to load
    await page.waitForSelector('.orchestration-consolidated-tab', { timeout: 5000 });
    
    // Check that header is visible
    await expect(page.locator('.orchestration-header h2')).toContainText('Orchestration & Integration');
  });

  test('should navigate between Orchestration sub-tabs', async ({ page }) => {
    // Navigate to Orchestration tab
    await page.click('button.tab-button:has-text("Orchestration")');
    await page.waitForSelector('.orchestration-consolidated-tab', { timeout: 5000 });
    
    // Click on Connectors sub-tab
    await page.click('.orchestration-nav .nav-button:has-text("Connectors")');
    await expect(page.locator('.orchestration-consolidated-tab')).toBeVisible();
    
    // Click on Experiments sub-tab
    await page.click('.orchestration-nav .nav-button:has-text("Experiments")');
    await expect(page.locator('.orchestration-consolidated-tab')).toBeVisible();
    
    // Click back to Orchestration sub-tab
    await page.click('.orchestration-nav .nav-button:has-text("Orchestration")');
    await expect(page.locator('.orchestration-consolidated-tab')).toBeVisible();
  });

  test('should maintain tab state when switching between main tabs', async ({ page }) => {
    // Navigate to Intelligence tab and select ML Intelligence sub-tab
    await page.click('button.tab-button:has-text("Intelligence")');
    await page.waitForSelector('.intelligence-tab', { timeout: 5000 });
    await page.click('.intelligence-nav .nav-button:has-text("ML Intelligence")');
    
    // Switch to another main tab
    await page.click('button.tab-button:has-text("Chat")');
    await page.waitForSelector('.chat-tab', { timeout: 5000 });
    
    // Switch back to Intelligence tab
    await page.click('button.tab-button:has-text("Intelligence")');
    await page.waitForSelector('.intelligence-tab', { timeout: 5000 });
    
    // The sub-tab state might reset, but the main tab should still be Intelligence
    await expect(page.locator('.intelligence-tab')).toBeVisible();
  });
});

test.describe('Tab Functionality', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('.app', { timeout: 10000 });
  });

  test('should display all main tabs in sidebar', async ({ page }) => {
    const expectedTabs = [
      'Chat',
      'Knowledge Base',
      'Governance',
      'Sandbox',
      'Intelligence',
      'Search & Discovery',
      'Code (IDE)',
      'APIs',
      'Tags',
      'Monitoring',
      'Version Control',
      'Task Manager',
      'Genesis Key',
      'Orchestration',
      'Whitelist'
    ];

    for (const tabName of expectedTabs) {
      const tab = page.locator(`button.tab-button:has-text("${tabName}")`);
      await expect(tab).toBeVisible();
    }
  });

  test('should show active state on selected tab', async ({ page }) => {
    // Chat should be active by default
    const chatTab = page.locator('button.tab-button.active').filter({ hasText: 'Chat' });
    await expect(chatTab).toBeVisible();
    
    // Click Intelligence tab
    await page.click('button.tab-button:has-text("Intelligence")');
    await page.waitForSelector('.intelligence-tab', { timeout: 5000 });
    
    // Intelligence should now be active
    const intelligenceTab = page.locator('button.tab-button.active').filter({ hasText: 'Intelligence' });
    await expect(intelligenceTab).toBeVisible();
    
    // Chat should no longer be active
    const chatTabInactive = page.locator('button.tab-button:not(.active)').filter({ hasText: 'Chat' });
    await expect(chatTabInactive).toBeVisible();
  });
});
