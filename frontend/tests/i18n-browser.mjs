import { showWorkspaceView, openSettings, logoutFromMenu } from './workspace-actions.mjs';
/** Locale browser checks use fake APIs, never live credentials or the development DB. */
import { fileURLToPath } from 'node:url';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
const catalogs = Object.fromEntries(
  await Promise.all(
    ['vi-VN', 'en-US', 'ru-RU'].map(async (locale) => [
      locale,
      JSON.parse(
        await readFile(
          new URL(`../src/lib/i18n/locales/${locale}/translation.json`, import.meta.url),
          'utf8',
        ),
      ),
    ]),
  ),
);
const models = {
  models: [
    { id: 'a', name: 'Original model <b>A</b>' },
    { id: 'b', name: 'Original model B' },
  ],
  selected_model_id: 'a',
  selection_required: false,
};
const citation = {
  citation_id: 'd:r:c',
  document_id: 'd',
  revision_id: 'r',
  chunk_id: 'c',
  ordinal: 0,
  start_offset: 0,
  end_offset: 12,
  title: 'Original title <b>text</b>',
  source_hash: 'abc123',
  software: 'Revit',
  software_version: '2026',
};
async function fixture(browser, origin, options = {}) {
  const context = await browser.newContext({
    locale: options.browserLocale ?? 'vi-VN',
    viewport: options.viewport ?? { width: 1280, height: 720 },
    deviceScaleFactor: options.scale ?? 1,
  });
  if (options.saved)
    await context.addInitScript((value) => {
      if (!sessionStorage.getItem('locale-seeded')) {
        localStorage.setItem('ruvie.ui.locale', value);
        sessionStorage.setItem('locale-seeded', '1');
      }
    }, options.saved);
  if (options.blocked)
    await context.addInitScript(() => {
      Object.defineProperty(Storage.prototype, 'getItem', {
        value() {
          throw new Error('blocked');
        },
      });
      Object.defineProperty(Storage.prototype, 'setItem', {
        value() {
          throw new Error('blocked');
        },
      });
    });
  const page = await context.newPage();
  const requests = [];
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  const state = {
    loggedIn: options.loggedIn ?? false,
    loginStatus: 200,
    llmStatus: 200,
    configured: true,
    configuration_version: 1,
    ready: false,
    uploadGate: null,
    loginGate: null,
    llmGate: null,
    modelGate: null,
    modelStatus: 200,
    documentStatus: 200,
    loginNetwork: false,
  };
  await page.route('**/*', async (route) => {
    const request = route.request();
    const api = new URL(request.url()).pathname;
    if (!/^\/(auth|admin|projects|models|llm|documents|chat)(\/|$)/.test(api)) {
      await route.continue();
      return;
    }
    requests.push({ api, method: request.method(), body: request.postData() });
    const json = (data) =>
      route.fulfill({ contentType: 'application/json', body: JSON.stringify(data) });
    if (api === '/auth/setup') return json({ requires_initial_admin: false });
    if (api === '/auth/session')
      return state.loggedIn
        ? json({
            user: { id: 'locale', system_role: 'admin', display_name: 'Original account' },
            csrf_token: 'csrf',
          })
        : route.fulfill({ status: 401 });
    if (api === '/auth/login') {
      if (state.loginNetwork) return route.abort('failed');
      if (state.loginGate) await state.loginGate;
      if (state.loginStatus !== 200) return route.fulfill({ status: state.loginStatus });
      state.loggedIn = true;
      return json({
        user: { id: 'locale', system_role: 'admin', display_name: 'Original account' },
        csrf_token: 'csrf',
      });
    }
    if (api === '/auth/logout') {
      state.loggedIn = false;
      return route.fulfill({ status: 204 });
    }
    if (api === '/projects')
      return json({ items: [{ id: 'p', code: 'P', name: 'Original project' }] });
    if (api === '/models') return json(models);
    if (api === '/llm/connection' && request.method() === 'PUT') {
      if (state.llmGate) await state.llmGate;
      if (state.llmStatus !== 200)
        return route.fulfill({
          status: state.llmStatus,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'secret-never-display' }),
        });
      state.source = 'personal';
      return json(models);
    }
    if (api === '/llm/connection' && request.method() === 'DELETE') {
      state.source = 'server';
      return route.fulfill({ status: 204 });
    }
    if (api === '/llm/connection')
      return json({
        source: state.source,
        base_url: 'https://example.test/v1',
        has_api_key: true,
        selected_model_id: 'a',
      });
    if (api === '/llm/connection/model') {
      if (state.modelGate) await state.modelGate;
      if (state.modelStatus !== 200) return route.fulfill({ status: state.modelStatus });
      return json({ selected_model_id: JSON.parse(request.postData()).model_id });
    }
    if (api === '/documents/upload') {
      if (state.uploadGate) await state.uploadGate;
      if (state.documentStatus !== 200) return route.fulfill({ status: state.documentStatus });
      return json({ document_id: 'd', revision_id: 'r', job_id: 'j', status: 'pending' });
    }
    if (api === '/documents/revisions/r/status')
      return json({
        revision_id: 'r',
        status: state.ready ? 'ready' : 'pending',
        error_code: null,
      });
    if (api === '/chat') return route.continue();
    return route.fulfill({ status: 404 });
  });
  await page.goto(origin);
  const select = page.locator('.language-selector select');
  await select.waitFor({ state: 'attached' });
  assert.equal(await select.count(), 1, 'A single operable language selector must exist');
  return { context, page, select, state, requests, errors };
}
async function choose(f, locale) {
  const workspace = (await f.page.locator('.workspace-shell').count()) > 0;
  const previous = f.page.url();
  if (workspace) await openSettings(f.page, 'appearance');
  await f.select.focus();
  await f.select.selectOption(locale);
  await f.page.waitForFunction((value) => document.documentElement.lang === value, locale);
  assert.equal(await f.select.inputValue(), locale);
  assert.equal(
    await f.select.evaluate((element) => document.activeElement === element),
    true,
    'locale keeps focus while choosing',
  );
  if (workspace && f.page.url() !== previous) await f.page.goBack();
}
async function signIn(f, locale = 'vi-VN') {
  const t = catalogs[locale];
  await f.page.getByLabel(t['auth.email'], { exact: true }).fill('user@example.test');
  await f.page.getByLabel(t['auth.password'], { exact: true }).fill('dummy-password');
  await f.page.getByRole('button', { name: t['auth.login'], exact: true }).click();
  await f.page.getByRole('navigation').waitFor();
  await f.page.getByRole('button', { name: t['model.choose'], exact: true }).waitFor();
}
export async function runLocaleChecks(browser, origin, streamHooks) {
  let checks = 0;
  for (const locale of ['vi-VN', 'en-US', 'ru-RU']) {
    const f = await fixture(browser, origin, { saved: locale, browserLocale: 'en-US' });
    const t = catalogs[locale];
    try {
      assert.equal(await f.page.locator('html').getAttribute('lang'), locale);
      assert.equal(await f.page.title(), t['page.title']);
      assert.equal(
        await f.page.locator('meta[name="description"]').getAttribute('content'),
        t['page.description'],
      );
      assert.deepEqual(await f.select.locator('option').allTextContents(), [
        'Tiếng Việt',
        'English',
        'Русский',
      ]);
      await signIn(f, locale);
      await f.page.getByLabel(t['chat.question'], { exact: true }).fill('Original draft');
      await showWorkspaceView(f.page, t['nav.documents']);
      await f.page.getByLabel(t['upload.project'], { exact: true }).selectOption('p');
      await f.page.getByLabel(t['upload.title'], { exact: true }).fill('Original document');
      await f.page.getByLabel(t['upload.software'], { exact: true }).fill('Original software');
      await f.page.getByLabel(t['upload.version'], { exact: true }).fill('2026');
      await f.page.getByLabel(t['upload.file'], { exact: true }).setInputFiles({
        name: 'Original.txt',
        mimeType: 'text/plain',
        buffer: Buffer.from('Original content'),
      });
      await openSettings(f.page, 'llm');
      await f.page.locator('#llm-key').fill('dummy-key');
      const before = f.requests.filter(
        ({ api }) => api !== '/auth/session' && !api.startsWith('/admin/'),
      ).length;
      const next = locale === 'ru-RU' ? 'en-US' : 'ru-RU';
      await choose(f, next);
      const n = catalogs[next];
      assert.equal(
        f.requests.filter(({ api }) => api !== '/auth/session' && !api.startsWith('/admin/'))
          .length,
        before,
        'locale navigation does not reload business data',
      );
      assert.equal(await f.page.locator('#llm-key').inputValue(), 'dummy-key');
      assert.equal(await f.page.evaluate(() => localStorage.getItem('ruvie.ui.locale')), next);
      assert.equal(await f.page.locator('#question').inputValue(), 'Original draft');
      await showWorkspaceView(f.page, n['nav.documents']);
      assert.equal(
        await f.page.getByLabel(n['upload.title'], { exact: true }).inputValue(),
        'Original document',
      );
      assert.equal(
        await f.page
          .getByLabel(n['upload.file'], { exact: true })
          .evaluate((input) => input.files[0].name),
        'Original.txt',
      );
      await choose(f, locale);
      await f.page.reload();
      await f.page.getByRole('navigation').waitFor();
      assert.equal(await f.select.inputValue(), locale);
      await logoutFromMenu(f.page);
      await f.page.getByRole('button', { name: t['auth.login'], exact: true }).waitFor();
      assert.equal(await f.select.inputValue(), locale);
      assert.deepEqual(f.errors, []);
      checks++;
    } finally {
      await f.context.close();
    }
  }
  // Native selector is the first login Tab stop and supports keyboard choices.
  const keyboard = await fixture(browser, origin);
  try {
    await keyboard.page.keyboard.press('Tab');
    assert.equal(await keyboard.select.evaluate((el) => document.activeElement === el), true);
    // Customizable native select opens first; Enter commits the highlighted option.
    await keyboard.page.keyboard.press('ArrowDown');
    await keyboard.page.keyboard.press('ArrowDown');
    await keyboard.page.keyboard.press('Enter');
    await keyboard.page.waitForFunction(() => document.documentElement.lang === 'en-US');
    await keyboard.page.keyboard.press('ArrowDown');
    await keyboard.page.keyboard.press('ArrowDown');
    await keyboard.page.keyboard.press('Enter');
    await keyboard.page.waitForFunction(() => document.documentElement.lang === 'ru-RU');
    await keyboard.page.keyboard.press('ArrowUp');
    await keyboard.page.keyboard.press('Home');
    await keyboard.page.keyboard.press('Enter');
    await keyboard.page.waitForFunction(() => document.documentElement.lang === 'vi-VN');
    assert.deepEqual(keyboard.errors, []);
    checks++;
  } finally {
    await keyboard.context.close();
  }
  // Browser detection and blocked storage are tested in fresh independent contexts.
  for (const [options, expected] of [
    [{ browserLocale: 'en-GB' }, 'en-US'],
    [{ browserLocale: 'ru-RU', saved: 'forged' }, 'ru-RU'],
    [{ browserLocale: 'fr-FR' }, 'vi-VN'],
    [{ browserLocale: 'en-US', blocked: true }, 'en-US'],
  ]) {
    const f = await fixture(browser, origin, options);
    try {
      assert.equal(await f.select.inputValue(), expected);
      await choose(f, 'ru-RU');
      assert.deepEqual(f.errors, []);
      checks++;
    } finally {
      await f.context.close();
    }
  }
  const f = await fixture(browser, origin);
  try {
    await f.page.getByLabel('Email', { exact: true }).fill('user@example.test');
    await f.page.getByLabel('Mật khẩu', { exact: true }).fill('dummy-password');
    f.state.loginStatus = 401;
    await f.page.getByRole('button', { name: 'Đăng nhập', exact: true }).click();
    await f.page.locator('[data-sonner-toast][data-type="error"] [data-title]').waitFor();
    await choose(f, 'ru-RU');
    assert.equal(
      await f.page.locator('[data-sonner-toast][data-type="error"] [data-title]').innerText(),
      catalogs['ru-RU']['auth.errors.credentials'],
    );
    assert.equal(await f.page.getByLabel('Пароль', { exact: true }).inputValue(), 'dummy-password');
    f.state.loginStatus = 200;
    await f.page.getByRole('button', { name: 'Войти', exact: true }).click();
    await f.page.getByRole('navigation').waitFor();
    await choose(f, 'vi-VN');
    await openSettings(f.page, 'llm');
    await f.page.locator('#llm-key').fill('dummy-key');
    f.state.llmStatus = 502;
    await f.page.getByRole('button', { name: 'Kết nối', exact: true }).click();
    await f.page.locator('.llm-panel [role=alert]').waitFor();
    const before = f.requests.filter(
      ({ api }) => api !== '/auth/session' && !api.startsWith('/admin/'),
    ).length;
    await choose(f, 'ru-RU');
    assert.equal(
      await f.page.locator('.llm-panel [role=alert]').innerText(),
      catalogs['ru-RU']['llm.errors.providerUnavailable'],
    );
    assert.equal(
      f.requests.filter(({ api }) => api !== '/auth/session' && !api.startsWith('/admin/')).length,
      before,
    );
    assert.ok(!(await f.page.locator('body').innerText()).includes('secret-never-display'));
    checks++;
    f.state.llmStatus = 200;
    await f.page
      .getByRole('button', { name: catalogs['ru-RU']['llm.connect'], exact: true })
      .click();
    await f.page.getByText(catalogs['ru-RU']['llm.saved'], { exact: true }).waitFor();
    await choose(f, 'en-US');
    await f.page.getByText('Connection saved.', { exact: true }).waitFor();
    checks++;
    await showWorkspaceView(f.page, 'Chat');
    streamHooks.plan({
      initial: 'Original <b>partial</b>',
      next: ' original final',
      citations: [citation],
    });
    await f.page.getByLabel('Your question', { exact: true }).fill('Original question');
    await f.page.getByRole('button', { name: 'Send question', exact: true }).click();
    await f.page.locator('.answer').filter({ hasText: 'Original <b>partial</b>' }).waitFor();
    const sent = f.requests.filter((request) => request.api === '/chat').length;
    await choose(f, 'ru-RU');
    assert.equal(f.requests.filter((request) => request.api === '/chat').length, sent);
    streamHooks.delta();
    await f.page.locator('.answer').filter({ hasText: 'original final' }).waitFor();
    streamHooks.finish();
    await f.page.getByText('1 источник', { exact: true }).waitFor();
    assert.equal(await f.page.locator('.answer b').count(), 0);
    await f.page.getByText('1 источник', { exact: true }).click();
    assert.equal(await f.page.locator('.source-title').innerText(), citation.title);
    checks++;
    streamHooks.plan({ initial: 'Second partial', next: ' final', error: true, citations: [] });
    await f.page.getByLabel('Ваш вопрос', { exact: true }).fill('Error question');
    await f.page.getByRole('button', { name: 'Отправить вопрос', exact: true }).click();
    await f.page.locator('.answer').filter({ hasText: 'Second partial' }).waitFor();
    streamHooks.delta();
    await f.page.locator('.answer').filter({ hasText: 'Second partial final' }).waitFor();
    streamHooks.finish();
    await f.page.locator('.response-error').waitFor();
    await choose(f, 'en-US');
    assert.equal(
      await f.page.locator('.response-error').innerText(),
      catalogs['en-US']['chat.errors.generation_failed'],
    );
    assert.equal(await f.page.locator('.sources').getAttribute('open'), '');
    await f.page.getByText('1 source', { exact: true }).waitFor();
    checks++;
    await showWorkspaceView(f.page, 'Upload documents');
    await f.page.getByLabel('Project', { exact: true }).selectOption('p');
    await f.page.getByLabel('Document title', { exact: true }).fill('Doc');
    await f.page.getByLabel('Software', { exact: true }).fill('App');
    await f.page.getByLabel('Version', { exact: true }).fill('1');
    await f.page
      .getByLabel('File', { exact: true })
      .setInputFiles({ name: 'Doc.txt', mimeType: 'text/plain', buffer: Buffer.from('Text') });
    let releaseUpload;
    f.state.uploadGate = new Promise((resolve) => {
      releaseUpload = resolve;
    });
    await f.page.getByRole('button', { name: 'Upload', exact: true }).click();
    await f.page.getByRole('button', { name: 'Uploading…', exact: true }).waitFor();
    await choose(f, 'ru-RU');
    assert.equal(f.requests.filter((request) => request.api === '/documents/upload').length, 1);
    releaseUpload();
    await f.page.getByText('Ожидает обработки', { exact: true }).waitFor();
    await choose(f, 'en-US');
    f.state.ready = true;
    await f.page.getByText('Ready', { exact: true }).waitFor();
    assert.equal(f.requests.filter((request) => request.api === '/documents/upload').length, 1);
    checks++;
    for (const request of f.requests) {
      if (request.api === '/chat' || (request.api.startsWith('/llm') && request.body)) {
        const body = JSON.parse(request.body);
        assert.ok(!('locale' in body));
      }
    }
    assert.deepEqual(f.errors, []);
  } finally {
    streamHooks.clear();
    await f.context.close();
  }
  // Delayed operations retain ownership while locale changes, including login and model save.
  const delayed = await fixture(browser, origin);
  try {
    let releaseLogin;
    delayed.state.loginGate = new Promise((resolve) => {
      releaseLogin = resolve;
    });
    await delayed.page.getByLabel('Email', { exact: true }).fill('user@example.test');
    await delayed.page.getByLabel('Mật khẩu', { exact: true }).fill('dummy-password');
    await delayed.page.getByRole('button', { name: 'Đăng nhập', exact: true }).click();
    await delayed.page.getByRole('button', { name: 'Đang đăng nhập…', exact: true }).waitFor();
    await choose(delayed, 'en-US');
    assert.equal(delayed.requests.filter((r) => r.api === '/auth/login').length, 1);
    releaseLogin();
    await delayed.page.getByRole('navigation').waitFor();
    await delayed.page.getByRole('button', { name: 'Choose a model', exact: true }).waitFor();
    await delayed.page
      .locator('.model-selector')
      .getByRole('button', { name: 'Choose a model', exact: true })
      .click();
    await delayed.page
      .getByRole('combobox', { name: 'Search models', exact: true })
      .fill('Original');
    const beforeSearch = delayed.requests.length;
    await choose(delayed, 'ru-RU');
    assert.equal(delayed.requests.length, beforeSearch);
    await delayed.page
      .locator('.model-selector')
      .getByRole('button', { name: 'Выбрать модель', exact: true })
      .click();
    // Settings dismisses the model popover; reopening starts a fresh search.
    assert.equal(await delayed.page.locator('#chat-model-search').inputValue(), '');
    await delayed.page
      .getByRole('combobox', { name: 'Поиск моделей', exact: true })
      .fill('Original');
    await delayed.page.getByRole('option').first().waitFor();
    assert.equal(await delayed.page.getByRole('option').count(), 2);
    let releaseModel;
    delayed.state.modelGate = new Promise((resolve) => {
      releaseModel = resolve;
    });
    await delayed.page.getByRole('option', { name: 'Original model B b', exact: true }).click();
    await delayed.page
      .locator('.workspace-toolbar')
      .getByText('Проверка моделей…', { exact: true })
      .waitFor();
    await choose(delayed, 'en-US');
    releaseModel();
    await delayed.page
      .locator('.workspace-toolbar')
      .getByText('Original model B', { exact: true })
      .waitFor();
    assert.equal(delayed.requests.filter((r) => r.api === '/llm/connection/model').length, 1);
    await showWorkspaceView(delayed.page, 'LLM connection');
    let releaseConnection;
    delayed.state.llmGate = new Promise((resolve) => {
      releaseConnection = resolve;
    });
    await delayed.page.locator('#llm-key').fill('dummy-key');
    await delayed.page.getByRole('button', { name: 'Connect', exact: true }).click();
    await delayed.page.getByText('Checking connection…', { exact: true }).waitFor();
    await choose(delayed, 'ru-RU');
    releaseConnection();
    await delayed.page.getByText(catalogs['ru-RU']['llm.saved'], { exact: true }).waitFor();
    assert.equal(
      delayed.requests.filter((r) => r.api === '/llm/connection' && r.method === 'PUT').length,
      1,
    );
    assert.deepEqual(delayed.errors, []);
    checks++;
  } finally {
    await delayed.context.close();
  }
  // Each error family renders in all supported locales; external details remain suppressed.
  for (const locale of ['vi-VN', 'en-US', 'ru-RU']) {
    const failure = await fixture(browser, origin, { saved: locale });
    const t = catalogs[locale];
    try {
      failure.state.loginNetwork = true;
      await failure.page.getByLabel(t['auth.email'], { exact: true }).fill('user@example.test');
      await failure.page.getByLabel(t['auth.password'], { exact: true }).fill('dummy-password');
      await failure.page.getByRole('button', { name: t['auth.login'], exact: true }).click();
      await failure.page.getByText(t['common.errors.network'], { exact: true }).waitFor();
      failure.state.loginNetwork = false;
      await signIn(failure, locale);
      await openSettings(failure.page, 'llm');
      for (const [status, key] of [
        [403, 'llm.errors.csrf'],
        [422, 'llm.errors.invalid'],
        [502, 'llm.errors.providerUnavailable'],
        [503, 'llm.errors.settings'],
      ]) {
        failure.state.llmStatus = status;
        await failure.page.getByRole('button', { name: t['llm.connect'], exact: true }).click();
        await failure.page.getByText(t[key], { exact: true }).waitFor();
      }
      await showWorkspaceView(failure.page, t['nav.documents']);
      await failure.page.getByLabel(t['upload.project'], { exact: true }).selectOption('p');
      await failure.page.getByLabel(t['upload.title'], { exact: true }).fill('Doc');
      await failure.page.getByLabel(t['upload.software'], { exact: true }).fill('App');
      await failure.page.getByLabel(t['upload.version'], { exact: true }).fill('1');
      await failure.page
        .getByLabel(t['upload.file'], { exact: true })
        .setInputFiles({ name: 'Doc.txt', mimeType: 'text/plain', buffer: Buffer.from('Text') });
      failure.state.documentStatus = 404;
      await failure.page.getByRole('button', { name: t['upload.submit'], exact: true }).click();
      await failure.page.getByText(t['upload.errors.notFound'], { exact: true }).waitFor();
      const next = locale === 'ru-RU' ? 'en-US' : 'ru-RU';
      const before = failure.requests.length;
      await choose(failure, next);
      await failure.page
        .getByText(catalogs[next]['upload.errors.notFound'], { exact: true })
        .waitFor();
      assert.equal(failure.requests.length, before);
      await showWorkspaceView(failure.page, catalogs[next]['nav.chat']);
      failure.state.modelStatus = 422;
      await failure.page
        .getByRole('button', { name: catalogs[next]['model.choose'], exact: true })
        .click();
      await failure.page.getByRole('option', { name: 'Original model B b', exact: true }).click();
      await failure.page.locator('.workspace-toolbar .model-selector [role=alert]').waitFor();
      await choose(failure, locale);
      assert.equal(
        await failure.page.locator('.workspace-toolbar .model-selector [role=alert]').innerText(),
        t['llm.errors.invalid'],
      );
      await failure.page.locator('#chat-model-menu').evaluate((menu) => menu.hidePopover());
      await openSettings(failure.page, 'llm');
      failure.state.llmStatus = 401;
      await failure.page.getByRole('button', { name: t['llm.connect'], exact: true }).click();
      await failure.page.getByRole('button', { name: t['auth.login'], exact: true }).waitFor();
      assert.equal(await failure.select.inputValue(), locale);
      assert.deepEqual(failure.errors, []);
      checks++;
    } finally {
      await failure.context.close();
    }
  }
  for (const locale of ['vi-VN', 'en-US', 'ru-RU'])
    for (const size of [
      { width: 1280, height: 720, scale: 1 },
      { width: 1024, height: 600, scale: 1 },
      { width: 640, height: 360, scale: 2 },
    ]) {
      const f = await fixture(browser, origin, {
        saved: locale,
        loggedIn: true,
        viewport: { width: size.width, height: size.height },
        scale: size.scale,
      });
      try {
        const t = catalogs[locale];
        await f.page.getByRole('button', { name: t['model.choose'], exact: true }).waitFor();
        for (const view of ['nav.chat', 'nav.documents', 'nav.llm']) {
          await showWorkspaceView(f.page, t[view]);
          assert.equal(
            await f.page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1),
            true,
            'no horizontal overflow',
          );
          await openSettings(f.page, 'appearance');
          await f.select.scrollIntoViewIfNeeded();
          assert.equal(await f.select.isVisible(), true);
          await f.select.focus();
          assert.equal(await f.select.evaluate((el) => document.activeElement === el), true);
        }
        if (locale === 'ru-RU' && size.scale === 2)
          await f.page.screenshot({
            path: fileURLToPath(new URL('../../logs/dev/f008-ru-zoom.png', import.meta.url)),
          });
        assert.deepEqual(f.errors, []);
        checks++;
      } finally {
        await f.context.close();
      }
    }
  return checks;
}
