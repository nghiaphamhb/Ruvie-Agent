import { showWorkspaceView, logoutFromMenu } from './workspace-actions.mjs';
/** Browser check against the built app and fake APIs; no dev database/provider is used.
 * Run after npm run build. RUVIE_PLAYWRIGHT_PATH/RUVIE_BROWSER_PATH may point to bundled tools.
 */
import assert from 'node:assert/strict';
import { runLocaleChecks } from './i18n-browser.mjs';
import { createServer } from 'node:http';
import { mkdir, readFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.RUVIE_PLAYWRIGHT_PATH || 'playwright');
const root = fileURLToPath(new URL('../dist/', import.meta.url));
let streamPlan = null;
const streamedTurns = [];
const streamConversation = {
  id: '00000000-0000-0000-0000-000000000019',
  title: 'Streaming history',
  version: 1,
};
let releaseDelta;
let releaseFinish;
const server = createServer(async (request, response) => {
  if (new URL(request.url, 'http://localhost').pathname === '/chat' && streamPlan) {
    let input = '';
    for await (const chunk of request) input += chunk;
    const posted = JSON.parse(input);
    const plan = streamPlan;
    const turn = {
      id: 'turn-' + (streamedTurns.length + 1),
      attempt_id: 'attempt-' + (streamedTurns.length + 1),
      question: posted.message,
      answer: '',
      citations: [],
      model_id: posted.model_id ?? 'a',
      status: 'generating',
      content_unavailable: false,
    };
    streamedTurns.push(turn);
    response.writeHead(200, { 'Content-Type': 'text/event-stream' });
    const frame = (event, data) => {
      if (event === 'delta') turn.answer += data.text;
      if (event === 'citations') turn.citations = data.citations;
      if (event === 'completed') turn.status = 'completed';
      if (event === 'error') {
        turn.status = 'error';
        turn.error_code = data.code;
      }
      if (!response.destroyed) response.write(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`);
    };
    frame('accepted', {
      conversation_id: streamConversation.id,
      turn_id: turn.id,
      attempt_id: turn.attempt_id,
    });
    frame('delta', { text: plan.initial });
    await new Promise((resolve) => {
      releaseDelta = resolve;
    });
    frame('delta', { text: plan.next });
    await new Promise((resolve) => {
      releaseFinish = resolve;
    });
    if (plan.error) {
      frame('citations', { citations: plan.citations });
      frame('error', { code: 'generation_failed' });
    } else {
      frame('citations', { citations: plan.citations });
      frame('completed', {});
    }
    response.end();
    return;
  }
  const target = path.resolve(
    root,
    '.' + new URL(request.url, 'http://localhost').pathname.replace(/\/$/, '/index.html'),
  );
  if (!target.startsWith(root)) {
    response.writeHead(403).end();
    return;
  }
  try {
    const content = await readFile(target);
    response.setHeader(
      'Content-Type',
      target.endsWith('.js')
        ? 'text/javascript'
        : target.endsWith('.css')
          ? 'text/css'
          : 'text/html',
    );
    response.end(content);
  } catch {
    response.writeHead(404).end();
  }
});
await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
const origin = `http://127.0.0.1:${server.address().port}`;
await mkdir(fileURLToPath(new URL('../../logs/', import.meta.url)), { recursive: true });
let browser;
let checks = 0;
async function runEnterChecks(browser) {
  const page = await browser.newPage({ locale: 'vi-VN' });
  let sent = 0;
  let connected = true;
  let holdChat = false;
  let releaseChat;
  const catalog = {
    models: [
      { id: 'one', name: 'One' },
      { id: 'two', name: 'Two' },
      ...Array.from({ length: 40 }, (_, index) => ({
        id: `provider/model-${index}`,
        name: `Provider: Model ${index}`,
      })),
    ],
    selected_model_id: 'one',
    selection_required: false,
  };
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.route('**/*', async (route) => {
    const api = new URL(route.request().url()).pathname;
    const json = (data) =>
      route.fulfill({ contentType: 'application/json', body: JSON.stringify(data) });
    if (api === '/auth/session')
      return json({
        user: { id: 'keyboard', system_role: 'admin', display_name: 'Keyboard' },
        csrf_token: 'csrf',
      });
    if (api === '/projects') return json({ items: [] });
    if (api === '/models') return json(catalog);
    if (api === '/llm/connection/model') {
      catalog.selected_model_id = route.request().postDataJSON().model_id;
      return json({ selected_model_id: catalog.selected_model_id });
    }
    if (api === '/llm/connection')
      return json({
        configured: connected,
        configuration_version: 1,
        selected_model_id: connected ? catalog.selected_model_id : null,
      });
    if (api === '/chat') {
      sent++;
      assert.equal(
        route.request().postDataJSON().model_id,
        catalog.selected_model_id,
        'chat uses the confirmed model',
      );
      if (holdChat)
        await new Promise((resolve) => {
          releaseChat = resolve;
        });
      return route.fulfill({
        contentType: 'text/event-stream',
        body: 'event: delta\ndata: {"text":"OK"}\n\nevent: completed\ndata: {}\n\n',
      });
    }
    return route.continue();
  });
  await page.goto(origin);
  const question = page.locator('#question');
  await page.getByText('One', { exact: true }).first().waitFor();
  const modelTrigger = page.locator('.workspace-toolbar [aria-haspopup="listbox"]');
  assert.equal(await modelTrigger.count(), 1, 'connected toolbar offers a model dropdown');
  await question.fill('Retain draft');
  await page.setViewportSize({ width: 1100, height: 360 });
  await modelTrigger.click();
  assert.equal(
    await page.getByRole('option', { name: 'One one', exact: true }).getAttribute('aria-selected'),
    'true',
  );
  const desktopMenu = page.locator('.menu:popover-open');
  assert.ok((await desktopMenu.boundingBox()).width <= 360, 'model dropdown is compact');
  const scrolling = await desktopMenu.evaluate(
    (element) =>
      [element, ...element.querySelectorAll('*')].filter(
        (node) =>
          ['auto', 'scroll'].includes(getComputedStyle(node).overflowY) &&
          node.scrollHeight > node.clientHeight + 1,
      ).length,
  );
  assert.equal(scrolling, 1, 'only the model list scrolls');
  const searchTop = await page
    .getByRole('combobox', { name: 'Tìm model', exact: true })
    .evaluate((element) => element.getBoundingClientRect().top);
  await desktopMenu.locator('.options').evaluate((element) => {
    element.scrollTop = element.scrollHeight;
  });
  assert.equal(
    await page
      .getByRole('combobox', { name: 'Tìm model', exact: true })
      .evaluate((element) => element.getBoundingClientRect().top),
    searchTop,
    'search stays fixed while models scroll',
  );
  await desktopMenu.locator('.options').evaluate((element) => {
    element.scrollTop = 0;
  });
  await page.screenshot({
    path: fileURLToPath(new URL('../../logs/model-picker-desktop.png', import.meta.url)),
  });
  await page.getByRole('option', { name: 'Two two', exact: true }).click();
  await page.waitForFunction(() =>
    document
      .querySelector('.workspace-toolbar [aria-haspopup="listbox"]')
      ?.textContent.includes('Two'),
  );
  assert.equal(await question.inputValue(), 'Retain draft', 'model change preserves draft');
  assert.equal(sent, 0, 'model change does not send chat');
  await modelTrigger.click();
  const search = page.getByRole('combobox', { name: 'Tìm model', exact: true });
  await search.fill('One');
  await search.press('ArrowDown');
  await search.press('Enter');
  await page.waitForFunction(() =>
    document
      .querySelector('.workspace-toolbar [aria-haspopup="listbox"]')
      ?.textContent.includes('One'),
  );
  await modelTrigger.click();
  const arrow = modelTrigger.locator('.chevron');
  await page.waitForFunction(
    () =>
      getComputedStyle(document.querySelector('.workspace-toolbar .chevron')).transform ===
      'matrix(-1, 0, 0, -1, 0, 0)',
  );
  assert.equal(await modelTrigger.getAttribute('aria-expanded'), 'true');
  await page.getByRole('combobox', { name: 'Tìm model', exact: true }).press('Escape');
  await page.waitForFunction(
    () =>
      getComputedStyle(document.querySelector('.workspace-toolbar .chevron')).transform ===
      'matrix(1, 0, 0, 1, 0, 0)',
  );
  await page.emulateMedia({ reducedMotion: 'reduce' });
  assert.ok(
    await arrow.evaluate(
      (element) => parseFloat(getComputedStyle(element).transitionDuration) <= 0.001,
    ),
    'reduced motion makes arrow change immediate',
  );
  await modelTrigger.click();
  await page.getByRole('combobox', { name: 'Tìm model', exact: true }).press('Escape');
  await page.emulateMedia({ reducedMotion: 'no-preference' });
  assert.equal(
    await modelTrigger.evaluate((e) => e === document.activeElement),
    true,
    'Escape returns focus',
  );
  assert.equal(
    await page.evaluate(() => {
      const ids = [...document.querySelectorAll('[id]')].map((e) => e.id);
      return new Set(ids).size === ids.length;
    }),
    true,
    'toolbar and Settings have unique IDs',
  );
  await question.fill('One line');
  await page.waitForFunction(() => !document.querySelector('.send-button')?.disabled);
  await question.press('Enter');
  await page.waitForFunction(() => document.querySelector('.answer')?.textContent.includes('OK'));
  assert.equal(sent, 1, 'one Enter sends a single-line question once');
  await question.fill('Tiếng Việt');
  await question.dispatchEvent('keydown', { key: 'Enter', isComposing: true });
  await question.dispatchEvent('compositionend');
  await question.dispatchEvent('keydown', { key: 'Enter', keyCode: 229 });
  assert.equal(await question.inputValue(), 'Tiếng Việt', 'IME confirmation retains draft');
  assert.equal(sent, 1, 'IME confirmation does not submit');
  // Dispatch in one browser task: no artificial 40ms wait after compositionend.
  await question.evaluate((element) => {
    element.dispatchEvent(new CompositionEvent('compositionend', { bubbles: true }));
    element.dispatchEvent(
      new KeyboardEvent('keydown', { key: 'Enter', bubbles: true, cancelable: true }),
    );
  });
  await page.waitForFunction(
    () =>
      document.querySelectorAll('.answer').length === 2 && !document.querySelector('.stop-button'),
  );
  assert.equal(await question.inputValue(), '', 'successful Enter clears the draft');
  assert.equal(sent, 2, 'committed text sends on the first Enter without a delay');
  await page.waitForFunction(() => !document.querySelector('.stop-button'));
  await question.fill('Line one');
  await question.press('Shift+Enter');
  assert.equal(await question.inputValue(), 'Line one\n', 'Shift+Enter inserts a newline');
  assert.equal(sent, 2, 'Shift+Enter never submits');
  holdChat = true;
  await question.fill('Busy check');
  await question.press('Enter');
  await page.locator('.stop-button').waitFor();
  assert.equal(await modelTrigger.isDisabled(), true, 'model changes are locked during chat');
  releaseChat();
  await page.waitForFunction(() => !document.querySelector('.stop-button'));
  connected = false;
  await page.reload();
  await page.locator('.chat-model-shortcut').click();
  await page.locator('#admin-settings-heading').waitFor();
  assert.equal(
    await page.locator('#admin-settings-tab-reply').getAttribute('aria-selected'),
    'true',
    'unconnected shortcut opens LLM settings',
  );
  assert.deepEqual(errors, []);
  await page.close();
  return 16;
}
try {
  browser = await chromium.launch({
    headless: true,
    executablePath: process.env.RUVIE_BROWSER_PATH || undefined,
  });
  checks += await runEnterChecks(browser);
  if (process.env.RUVIE_ENTER_ONLY) {
    console.log(`Toolbar/Enter browser: ${checks} checks passed`);
  } else {
    if (!process.env.RUVIE_CONNECTION_ONLY)
      checks += await runLocaleChecks(browser, origin, {
        plan(value) {
          streamPlan = value;
        },
        delta() {
          releaseDelta();
        },
        finish() {
          releaseFinish();
        },
        clear() {
          streamPlan = null;
        },
      });
    const context = await browser.newContext({
      locale: 'vi-VN',
      viewport: { width: 1366, height: 900 },
    });
    const page = await context.newPage();
    page.setDefaultTimeout(8000);
    const errors = [];
    page.on('pageerror', (error) => errors.push(error.message));
    streamedTurns.length = 0;
    let loggedIn = false,
      loginStatus = 401,
      expired = false,
      verifyStatus = 200,
      modelStatus = 200,
      selectionStatus = 200;
    let modelReads = 0,
      puts = 0,
      releaseLogin,
      releaseSelection,
      gateLogin = false,
      gateSelection = false;
    let signalLogin, signalSelection;
    const loginEntered = new Promise((resolve) => {
      signalLogin = resolve;
    });
    const selectionEntered = new Promise((resolve) => {
      signalSelection = resolve;
    });
    const writes = [];
    let org = {
      configured: true,
      base_url: 'https://server.test/v1',
      has_api_key: true,
      network: { mode: 'direct', proxy_url: null },
      allowed_model_ids: ['a', 'b'],
      default_model_id: 'a',
      version: 1,
      updated_at: null,
    };
    const catalog = {
      models: [
        { id: 'a', name: 'Model A' },
        { id: 'b', name: 'Model B' },
      ],
      selected_model_id: 'a',
      selection_required: false,
      configuration_version: 1,
    };
    await page.route('**/*', async (route) => {
      const req = route.request(),
        api = new URL(req.url()).pathname,
        method = req.method();
      const json = (value, status = 200) => route.fulfill({ status, json: value });
      const session = {
        user: { id: 'alpha', display_name: 'Alpha', system_role: 'admin' },
        csrf_token: 'csrf',
      };
      if (api === '/auth/setup') return json({ requires_initial_admin: false });
      if (api === '/auth/session') return json(loggedIn ? session : {}, loggedIn ? 200 : 401);
      if (api === '/auth/presence') return route.fulfill({ status: 204 });
      if (api === '/auth/login') {
        if (loginStatus !== 200) return json({ detail: 'private-login-marker' }, loginStatus);
        if (gateLogin)
          await new Promise((resolve) => {
            releaseLogin = resolve;
            signalLogin();
          });
        loggedIn = true;
        return json(session);
      }
      if (api === '/auth/logout') {
        loggedIn = false;
        return route.fulfill({ status: 204 });
      }
      if (api === '/projects') return json({ items: [] });
      if (api === '/admin/users/list')
        return json({ users: [], total: 0, page: 1, page_size: 20, presence: {} });
      if (api === '/conversations')
        return json({ items: streamedTurns.length ? [streamConversation] : [], next_cursor: null });
      if (api.startsWith('/conversations/'))
        return json({ conversation: streamConversation, turns: streamedTurns, next_cursor: null });
      if (api === '/models') {
        modelReads++;
        return json(catalog, modelStatus);
      }
      if (api === '/llm/connection') {
        assert.equal(method, 'GET', 'personal credential writes must never return');
        return json({
          configured: org.configured,
          configuration_version: org.version,
          selected_model_id: catalog.selected_model_id,
        });
      }
      if (api === '/llm/connection/model') {
        if (gateSelection)
          await new Promise((resolve) => {
            releaseSelection = resolve;
            signalSelection();
          });
        if (selectionStatus !== 200)
          return json({ detail: 'private-selection-marker' }, selectionStatus);
        catalog.selected_model_id = req.postDataJSON().model_id;
        return json({
          selected_model_id: catalog.selected_model_id,
          configuration_version: org.version,
        });
      }
      if (api.startsWith('/admin/llm/connection')) {
        if (expired) return json({ detail: { code: 'authentication_required' } }, 401);
        if (method === 'GET') return json(org);
        const body = req.postDataJSON();
        writes.push({ api, body });
        assert.equal(req.headers()['x-csrf-token'], 'csrf');
        if (api.endsWith('/verify'))
          return verifyStatus === 200
            ? json({ models: catalog.models, version: org.version })
            : json(
                { detail: { code: 'llm_provider_unavailable', message: 'private-verify-marker' } },
                verifyStatus,
              );
        if (api.endsWith('/probe'))
          return json({ success: true, model_id: body.model_id, version: org.version });
        assert.equal(method, 'PUT');
        assert.equal(body.expected_version, org.version);
        puts++;
        org = {
          ...org,
          base_url: body.base_url,
          network: body.network,
          has_api_key: body.key_action === 'keep' ? org.has_api_key : body.key_action === 'replace',
          allowed_model_ids: body.allowed_model_ids,
          default_model_id: body.default_model_id,
          version: org.version + 1,
        };
        return json(org);
      }
      return route.continue();
    });
    await page.goto(origin);
    await page.getByLabel('Email', { exact: true }).fill('alpha@test.com');
    await page.getByLabel('Mật khẩu', { exact: true }).fill('wrong');
    await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click();
    await page.locator('[data-sonner-toast][data-type="error"]').waitFor();
    assert.equal((await page.locator('body').innerText()).includes('private-login-marker'), false);
    checks++;
    loginStatus = 200;
    gateLogin = true;
    await page.getByLabel('Mật khẩu', { exact: true }).fill('test-password');
    await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click();
    await loginEntered;
    assert.equal(await page.getByLabel('Email', { exact: true }).isDisabled(), true);
    releaseLogin();
    await page.locator('.workspace-toolbar').getByText('Model A', { exact: true }).waitFor();
    checks++;
    const initialReads = modelReads;
    await page.locator('#question').fill('Retained draft');
    await showWorkspaceView(page, 'Kết nối LLM');
    const form = page.locator('[data-connection="reply"]');
    await form.locator('#llm-url').waitFor();
    assert.equal(await form.locator('#llm-url').inputValue(), org.base_url);
    assert.equal(await form.locator('#llm-key').count(), 0);
    checks++;
    await showWorkspaceView(page, 'Tải tài liệu');
    await showWorkspaceView(page, 'Chat');
    assert.equal(await page.locator('#question').inputValue(), 'Retained draft');
    assert.equal(modelReads, initialReads);
    checks++;
    await showWorkspaceView(page, 'Kết nối LLM');
    const action = async (kind) => {
      await form.locator('#llm-key-action').click();
      await page.locator('#llm-key-options [data-key-action="' + kind + '"]').click();
    };
    const verify = form.getByRole('button', { name: 'Kiểm tra kết nối', exact: true }),
      apply = form.getByRole('button', { name: 'Áp dụng cấu hình', exact: true });
    await action('replace');
    await form.locator('#llm-key').fill('replacement-secret');
    assert.equal(await form.locator('#llm-key').getAttribute('type'), 'password');
    await verify.click();
    await form.getByText('Model A', { exact: true }).first().waitFor();
    assert.equal(puts, 0);
    await apply.click();
    await page.locator('[data-sonner-toast]').filter({ hasText: 'Đã áp dụng' }).waitFor();
    assert.equal(puts, 1);
    assert.equal(writes.at(-1).body.key_action, 'replace');
    assert.equal(writes.at(-1).body.api_key, 'replacement-secret');
    assert.equal(await form.locator('#llm-key').count(), 0);
    checks++;
    await verify.click();
    await apply.click();
    await page.waitForFunction(
      () => !document.querySelector('[data-connection="reply"] fieldset')?.disabled,
    );
    assert.equal(puts, 2);
    assert.equal(writes.at(-1).body.key_action, 'keep');
    assert.equal('api_key' in writes.at(-1).body, false);
    checks++;
    await action('replace');
    await form.locator('#llm-key').fill('unsaved-secret');
    await showWorkspaceView(page, 'Chat');
    await showWorkspaceView(page, 'Kết nối LLM');
    assert.equal(await form.locator('#llm-key').count(), 0);
    checks++;
    verifyStatus = 502;
    await verify.click();
    await page
      .locator('[data-sonner-toast][data-type="error"]')
      .filter({ hasText: 'Không lấy được model.' })
      .waitFor();
    assert.equal((await page.locator('body').innerText()).includes('private-verify-marker'), false);
    verifyStatus = 200;
    checks++;
    await action('clear');
    await verify.click();
    await apply.click();
    await page.waitForFunction(
      () => !document.querySelector('[data-connection="reply"] fieldset')?.disabled,
    );
    assert.equal(org.has_api_key, false);
    assert.equal(writes.at(-1).body.key_action, 'clear');
    assert.equal('api_key' in writes.at(-1).body, false);
    checks++;
    await showWorkspaceView(page, 'Chat');
    const picker = page.getByRole('button', { name: 'Chọn model', exact: true });
    await picker.click();
    await page.getByRole('combobox', { name: 'Tìm model', exact: true }).fill('no-such-model');
    await page.getByText('Không có model phù hợp.', { exact: true }).waitFor();
    await page.getByRole('combobox', { name: 'Tìm model', exact: true }).fill('B');
    await page.keyboard.press('ArrowDown');
    await page.keyboard.press('Enter');
    await picker.getByText('Model B', { exact: true }).waitFor();
    assert.equal(await picker.evaluate((element) => element === document.activeElement), true);
    checks++;
    selectionStatus = 422;
    await picker.click();
    await page.getByRole('option', { name: /Model A/ }).click();
    await page.locator('.model-selector [role="alert"]').waitFor();
    assert.equal(catalog.selected_model_id, 'b');
    selectionStatus = 200;
    await page.keyboard.press('Escape');
    checks++;
    streamPlan = { initial: 'Partial answer', next: ' final', citations: [] };
    await page.locator('#question').fill('Question');
    await page.locator('.send-button').click();
    await page.getByText('Partial answer', { exact: true }).waitFor();
    assert.equal(await picker.isDisabled(), true);
    await showWorkspaceView(page, 'Kết nối LLM');
    await showWorkspaceView(page, 'Chat');
    releaseDelta();
    await page.getByText('Partial answer final', { exact: true }).waitFor();
    releaseFinish();
    await page.waitForFunction(() => !document.querySelector('.stop-button'));
    streamPlan = null;
    checks++;
    await page.reload();
    await page.getByText('Partial answer final', { exact: true }).waitFor();
    assert.equal(
      await page.locator('.turn').count(),
      1,
      'Reload hydrates committed server history',
    );
    checks++;
    gateSelection = true;
    await picker.click();
    await page.getByRole('option', { name: /Model A/ }).click();
    await selectionEntered;
    await logoutFromMenu(page);
    await page.getByRole('button', { name: 'Đăng nhập', exact: true }).waitFor();
    const selectionResponse = page.waitForResponse(
      (response) => new URL(response.url()).pathname === '/llm/connection/model',
    );
    releaseSelection();
    await (await selectionResponse).finished();
    assert.equal(await page.locator('.workspace-shell').count(), 0);
    checks++;
    loggedIn = true;
    gateSelection = false;
    await page.goto(origin + '/?view=admin-settings');
    await form.locator('#llm-url').waitFor();
    expired = true;
    await form.getByRole('button', { name: 'Tải lại', exact: true }).click();
    await page.getByRole('button', { name: 'Đăng nhập', exact: true }).waitFor();
    assert.deepEqual(errors, []);
    checks++;
    await context.close();
    console.log(
      `Browser: ${checks} checks passed (current organization credentials, verify/apply, locale, models, streaming history, logout/expiry).`,
    );
  }
} finally {
  releaseDelta?.();
  releaseFinish?.();
  await browser?.close();
  server.closeAllConnections();
  await new Promise((resolve) => server.close(resolve));
}
