import { showWorkspaceView, openAccountMenu, logoutFromMenu } from './workspace-actions.mjs';
/** Browser check against the built app and fake APIs; no dev database/provider is used.
 * Run after npm run build. RUVIE_PLAYWRIGHT_PATH/RUVIE_BROWSER_PATH may point to bundled tools.
 */
import assert from 'node:assert/strict';
import { runUploadChecks } from './upload-browser.mjs';
import { runLayoutChecks } from './layout-browser.mjs';
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
let releaseDelta;
let releaseFinish;
const server = createServer(async (request, response) => {
  if (new URL(request.url, 'http://localhost').pathname === '/chat' && streamPlan) {
    for await (const _chunk of request) {
      // Drain the POST body before sending the streaming response.
    } // Consume the active POST body before responding.
    const plan = streamPlan;
    response.writeHead(200, { 'Content-Type': 'text/event-stream' });
    const frame = (event, data) =>
      response.write(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`);
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
const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
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
        source: connected ? 'server' : 'none',
        base_url: connected ? 'https://example.test/v1' : null,
        has_api_key: connected,
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
    await page.locator('#admin-settings-tab-llm').getAttribute('aria-selected'),
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
    const page = await browser.newPage({ locale: 'vi-VN', viewport: { width: 1100, height: 900 } });
    const errors = [];
    page.on('pageerror', (error) => errors.push(error.message));
    let loggedIn = false;
    let loginStatus = 200;
    let slowLogin = false;
    let expired = false;
    let failSave = false;
    let slowSave = false;
    let slowChat = false;
    let slowModels = false;
    let delayedProjects = false;
    let failProjects = false;
    let selectionStatus = 200;
    let modelsStatus = 200;
    let chatStatus = 200;
    let slowSelection = false;
    const chatBodies = [];
    const bodies = [];
    let metadata = {
      source: 'server',
      base_url: 'https://server.test/v1',
      has_api_key: true,
      selected_model_id: 'a',
    };
    const catalog = {
      models: [
        { id: 'a', name: 'Model A' },
        { id: 'b', name: 'Model B' },
      ],
      selected_model_id: 'a',
      selection_required: false,
    };
    const citation = {
      citation_id: 'c1',
      document_id: 'doc1',
      revision_id: 'rev1',
      chunk_id: 'chunk1',
      ordinal: 2,
      start_offset: 10,
      end_offset: 30,
      title: '<script>Source</script>',
      source_hash: 'hash1',
      software: 'Ruvie',
      software_version: '1',
    };
    let modelReads = 0;
    await page.route('**/*', async (route) => {
      const req = route.request();
      const api = new URL(req.url()).pathname;
      const respond = (data, status = 200) =>
        route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(data) });
      if (api === '/auth/setup') return respond({ requires_initial_admin: false });
      if (api === '/auth/session')
        return respond(
          loggedIn
            ? {
                user: { id: 'alpha', system_role: 'admin', display_name: 'Alpha' },
                csrf_token: 'csrf',
              }
            : {},
          loggedIn ? 200 : 401,
        );
      if (api === '/auth/login') {
        if (loginStatus !== 200) return respond({ detail: 'unsafe-login-detail' }, loginStatus);
        if (slowLogin) await wait(500);
        loggedIn = true;
        expired = false;
        return respond({
          user: { id: 'alpha', system_role: 'admin', display_name: 'Alpha' },
          csrf_token: 'csrf',
        });
      }
      if (api === '/auth/logout') {
        loggedIn = false;
        return respond({});
      }
      // Keep login busy while the connection component mounts.
      if (api === '/projects') {
        if (failProjects) return respond({}, 503);
        const stale = delayedProjects;
        delayedProjects = false;
        await wait(stale ? 1000 : 250);
        return respond({
          items: stale ? [{ id: 'old', code: 'old', name: 'Private old project' }] : [],
        });
      }
      if (api === '/models') {
        modelReads++;
        if (slowModels) await wait(700);
        return respond(catalog, modelsStatus);
      }
      if (api === '/llm/connection/model') {
        if (slowSelection) await wait(500);
        if (selectionStatus !== 200) return respond({}, selectionStatus);
        const id = req.postDataJSON().model_id;
        catalog.selected_model_id = id;
        metadata.selected_model_id = id;
        return respond({ selected_model_id: id });
      }
      if (api === '/llm/connection') {
        if (expired) return respond({}, 401);
        if (req.method() === 'PUT') {
          bodies.push(req.postDataJSON());
          if (slowSave) await wait(500);
          if (failSave) return respond({ detail: 'private-key' }, 502);
          const body = req.postDataJSON();
          const same = metadata.source === 'personal' && metadata.base_url === body.base_url;
          metadata = {
            source: 'personal',
            base_url: body.base_url,
            has_api_key:
              body.api_key === undefined ? same && metadata.has_api_key : Boolean(body.api_key),
            selected_model_id: 'a',
          };
          return respond(catalog);
        }
        if (req.method() === 'DELETE') {
          metadata = {
            source: 'server',
            base_url: 'https://server.test/v1',
            has_api_key: true,
            selected_model_id: 'a',
          };
          return route.fulfill({ status: 204 });
        }
        return respond(metadata);
      }
      if (api === '/chat') {
        chatBodies.push(req.postDataJSON());
        if (chatStatus !== 200) return respond({}, chatStatus);
        if (streamPlan) return route.continue();
        if (slowChat) await wait(700);
        return route.fulfill({
          contentType: 'text/event-stream',
          body: `event: delta\ndata: {"text":"Answer"}\n\nevent: citations\ndata: ${JSON.stringify({ citations: [citation] })}\n\nevent: completed\ndata: {}\n\n`,
        });
      }
      return route.continue();
    });
    await page.goto(origin);
    async function login() {
      await page.getByLabel('Email', { exact: true }).fill('alpha@test.com');
      await page.getByLabel('Mật khẩu', { exact: true }).fill('test-password');
      await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click();
      await page
        .locator('.workspace-toolbar')
        .getByText('Model A', { exact: true })
        .waitFor({ timeout: 4000 });
    }
    loginStatus = 401;
    await page.getByLabel('Email', { exact: true }).fill('alpha@test.com');
    await page.getByLabel('Mật khẩu', { exact: true }).fill('wrong-password');
    await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click();
    await page
      .locator('[data-sonner-toast][data-type="error"]')
      .filter({ hasText: 'Email hoặc mật khẩu không đúng.' })
      .waitFor();
    assert.equal(
      (await page.locator('[data-sonner-toast][data-type="error"]').innerText()).includes(
        'unsafe-login-detail',
      ),
      false,
    );
    loginStatus = 200;
    slowLogin = true;
    await page.getByLabel('Mật khẩu', { exact: true }).fill('test-password');
    await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click();
    assert.equal(
      await page.getByLabel('Email', { exact: true }).isDisabled(),
      true,
      'login locks inputs while pending',
    );
    await page
      .locator('.selected-name:visible')
      .filter({ hasText: /^(Model: )?Model A$/ })
      .first()
      .waitFor();
    slowLogin = false;
    checks++;
    assert.ok(modelReads > 0, 'models must load even when login is still busy');
    // F007: rebuilding panels on navigation would lose draft/state and reload models.
    const navigation = page.getByRole('navigation', { name: 'Điều hướng chính' });
    assert.equal(await navigation.count(), 1, 'desktop has a persistent navigation sidebar');
    async function showView(name) {
      await showWorkspaceView(page, name);
    }
    assert.equal(
      await navigation
        .getByRole('button', { name: 'Chat mới', exact: true })
        .getAttribute('aria-current'),
      'page',
    );
    assert.equal(await page.getByLabel('Base URL', { exact: true }).isVisible(), false);
    await page.getByLabel('Câu hỏi của bạn', { exact: true }).fill('Keep draft');
    const readsBeforeNavigation = modelReads;
    await showView('Kết nối LLM');
    assert.equal(await page.getByLabel('Base URL', { exact: true }).isVisible(), true);
    assert.equal(
      await page.locator('#admin-settings-llm').isVisible(),
      true,
      'LLM settings use the admin page',
    );
    await showView('Tải tài liệu');
    await page
      .locator('.upload-panel')
      .getByText('Bạn chưa tham gia project nào.', { exact: true })
      .waitFor();
    await showView('Chat');
    assert.equal(
      await page.getByLabel('Câu hỏi của bạn', { exact: true }).inputValue(),
      'Keep draft',
    );
    assert.equal(modelReads, readsBeforeNavigation, 'navigation does not reload the catalog');
    assert.equal(
      await page
        .locator('.chat-welcome h1')
        .evaluate((element) => element === document.activeElement),
      true,
    );
    await page.getByLabel('Câu hỏi của bạn', { exact: true }).fill('');
    await openAccountMenu(page);
    await page.locator('.account-settings').focus();
    await page.keyboard.press('Space');
    await showView('Kết nối LLM');
    assert.equal(
      await page.getByLabel('Base URL', { exact: true }).isVisible(),
      true,
      'sidebar supports keyboard activation',
    );
    await showView('Chat');
    checks++;
    // Real incremental SSE from the local fixture server, with explicit release gates.
    streamPlan = {
      initial: Array.from({ length: 100 }, (_, i) => `Line ${i}\n`).join(''),
      next: 'Stream tail',
      citations: [citation],
    };
    await page.getByLabel('Câu hỏi của bạn', { exact: true }).fill('Stream with navigation');
    await page.getByRole('button', { name: 'Gửi câu hỏi', exact: true }).click();
    await page.getByText('Đang trả lời…', { exact: true }).waitFor();
    assert.equal(await page.locator('.sources').count(), 0, 'uncompleted streams have no sources');
    await page.locator('.conversation').evaluate((e) => {
      e.scrollTop = 0;
      e.dispatchEvent(new Event('scroll'));
    });
    await showView('Kết nối LLM');
    await showView('Chat');
    assert.equal(
      await page.locator('.conversation').evaluate((e) => e.scrollTop),
      0,
      'navigation preserves reading position',
    );
    releaseDelta();
    await page.getByText('Stream tail', { exact: false }).waitFor();
    assert.equal(
      await page.locator('.conversation').evaluate((e) => e.scrollTop),
      0,
      'delta does not move a reader at the top',
    );
    await page.locator('.conversation').evaluate((e) => {
      e.scrollTop = e.scrollHeight;
      e.dispatchEvent(new Event('scroll'));
    });
    await showView('Tải tài liệu');
    releaseFinish();
    await showView('Chat');
    await page.getByText('1 nguồn tham khảo', { exact: true }).waitFor();
    assert.ok(
      await page
        .locator('.conversation')
        .evaluate((e) => e.scrollHeight - e.scrollTop - e.clientHeight < 80),
      'returning from hidden panel follows output when already at the end',
    );
    await page.locator('.conversation').evaluate((e) => {
      e.scrollTop = 0;
      e.dispatchEvent(new Event('scroll'));
    });
    streamPlan = {
      initial: 'Partial answer',
      next: ' before error',
      citations: [citation],
      error: true,
    };
    await page.getByLabel('Câu hỏi của bạn', { exact: true }).fill('Stream failure');
    await page.getByRole('button', { name: 'Gửi câu hỏi', exact: true }).click();
    await page.getByText('Partial answer', { exact: true }).waitFor();
    assert.ok(
      await page
        .locator('.conversation')
        .evaluate((e) => e.scrollHeight - e.scrollTop - e.clientHeight < 80),
      'a new question follows its answer',
    );
    releaseDelta();
    await page.getByText('Partial answer before error', { exact: true }).waitFor();
    releaseFinish();
    await page.getByRole('alert').filter({ hasText: 'Không thể tạo câu trả lời' }).waitFor();
    assert.equal(
      await page.locator('.turn').last().locator('.sources').count(),
      0,
      'failed stream discards unconfirmed citations',
    );
    assert.equal(
      await page.getByText('Partial answer before error', { exact: true }).isVisible(),
      true,
      'failure keeps partial text',
    );
    streamPlan = null;
    await page.reload();
    await page
      .locator('.selected-name:visible')
      .filter({ hasText: /^(Model: )?Model A$/ })
      .first()
      .waitFor();
    checks++;

    const picker = page.getByRole('button', { name: 'Chọn model', exact: true });
    await picker.waitFor({ timeout: 2000 });
    await picker.click();
    const search = page.getByRole('combobox', { name: 'Tìm model', exact: true });
    await search.fill('no-such-model');
    await page.getByText('Không có model phù hợp.', { exact: true }).waitFor();
    await search.fill('B');
    await page.keyboard.press('ArrowDown');
    await page.keyboard.press('Enter');
    await page.waitForFunction(() =>
      document.querySelector('[aria-label="Chọn model"]').textContent.includes('Model B'),
    );
    assert.equal(await picker.evaluate((element) => element === document.activeElement), true);
    await picker.click();
    assert.equal(
      await page.getByRole('option', { name: /Model B/ }).getAttribute('aria-selected'),
      'true',
    );
    await page.keyboard.press('Escape');
    assert.equal(await picker.evaluate((element) => element === document.activeElement), true);
    await picker.click();
    await showView('Kết nối LLM');
    await page.waitForFunction(
      () =>
        document.querySelector('[aria-label="Chọn model"]')?.getAttribute('aria-expanded') ===
        'false',
      null,
      { polling: 50 },
    );
    assert.equal(
      await page.locator('[aria-label="Chọn model"]:visible').last().getAttribute('aria-expanded'),
      'false',
      'leaving Chat closes its popover',
    );
    assert.equal(await page.getByRole('listbox').count(), 0);
    await showView('Chat');
    await picker.click();
    await page.locator('.chat-welcome h1').click();
    assert.equal(await page.getByRole('listbox').count(), 0);
    checks++;
    await page.getByLabel('Câu hỏi của bạn', { exact: true }).fill('Use B');
    await page.getByRole('button', { name: 'Gửi câu hỏi', exact: true }).click();
    await page.getByText('Answer', { exact: true }).waitFor();
    assert.deepEqual(chatBodies.at(-1), { message: 'Use B', model_id: 'b' });
    const sources = page.getByText('1 nguồn tham khảo', { exact: true });
    assert.equal(
      await sources.evaluate((e) => getComputedStyle(e).borderRadius),
      '999px',
      'source-count control keeps the legacy pill shape',
    );
    await sources.focus();
    await page.keyboard.press('Enter');
    await page.getByText(citation.title, { exact: true }).waitFor();
    assert.equal(await page.locator('.sources li').count(), 1);
    await page.locator('.source-title').click();
    await page.locator('.source-dialog details summary').click();
    assert.equal(
      await page.locator('.source-dialog').getByText('c1', { exact: true }).count(),
      1,
      'citation identity is readable in technical details',
    );
    assert.equal(await page.locator('.source-number').innerText(), '1');
    for (const value of ['c1', 'doc1', 'rev1', 'chunk1 · #2', '10–30', 'hash1', 'Ruvie 1'])
      assert.ok((await page.locator('.source-dialog').innerText()).includes(value));
    assert.equal(
      await page.locator('.source-dialog script').count(),
      0,
      'citation title stays escaped',
    );
    await page.locator('.source-dialog').press('Escape');
    await sources.focus();
    await page.keyboard.press('Enter');
    assert.equal(await page.getByText(citation.title, { exact: true }).isVisible(), false);
    const question = page.getByLabel('Câu hỏi của bạn', { exact: true });
    const beforeIme = chatBodies.length;
    await question.fill('IME');
    await question.dispatchEvent('keydown', { key: 'Enter', isComposing: true });
    await question.dispatchEvent('compositionend');
    await question.dispatchEvent('keydown', { key: 'Enter', keyCode: 229 });
    assert.equal(chatBodies.length, beforeIme, 'IME confirmation never submits');
    await question.focus();
    await page.keyboard.press('Shift+Enter');
    assert.ok((await question.inputValue()).includes('\n'));
    await question.fill('Keyboard submit');
    await page.keyboard.press('Enter');
    await page.waitForFunction(
      () =>
        document.querySelector('#question').value === '' || document.querySelector('.stop-button'),
    );
    await page.getByText('Answer', { exact: true }).last().waitFor();
    assert.equal(chatBodies.length, beforeIme + 1, 'Enter submits once');
    checks++;

    await page.reload();
    await page
      .locator('.selected-name:visible')
      .filter({ hasText: /^(Model: )?Model B$/ })
      .first()
      .waitFor();
    assert.equal(await page.locator('.turn').count(), 0, 'reload clears in-page chat');
    assert.equal(
      await page.getByLabel('Câu hỏi của bạn', { exact: true }).inputValue(),
      '',
      'reload clears draft',
    );
    assert.equal(await page.evaluate(() => localStorage.length), 0);
    checks++;
    await picker.click();
    await page.getByRole('option', { name: /Model A/ }).click();
    await page
      .locator('.selected-name:visible')
      .filter({ hasText: /^(Model: )?Model A$/ })
      .first()
      .waitFor();
    selectionStatus = 502;
    await picker.click();
    await page.getByRole('option', { name: /Model B/ }).click();
    await page.getByRole('alert').filter({ hasText: 'Không lấy được model' }).waitFor();
    assert.ok((await picker.innerText()).includes('Model A'));
    selectionStatus = 200;
    slowSelection = true;
    await page.getByLabel('Câu hỏi của bạn', { exact: true }).fill('Pending selection');
    await picker.click();
    await page.getByRole('option', { name: /Model B/ }).click();
    const chatsBeforePendingSelection = chatBodies.length;
    await page.getByRole('button', { name: 'Gửi câu hỏi', exact: true }).click();
    assert.equal(
      chatBodies.length,
      chatsBeforePendingSelection,
      'pending selection cannot send chat',
    );
    await page
      .locator('.selected-name:visible')
      .filter({ hasText: /^(Model: )?Model B$/ })
      .first()
      .waitFor();
    slowSelection = false;
    await picker.click();
    await page.getByRole('option', { name: /Model A/ }).click();
    await page
      .locator('.selected-name:visible')
      .filter({ hasText: /^(Model: )?Model A$/ })
      .first()
      .waitFor();
    await page.getByLabel('Câu hỏi của bạn', { exact: true }).fill('');
    checks++;
    // Provider changes must block sending until a valid choice is confirmed.
    const originalModels = [...catalog.models];
    catalog.models = [{ id: 'b', name: 'Model B' }];
    catalog.selection_required = true;
    await showView('Kết nối LLM');
    await page.getByRole('button', { name: 'Tải lại model', exact: true }).click();
    await showView('Chat');
    await page
      .getByText('Model đã lưu không còn khả dụng. Hãy chọn lại model.', { exact: true })
      .first()
      .waitFor();
    await page.getByLabel('Câu hỏi của bạn', { exact: true }).fill('Blocked');
    const beforeInvalidModel = chatBodies.length;
    await page.getByRole('button', { name: 'Gửi câu hỏi', exact: true }).click();
    assert.equal(chatBodies.length, beforeInvalidModel);
    await picker.click();
    await page.getByRole('option', { name: /Model B/ }).click();
    await page
      .locator('.selected-name:visible')
      .filter({ hasText: /^(Model: )?Model B$/ })
      .first()
      .waitFor();
    catalog.models = originalModels;
    catalog.selection_required = false;
    catalog.selected_model_id = 'a';
    await showView('Kết nối LLM');
    await page.getByRole('button', { name: 'Tải lại model', exact: true }).click();
    await showView('Chat');
    await page
      .locator('.selected-name:visible')
      .filter({ hasText: /^(Model: )?Model A$/ })
      .first()
      .waitFor();
    modelsStatus = 502;
    await showView('Kết nối LLM');
    await page.getByRole('button', { name: 'Tải lại model', exact: true }).click();
    await page.getByRole('alert').filter({ hasText: 'Không lấy được model' }).waitFor();
    assert.equal(await picker.isDisabled(), true);
    modelsStatus = 200;
    await showView('Kết nối LLM');
    await page.getByRole('button', { name: 'Tải lại model', exact: true }).click();
    await showView('Chat');
    await page
      .locator('.selected-name:visible')
      .filter({ hasText: /^(Model: )?Model A$/ })
      .first()
      .waitFor();
    checks++;
    // A model can disappear after the UI loads. HTTP 422 reloads choices, not the chat.
    chatStatus = 422;
    catalog.models = [{ id: 'b', name: 'Model B' }];
    catalog.selection_required = true;
    const previousChats = chatBodies.length;
    await page.getByRole('button', { name: 'Gửi câu hỏi', exact: true }).click();
    await page
      .getByText('Model đã lưu không còn khả dụng. Hãy chọn lại model.', { exact: true })
      .first()
      .waitFor();
    assert.equal(chatBodies.length, previousChats + 1, 'no automatic chat retry');
    await page.getByLabel('Câu hỏi của bạn', { exact: true }).fill('Try again with missing model');
    await page.getByRole('button', { name: 'Gửi câu hỏi', exact: true }).click();
    assert.equal(chatBodies.length, previousChats + 1, 'invalid model blocks another send');
    chatStatus = 200;
    catalog.models = originalModels;
    catalog.selection_required = false;
    await showView('Kết nối LLM');
    await page.getByRole('button', { name: 'Tải lại model', exact: true }).click();
    await showView('Chat');
    await page
      .locator('.selected-name:visible')
      .filter({ hasText: /^(Model: )?Model A$/ })
      .first()
      .waitFor();
    checks++;
    await showView('Kết nối LLM');
    const url = page.getByLabel('Base URL', { exact: true });
    const key = page.getByLabel('API key (tùy chọn)', { exact: true });
    const connect = page.getByRole('button', { name: 'Kết nối', exact: true });
    await key.fill('temporary-key');
    await url.fill('https://personal.test/v1');
    assert.equal(await key.inputValue(), '', 'changing URL clears typed key');
    await connect.click();
    await page.getByText('Đã lưu kết nối.', { exact: true }).waitFor();
    assert.deepEqual(bodies.at(-1), { base_url: 'https://personal.test/v1' });
    checks++;
    await key.fill('personal-key');
    await connect.click();
    await page.getByText('Đã lưu key.', { exact: false }).waitFor();
    assert.equal(await key.inputValue(), '');
    await connect.click();
    await page.getByText('Đã lưu kết nối.', { exact: true }).waitFor();
    assert.equal(Object.hasOwn(bodies.at(-1), 'api_key'), false);
    await page.getByRole('button', { name: 'Xóa key đã lưu', exact: true }).click();
    await connect.click();
    await page.getByText('Chỉ nhập key', { exact: false }).waitFor();
    assert.equal(bodies.at(-1).api_key, '');
    checks++;
    await page.reload();
    await page
      .locator('.selected-name:visible')
      .filter({ hasText: /^(Model: )?Model A$/ })
      .first()
      .waitFor();
    await showView('Kết nối LLM');
    assert.equal(await url.inputValue(), 'https://personal.test/v1');
    assert.equal(await key.inputValue(), '');
    assert.equal(await page.evaluate(() => localStorage.length), 0);
    checks++;
    failSave = true;
    await url.fill('https://failed.test/v1');
    await connect.click();
    await page.getByRole('alert').filter({ hasText: 'Không lấy được model' }).waitFor();
    assert.equal(metadata.base_url, 'https://personal.test/v1');
    assert.ok(!(await page.getByRole('alert').innerText()).includes('private-key'));
    failSave = false;
    await url.fill('https://personal.test/v1');
    slowSave = true;
    const prior = bodies.length;
    await connect.click();
    assert.equal(await url.isDisabled(), true);
    assert.equal(await page.locator('button[aria-label="Gửi câu hỏi"]').isDisabled(), true);
    await page.getByText('Đã lưu kết nối.', { exact: true }).waitFor();
    assert.equal(bodies.length, prior + 1);
    slowSave = false;
    checks++;
    slowChat = true;
    await showView('Chat');
    await page.getByLabel('Câu hỏi của bạn', { exact: true }).fill('Question');
    await page.getByRole('button', { name: 'Gửi câu hỏi', exact: true }).click();
    await showView('Kết nối LLM');
    assert.equal(await url.isDisabled(), true);
    await showView('Tải tài liệu');
    await showView('Chat');
    await page.getByText('Answer', { exact: true }).waitFor();
    await showView('Kết nối LLM');
    await page.waitForFunction(() => !document.querySelector('#llm-url').disabled);
    await showView('Chat');
    checks++;
    await page.setViewportSize({ width: 1280, height: 720 });
    catalog.models = [
      ...originalModels,
      ...Array.from({ length: 25 }, (_, index) => ({
        id: `extra-${index}`,
        name: `Extra model ${index} with a long provider name`,
      })),
    ];
    await showView('Kết nối LLM');
    await page.getByRole('button', { name: 'Tải lại model', exact: true }).click();
    await showView('Chat');
    await page
      .locator('.selected-name:visible')
      .filter({ hasText: /^(Model: )?Model A$/ })
      .first()
      .waitFor();
    await picker.click();
    await search.fill('extra-');
    await page.waitForFunction(
      () =>
        document.querySelector('[role="listbox"]')?.querySelectorAll('[role="option"]').length ===
        25,
      null,
      { polling: 50 },
    );
    await page.keyboard.press('ArrowUp');
    await page.waitForFunction(() =>
      document
        .querySelector('[role="combobox"][aria-expanded="true"]')
        ?.getAttribute('aria-activedescendant')
        ?.endsWith('-option-24'),
    );
    await page.waitForFunction(
      () => document.querySelector('[role="listbox"]')?.scrollTop > 0,
      null,
      { polling: 50 },
    );
    assert.ok(
      await page.getByRole('listbox').evaluate((element) => element.scrollTop > 0),
      'keyboard scrolls long catalog',
    );
    const menuBounds = await page.locator('.menu:popover-open').boundingBox();
    assert.ok(
      menuBounds.x >= 0 &&
        menuBounds.x + menuBounds.width <= 1280 &&
        menuBounds.y >= 0 &&
        menuBounds.y + menuBounds.height <= 720,
    );
    await page.screenshot({
      path: fileURLToPath(new URL('../../logs/f007-selector-desktop.png', import.meta.url)),
      fullPage: true,
    });
    await page.keyboard.press('Escape');
    catalog.models = originalModels;
    await showView('Kết nối LLM');
    await page.screenshot({
      path: fileURLToPath(new URL('../../logs/f007-form-desktop.png', import.meta.url)),
      fullPage: true,
    });
    const overflow = await page.evaluate(() =>
      [...document.querySelectorAll('body *')]
        .filter((element) => element.getBoundingClientRect().right > innerWidth + 1)
        .map((element) => ({
          tag: element.tagName,
          class: element.className,
          right: element.getBoundingClientRect().right,
        })),
    );
    assert.deepEqual(overflow, [], 'no desktop horizontal overflow');
    await url.focus();
    await page.keyboard.press('Tab');
    assert.equal(await key.evaluate((element) => element === document.activeElement), true);
    await page.screenshot({
      path: fileURLToPath(new URL('../../logs/f007-form-desktop.png', import.meta.url)),
      fullPage: true,
    });
    checks++;
    await page.getByRole('button', { name: 'Gỡ kết nối', exact: true }).click();
    await page.getByText('Đã gỡ kết nối riêng.', { exact: true }).waitFor();
    assert.equal(await url.inputValue(), 'https://server.test/v1');
    assert.equal(await key.inputValue(), '');
    assert.equal(
      await page.getByRole('button', { name: 'Gỡ kết nối', exact: true }).isDisabled(),
      true,
    );
    checks++;
    slowModels = true;
    await page.getByRole('button', { name: 'Tải lại', exact: true }).click();
    await logoutFromMenu(page);
    await page.getByRole('heading', { name: 'Đăng nhập', exact: true }).waitFor();
    await wait(900);
    assert.equal(await page.getByRole('heading', { name: 'Kết nối LLM', exact: true }).count(), 0);
    slowModels = false;
    await login();
    // A pending project read must not restore account data after logout/login.
    failProjects = true;
    await page.reload();
    await page
      .locator('.selected-name:visible')
      .filter({ hasText: /^(Model: )?Model A$/ })
      .first()
      .waitFor();
    failProjects = false;
    delayedProjects = true;
    await showView('Tải tài liệu');
    await page.getByRole('button', { name: 'Thử lại', exact: true }).click();
    await logoutFromMenu(page);
    await page.getByRole('heading', { name: 'Đăng nhập', exact: true }).waitFor();
    await login();
    await wait(1200);
    await showView('Tải tài liệu');
    assert.equal(
      await page.getByRole('option', { name: 'Private old project', exact: false }).count(),
      0,
    );
    await page
      .locator('.upload-panel')
      .getByText('Bạn chưa tham gia project nào.', { exact: true })
      .waitFor();
    checks++;
    slowSelection = true;
    await showView('Chat');
    await picker.click();
    await page.getByRole('option', { name: /Model B/ }).click();
    await logoutFromMenu(page);
    await page.getByRole('heading', { name: 'Đăng nhập', exact: true }).waitFor();
    await wait(700);
    assert.equal(await picker.count(), 0, 'late PATCH cannot restore logged-out state');
    slowSelection = false;
    catalog.selected_model_id = 'a';
    metadata.selected_model_id = 'a';
    await login();
    checks++;
    expired = true;
    await showView('Kết nối LLM');
    await page.getByRole('button', { name: 'Tải lại', exact: true }).click();
    await page.getByRole('heading', { name: 'Đăng nhập', exact: true }).waitFor();
    checks++;
    checks += await runUploadChecks(browser, origin);
    checks += await runLayoutChecks(browser, origin);
    assert.deepEqual(errors, []);
    console.log(
      `Browser: ${checks} checks passed (loading, key semantics, reload, errors, locks, desktop navigation/keyboard, logout/expiry).`,
    );
  }
} finally {
  releaseDelta?.();
  releaseFinish?.();
  await browser?.close();
  server.closeAllConnections();
  await new Promise((resolve) => server.close(resolve));
}
