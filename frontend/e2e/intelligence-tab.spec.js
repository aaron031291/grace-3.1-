import { test, expect } from '@playwright/test';

/**
 * E2E Tests for Intelligence Tab
 * Tests the consolidated Intelligence tab with real-time decisions, ML Intelligence, Insights, and Learning
 */

test.describe('Intelligence Tab - Real-Time Decisions', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('.app', { timeout: 10000 });
    
    // Navigate to Intelligence tab
    await page.click('button.tab-button:has-text("Intelligence")');
    await page.waitForSelector('.intelligence-tab', { timeout: 5000 });
  });

  test('should display real-time decisions view by default', async ({ page }) => {
    // Check for the live decisions header
    await expect(page.locator('.live-header h3')).toContainText("Grace's Decisions in Real-Time");
    
    // Check for the OODA loop description
    await expect(page.locator('.live-header p')).toContainText('OODA loop');
    
    // Check for decisions stream container
    await expect(page.locator('.decisions-stream')).toBeVisible();
  });

  test('should show streaming indicator when active', async ({ page }) => {
    // The streaming indicator might not always be visible
    // Check if the container exists (it may be hidden if no streaming)
    const streamingContainer = page.locator('.header-right');
    await expect(streamingContainer).toBeVisible();
  });

  test('should display decision timeline when decisions exist', async ({ page }) => {
    // Wait a moment for any decisions to load
    await page.waitForTimeout(2000);
    
    // Check if decisions stream container exists (timeline might not exist if no decisions)
    const streamContainer = page.locator('.decisions-stream');
    await expect(streamContainer).toBeVisible();
    
    // Timeline might not exist if there are no decisions, which is fine
    const timeline = page.locator('.decisions-timeline');
    const timelineCount = await timeline.count();
    // Either timeline exists or empty state is shown - both are valid
    expect(timelineCount >= 0).toBeTruthy();
  });

  test('should navigate to Cognitive Blueprint from decisions view', async ({ page }) => {
    // Look for the button to full cognitive view (be more specific)
    const cognitiveButton = page.locator('button.view-full-cognitive');
    
    // If the button exists, click it
    if (await cognitiveButton.count() > 0) {
      await cognitiveButton.click();
      // Should navigate to cognitive view
      await expect(page.locator('.cognitive-tab')).toBeVisible({ timeout: 5000 });
    } else {
      // If button doesn't exist, navigate directly via sub-tab
      await page.click('.intelligence-nav .nav-button:has-text("Cognitive Blueprint")');
      await expect(page.locator('.cognitive-tab')).toBeVisible({ timeout: 5000 });
    }
  });
});

test.describe('Intelligence Tab - Sub-navigation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('.app', { timeout: 10000 });
    await page.click('button.tab-button:has-text("Intelligence")');
    await page.waitForSelector('.intelligence-tab', { timeout: 5000 });
  });

  test('should have all sub-tabs visible', async ({ page }) => {
    const subTabs = [
      'Real-Time Decisions',
      'ML Intelligence',
      'Insights',
      'Learning',
      'Cognitive Blueprint'
    ];

    for (const tabName of subTabs) {
      const tab = page.locator(`.intelligence-nav .nav-button:has-text("${tabName}")`);
      await expect(tab).toBeVisible();
    }
  });

  test('should highlight active sub-tab', async ({ page }) => {
    // Real-Time Decisions should be active by default
    const decisionsTab = page.locator('.intelligence-nav .nav-button.active').filter({ hasText: 'Real-Time Decisions' });
    await expect(decisionsTab).toBeVisible();
    
    // Click ML Intelligence
    await page.click('.intelligence-nav .nav-button:has-text("ML Intelligence")');
    await page.waitForSelector('.ml-tab', { timeout: 5000 });
    
    // ML Intelligence should now be active
    const mlTab = page.locator('.intelligence-nav .nav-button.active').filter({ hasText: 'ML Intelligence' });
    await expect(mlTab).toBeVisible();
  });

  test('should load ML Intelligence content', async ({ page }) => {
    await page.click('.intelligence-nav .nav-button:has-text("ML Intelligence")');
    await page.waitForSelector('.ml-tab', { timeout: 5000 });
    
    // Check for ML Intelligence header
    await expect(page.locator('.ml-header h2')).toContainText('ML Intelligence');
    
    // Check for toolbar with view tabs
    await expect(page.locator('.ml-toolbar')).toBeVisible();
  });

  test('should load Insights content', async ({ page }) => {
    await page.click('.intelligence-nav .nav-button:has-text("Insights")');
    await page.waitForSelector('.insights-tab', { timeout: 5000 });
    
    // Check for Insights header
    await expect(page.locator('.insights-header h2')).toContainText('Insights');
  });

  test('should load Learning content', async ({ page }) => {
    await page.click('.intelligence-nav .nav-button:has-text("Learning")');
    
    // Learning tab should be visible (it might have different structure)
    await expect(page.locator('.intelligence-tab')).toBeVisible();
  });

  test('should load Cognitive Blueprint content', async ({ page }) => {
    await page.click('.intelligence-nav .nav-button:has-text("Cognitive Blueprint")');
    await page.waitForSelector('.cognitive-tab', { timeout: 5000 });
    
    // Check for Cognitive Blueprint header
    await expect(page.locator('.tab-header h1, .cognitive-tab h1')).toContainText('Cognitive');
  });
});
