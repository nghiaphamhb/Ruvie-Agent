/**
 * F016: Browser interaction tests for OrganizationModelPolicyEditor.
 * Uses programmatic Vite server with memory HTML bootstrap and mounted Svelte 5 harness.
 */
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';
import { createServer as createViteServer } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

const require = createRequire(import.meta.url);

// Resolve Playwright module
let playwrightModule = process.env.RUVIE_PLAYWRIGHT_PATH;
if (!playwrightModule) {
  try {
    playwrightModule = require.resolve('playwright');
  } catch {
    try {
      playwrightModule =
        require.resolve('../node_modules/.f014-browser-tools/node_modules/playwright');
    } catch {
      playwrightModule = null;
    }
  }
}

// Prefer an explicitly configured executable; otherwise use Playwright's matching installation.
const browserExecutable = process.env.RUVIE_BROWSER_PATH;

if (!playwrightModule) {
  console.error('Browser check bị chặn: Không tìm thấy module Playwright');
  process.exit(1);
}

const { chromium } = require(playwrightModule);

const frontendRoot = fileURLToPath(new URL('../', import.meta.url));

let viteServer;
let browser;
let checks = 0;

try {
  // 1. Start programmatic Vite server on random loopback port
  viteServer = await createViteServer({
    root: frontendRoot,
    configFile: false,
    plugins: [
      svelte(),
      {
        name: 'f016-browser-test-entry',
        resolveId(id) {
          if (id === '/__f016_browser_entry.js') return '\0f016-browser-entry';
        },
        load(id) {
          if (id === '\0f016-browser-entry') {
            return `
              import { mount } from 'svelte';
              import Harness from '/tests/fixtures/F016ModelPolicyEditorHarness.svelte';
              import '/src/styles/base.css';
              import '/src/styles/workspace.css';

              const app = document.getElementById('app');
              mount(Harness, { target: app });
            `;
          }
        },
      },
    ],
    server: { host: '127.0.0.1', port: 0, hmr: false },
    appType: 'custom',
  });

  viteServer.middlewares.use('/favicon.ico', (_req, res) => {
    res.statusCode = 204;
    res.end();
  });

  viteServer.middlewares.use('/__f016_test', (_req, res) => {
    res.setHeader('Content-Type', 'text/html');
    res.end(`<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>F016 Model Policy Editor Test</title>
</head>
<body>
  <div class="workspace-shell" data-theme="light">
    <div id="app"></div>
  </div>
  <script type="module" src="/__f016_browser_entry.js"></script>
</body>
</html>`);
  });

  await viteServer.listen();
  const port = viteServer.httpServer.address().port;
  const testUrl = `http://127.0.0.1:${port}/__f016_test`;

  // 2. Launch browser
  try {
    browser = await chromium.launch({
      executablePath: browserExecutable || undefined,
      headless: true,
    });
  } catch (launchErr) {
    console.error('Browser check bị chặn: Không thể khởi chạy Chromium', launchErr.message);
    throw launchErr;
  }

  const page = await browser.newPage({
    locale: 'vi-VN',
    viewport: { width: 1280, height: 800 },
  });
  page.setDefaultTimeout(8000);

  const pageErrors = [];
  const consoleErrors = [];
  page.on('pageerror', (err) => pageErrors.push(err.message));
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      consoleErrors.push(msg.text());
    }
  });

  await page.goto(testUrl);
  await page.waitForSelector('.model-policy-editor');

  // Verify harness bridge is mounted
  await page.waitForFunction(() => typeof window.__f016Harness !== 'undefined');

  // Initial state check: no initial callback fired on mount
  let callbacks = await page.evaluate(() => window.__f016Harness.getCallbacks());
  assert.equal(callbacks.length, 0, 'No callbacks must be fired on initial mount');
  checks++;

  // A parent may decline a callback; native inputs must still reflect controlled props.
  await page.evaluate(() => window.__f016Harness.setAutoApply(false));
  await page.locator('#f016-editor-allow-1').click();
  assert.equal(await page.locator('#f016-editor-allow-1').isChecked(), false);
  await page.evaluate(() => {
    window.__f016Harness.setAutoApply(true);
    window.__f016Harness.clearCallbacks();
  });
  checks++;

  assert.equal(
    await page.getByRole('checkbox', { name: /Cấp quyền.*GPT-4o.*openai\/gpt-4o/ }).count(),
    1,
  );
  assert.equal(
    await page.getByRole('radio', { name: /Mặc định.*Llama 3 8B.*meta-llama/ }).count(),
    1,
  );
  checks++;

  // -------------------------------------------------------------
  // Test 1: Checkbox emits correct draft array; radio only picks allowed model
  // -------------------------------------------------------------
  // Current models:
  // 0: meta-llama/llama-3-8b (allowed, default)
  // 1: openai/gpt-4o (not allowed)
  // 2: anthropic/claude-3-opus (unavailable, not allowed)
  // 3: mistralai/mistral-large-2407 (not allowed)

  // Allow GPT-4o
  const gptCheckbox = page.locator('#f016-editor-allow-1');
  assert.equal(await gptCheckbox.isChecked(), false);
  await gptCheckbox.check();

  callbacks = await page.evaluate(() => window.__f016Harness.getCallbacks());
  assert.equal(callbacks.length, 1);
  assert.deepEqual(callbacks[0].allowedModelIds, ['meta-llama/llama-3-8b', 'openai/gpt-4o']);
  assert.equal(callbacks[0].defaultModelId, 'meta-llama/llama-3-8b');
  checks++;

  // Now select GPT-4o as default
  const gptRadio = page.locator('#f016-editor-default-1');
  assert.equal(await gptRadio.isEnabled(), true);
  await page.evaluate(() => window.__f016Harness.setAutoApply(false));
  await gptRadio.click();
  assert.equal(await gptRadio.isChecked(), false);
  assert.equal(await page.locator('#f016-editor-default-0').isChecked(), true);
  await page.evaluate(() => {
    window.__f016Harness.setAutoApply(true);
    window.__f016Harness.clearCallbacks();
  });
  // Restore the callback history expected by the existing checks below.
  await page.evaluate(() => {
    window.__f016Harness.setProps({
      allowedModelIds: ['meta-llama/llama-3-8b'],
      defaultModelId: 'meta-llama/llama-3-8b',
    });
  });
  await gptCheckbox.check();
  await gptRadio.check();

  callbacks = await page.evaluate(() => window.__f016Harness.getCallbacks());
  assert.equal(callbacks.length, 2);
  assert.equal(callbacks[1].defaultModelId, 'openai/gpt-4o');
  checks++;

  // Mistral Large is not allowed, so its radio must be disabled
  const mistralRadio = page.locator('#f016-editor-default-3');
  assert.equal(await mistralRadio.isDisabled(), true);
  checks++;

  // -------------------------------------------------------------
  // Test 2: Unallowing default model emits defaultModelId: null
  // -------------------------------------------------------------
  // GPT-4o is currently default and allowed. Uncheck GPT-4o allow checkbox.
  await gptCheckbox.uncheck();

  callbacks = await page.evaluate(() => window.__f016Harness.getCallbacks());
  assert.equal(callbacks.length, 3);
  assert.equal(
    callbacks[2].defaultModelId,
    null,
    'Unallowing default model must emit null defaultModelId',
  );
  assert.deepEqual(callbacks[2].allowedModelIds, ['meta-llama/llama-3-8b']);
  checks++;

  // -------------------------------------------------------------
  // Test 3: Unavailable model cannot be allowed or made default; but if allowed, can be unallowed
  // -------------------------------------------------------------
  // Claude 3 Opus is available: false, and currently not allowed.
  const claudeCheckbox = page.locator('#f016-editor-allow-2');
  const claudeRadio = page.locator('#f016-editor-default-2');
  assert.equal(
    await claudeCheckbox.isDisabled(),
    true,
    'Unavailable model not allowed cannot be checked',
  );
  assert.equal(await claudeRadio.isDisabled(), true, 'Unavailable model cannot be set as default');
  checks++;

  // If Claude was already allowed by parent:
  await page.evaluate(() => {
    window.__f016Harness.clearCallbacks();
    window.__f016Harness.setProps({
      allowedModelIds: ['meta-llama/llama-3-8b', 'anthropic/claude-3-opus'],
      defaultModelId: 'meta-llama/llama-3-8b',
    });
  });

  // Verify parent update reflected without triggering callback
  callbacks = await page.evaluate(() => window.__f016Harness.getCallbacks());
  assert.equal(callbacks.length, 0, 'Updating props from parent must not fire callback');
  assert.equal(await claudeCheckbox.isChecked(), true);
  assert.equal(
    await claudeCheckbox.isEnabled(),
    true,
    'Unavailable model that is allowed can be unchecked',
  );
  assert.equal(await claudeRadio.isDisabled(), true, 'Unavailable model still cannot be default');
  checks++;

  // Uncheck Claude
  await claudeCheckbox.uncheck();
  callbacks = await page.evaluate(() => window.__f016Harness.getCallbacks());
  assert.equal(callbacks.length, 1);
  assert.deepEqual(callbacks[0].allowedModelIds, ['meta-llama/llama-3-8b']);
  checks++;

  // -------------------------------------------------------------
  // Test 4: Search by ID and name; no-matches display; search does not lose selections
  // -------------------------------------------------------------
  const searchInput = page.locator('#f016-editor-search');

  // Search by name "Mistral"
  await searchInput.fill('Mistral');
  assert.equal(await page.locator('.model-item').count(), 1);
  assert.match(await page.locator('.model-name').textContent(), /Mistral Large 2/);
  checks++;

  // Search by ID "openai"
  await searchInput.fill('openai');
  assert.equal(await page.locator('.model-item').count(), 1);
  assert.match(await page.locator('.model-id').textContent(), /openai\/gpt-4o/);
  checks++;

  // Search no matches
  await searchInput.fill('nonexistent-model-xyz');
  assert.equal(await page.locator('.model-item').count(), 0);
  assert.equal(await page.locator('#f016-editor-no-matches').isVisible(), true);
  checks++;

  // Clear search: check that previously allowed model (meta-llama/llama-3-8b) is still allowed
  await searchInput.fill('');
  assert.equal(await page.locator('.model-item').count(), 4);
  const llamaCheckbox = page.locator('#f016-editor-allow-0');
  assert.equal(
    await llamaCheckbox.isChecked(),
    true,
    'Clearing search preserves allowed selection',
  );
  checks++;

  // -------------------------------------------------------------
  // Bulk selection follows the filter and preserves selections outside it.
  const bulk = page.locator('#f016-editor-allow-all');
  assert.equal(await bulk.count(), 1, 'Table header must have a bulk checkbox');
  assert.equal(await bulk.evaluate((input) => input.indeterminate), true);
  await bulk.click();
  assert.equal(await bulk.isChecked(), true);
  assert.deepEqual(
    (await page.evaluate(() => window.__f016Harness.getProps())).allowedModelIds,
    ['meta-llama/llama-3-8b', 'openai/gpt-4o', 'mistralai/mistral-large-2407'],
    'Bulk selection must skip unavailable models',
  );
  await searchInput.fill('openai');
  await bulk.click();
  let bulkProps = await page.evaluate(() => window.__f016Harness.getProps());
  assert.deepEqual(bulkProps.allowedModelIds, [
    'meta-llama/llama-3-8b',
    'mistralai/mistral-large-2407',
  ]);
  assert.equal(bulkProps.defaultModelId, 'meta-llama/llama-3-8b');
  assert.equal(await bulk.isChecked(), false);
  await page.evaluate(() => window.__f016Harness.setAutoApply(false));
  await bulk.click();
  assert.equal(await bulk.isChecked(), false, 'Declined updates must restore header state');
  await page.evaluate(() => window.__f016Harness.setAutoApply(true));
  await searchInput.fill('llama');
  await bulk.click();
  bulkProps = await page.evaluate(() => window.__f016Harness.getProps());
  assert.equal(bulkProps.defaultModelId, null, 'Deselecting the default must clear it');
  await searchInput.fill('claude');
  assert.equal(await bulk.isDisabled(), true, 'Unavailable unselected results cannot be allowed');
  await searchInput.fill('nonexistent');
  assert.equal(await bulk.count(), 0);
  await searchInput.fill('');
  await page.evaluate(() =>
    window.__f016Harness.setProps({
      allowedModelIds: ['meta-llama/llama-3-8b'],
      defaultModelId: 'meta-llama/llama-3-8b',
    }),
  );
  checks++;

  // Test 5: Disabled prop locks all controls and blocks callbacks
  // -------------------------------------------------------------
  await page.evaluate(() => {
    window.__f016Harness.clearCallbacks();
    window.__f016Harness.setProps({ disabled: true });
  });

  assert.equal(await searchInput.isDisabled(), true);
  assert.equal(await bulk.isDisabled(), true);
  assert.equal(await llamaCheckbox.isDisabled(), true);
  const llamaRadio = page.locator('#f016-editor-default-0');
  assert.equal(await llamaRadio.isDisabled(), true);

  // Attempt click while disabled
  await llamaCheckbox.click({ force: true });
  callbacks = await page.evaluate(() => window.__f016Harness.getCallbacks());
  assert.equal(callbacks.length, 0, 'No callback should fire when component is disabled');
  checks++;

  // Re-enable
  await page.evaluate(() => {
    window.__f016Harness.setProps({ disabled: false });
  });
  assert.equal(await llamaCheckbox.isEnabled(), true);
  checks++;

  // -------------------------------------------------------------
  // Test 6: Keyboard navigation & Accessible labels
  // -------------------------------------------------------------
  // Focus search input, press Tab to move to allow checkbox, Space to toggle
  await searchInput.focus();
  await page.keyboard.press('Tab');
  assert.equal(await page.evaluate(() => document.activeElement.id), 'f016-editor-allow-all');
  await page.keyboard.press('Tab');
  assert.equal(
    await page.evaluate(() => document.activeElement.id),
    'f016-editor-allow-0',
    'Tab navigates through the header checkbox to first model checkbox',
  );

  // Press Space to uncheck llama
  await page.evaluate(() => window.__f016Harness.clearCallbacks());
  await page.keyboard.press('Space');
  callbacks = await page.evaluate(() => window.__f016Harness.getCallbacks());
  assert.equal(callbacks.length, 1);
  assert.deepEqual(callbacks[0].allowedModelIds, []);
  checks++;

  // Press Space again to re-check
  await page.keyboard.press('Space');
  callbacks = await page.evaluate(() => window.__f016Harness.getCallbacks());
  assert.equal(callbacks.length, 2);
  assert.deepEqual(callbacks[1].allowedModelIds, ['meta-llama/llama-3-8b']);
  checks++;

  // -------------------------------------------------------------
  // Test 7: Viewport 360px without horizontal overflow
  // -------------------------------------------------------------
  await page.setViewportSize({ width: 360, height: 640 });
  const mobileMetrics = await page
    .locator('.model-item')
    .first()
    .evaluate((row) => ({
      metaHeight: row.querySelector('.model-meta').getBoundingClientRect().height,
      controls: [...row.querySelectorAll('.control-option')].map(
        (control) => control.getBoundingClientRect().height,
      ),
    }));
  assert.ok(
    mobileMetrics.metaHeight < 150,
    'Short model metadata must not reserve 200px in a column',
  );
  assert.ok(
    mobileMetrics.controls.every((height) => height >= 44),
    'Control labels need a 44px hit area',
  );
  const hasHorizontalScroll = await page.evaluate(() => {
    const el = document.querySelector('.model-policy-editor');
    return el.scrollWidth > el.clientWidth;
  });
  assert.equal(hasHorizontalScroll, false, '360px viewport must not have horizontal overflow');
  checks++;

  // -------------------------------------------------------------
  // Test 8: Theme and Locales (vi-VN, en-US, ru-RU)
  // -------------------------------------------------------------
  // Light theme
  await page.evaluate(() => {
    document.querySelector('.workspace-shell').setAttribute('data-theme', 'light');
  });
  assert.equal(await page.locator('.workspace-shell').getAttribute('data-theme'), 'light');

  // Dark theme
  await page.evaluate(() => {
    document.querySelector('.workspace-shell').setAttribute('data-theme', 'dark');
  });
  assert.equal(await page.locator('.workspace-shell').getAttribute('data-theme'), 'dark');
  checks++;

  // Test en-US labels
  const enLabels = {
    heading: 'Model Policy',
    search: 'Search models',
    allow: 'Allow',
    defaultModel: 'Default',
    unavailable: 'Unavailable',
    empty: 'No models available',
    noMatches: 'No matching models',
    help: 'Configure allowed models for organization users.',
  };
  await page.evaluate((labels) => window.__f016Harness.setProps({ labels }), enLabels);
  assert.match(await page.locator('.editor-heading').textContent(), /Model Policy/);
  assert.match(await page.locator('.search-label').textContent(), /Search models/);
  checks++;

  // Test ru-RU labels
  const ruLabels = {
    heading: 'Политика моделей',
    search: 'Поиск моделей',
    allow: 'Разрешить',
    defaultModel: 'По умолчанию',
    unavailable: 'Недоступно',
    empty: 'Нет доступных моделей',
    noMatches: 'Совпадений не найдено',
    help: 'Настройка разрешенных моделей для организации.',
  };
  await page.evaluate((labels) => window.__f016Harness.setProps({ labels }), ruLabels);
  assert.match(await page.locator('.editor-heading').textContent(), /Политика моделей/);
  assert.match(await page.locator('.search-label').textContent(), /Поиск моделей/);
  checks++;

  // -------------------------------------------------------------
  // The full filtered catalog scrolls inside a bounded table with a sticky header.
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.evaluate(() =>
    window.__f016Harness.setProps({
      models: Array.from({ length: 60 }, (_, index) => ({
        id: `scroll/model-${index}`,
        name: `Model ${index}`,
        available: true,
      })),
      allowedModelIds: [],
      defaultModelId: null,
    }),
  );
  const scrolling = await page.locator('.models-container').evaluate((container) => {
    container.scrollTop = 160;
    const heading = container.querySelector('th');
    return {
      height: container.clientHeight,
      scrollHeight: container.scrollHeight,
      sticky: getComputedStyle(heading).position,
      top: heading.getBoundingClientRect().top - container.getBoundingClientRect().top,
    };
  });
  assert.equal(scrolling.height, 360);
  assert.ok(scrolling.scrollHeight > scrolling.height);
  assert.equal(scrolling.sticky, 'sticky');
  assert.ok(Math.abs(scrolling.top) <= 2);
  await bulk.click();
  assert.equal(
    (await page.evaluate(() => window.__f016Harness.getProps())).allowedModelIds.length,
    60,
    'Bulk selection includes rows outside the visible scroll area',
  );
  checks++;

  // Test 9: Zero browser console or page errors
  // -------------------------------------------------------------
  assert.deepEqual(pageErrors, [], `No page errors expected, got: ${pageErrors.join(', ')}`);
  assert.deepEqual(
    consoleErrors,
    [],
    `No console errors expected, got: ${consoleErrors.join(', ')}`,
  );
  checks++;

  console.log(`✔ All F016 browser interaction checks passed (${checks} checks verified)`);
} finally {
  if (browser) {
    await browser.close();
  }
  if (viteServer) {
    await viteServer.close();
  }
}
