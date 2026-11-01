import { showWorkspaceView, openSettings, logoutFromMenu } from './workspace-actions.mjs';
/** Locale browser checks use fake APIs, never live credentials or the development DB. */
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
    if (!/^\/(auth|admin|projects|models|llm|documents|chat|conversations)(\/|$)/.test(api)) {
      await route.continue();
      return;
    }
    requests.push({ api, method: request.method(), body: request.postData() });
    const json = (data) =>
      route.fulfill({ contentType: 'application/json', body: JSON.stringify(data) });
    if (api === '/conversations') return json({ items: [], next_cursor: null });
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
    if (api === '/admin/llm/connection' && request.method() === 'GET')
      return json({
        configured: true,
        base_url: 'https://example.test/v1',
        has_api_key: true,
        network: { mode: 'direct', proxy_url: null },
        allowed_model_ids: ['a', 'b'],
        default_model_id: 'a',
        version: 1,
        updated_at: null,
      });
    if (api === '/admin/llm/connection/verify') {
      if (state.llmGate) await state.llmGate;
      if (state.llmStatus !== 200)
        return route.fulfill({
          status: state.llmStatus,
          contentType: 'application/json',
          body: JSON.stringify({
            detail: {
              code: {
                401: 'authentication_required',
                403: 'csrf_invalid',
                422: 'invalid_llm_request',
                502: 'llm_provider_unavailable',
                503: 'llm_settings_unavailable',
              }[state.llmStatus],
              secret: 'secret-never-display',
            },
          }),
        });
      return json({ models: models.models, version: 1 });
    }
    if (api === '/llm/connection')
      return json({ configured: true, configuration_version: 1, selected_model_id: 'a' });
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
      await f.page.locator('#question').fill('Original draft');
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
      await f.page.locator('#llm-url').waitFor();
      await f.page.locator('#llm-key-action').click();
      await f.page.getByRole('option', { name: t['llm.org.replace'], exact: true }).click();
      await f.page.locator('#llm-key').fill('dummy-key');
      const next = locale === 'ru-RU' ? 'en-US' : 'ru-RU';
      const before = f.requests.filter((r) => r.api === '/chat').length;
      await choose(f, next);
      assert.equal(f.requests.filter((r) => r.api === '/chat').length, before);
      await showWorkspaceView(f.page, catalogs[next]['nav.documents']);
      assert.equal(
        await f.page.getByLabel(catalogs[next]['upload.title'], { exact: true }).inputValue(),
        'Original document',
      );
      assert.equal(
        await f.page
          .getByLabel(catalogs[next]['upload.file'], { exact: true })
          .evaluate((input) => input.files[0].name),
        'Original.txt',
      );
      await showWorkspaceView(f.page, catalogs[next]['nav.chat']);
      assert.equal(await f.page.locator('#question').inputValue(), 'Original draft');
      await openSettings(f.page, 'llm');
      await f.page.locator('#llm-url').waitFor();
      assert.equal(
        await f.page.locator('#llm-key').count(),
        0,
        'leaving settings discards secret draft',
      );
      for (const [status, key] of [
        [403, 'llm.errors.csrf'],
        [422, 'llm.errors.invalid'],
        [502, 'llm.errors.providerUnavailable'],
        [503, 'llm.errors.settings'],
      ]) {
        f.state.llmStatus = status;
        await f.page
          .getByRole('button', { name: catalogs[next]['llm.org.verify'], exact: true })
          .click();
        await f.page.getByText(catalogs[next][key], { exact: true }).first().waitFor();
        assert.ok(!(await f.page.locator('body').innerText()).includes('secret-never-display'));
        checks++;
      }
      f.state.llmStatus = 200;
      await f.page
        .getByRole('button', { name: catalogs[next]['llm.org.verify'], exact: true })
        .click();
      await f.page
        .getByRole('button', { name: catalogs[next]['llm.org.apply'], exact: true })
        .waitFor();
      assert.equal(
        f.requests.some((r) => r.api === '/admin/llm/connection' && r.method === 'PUT'),
        false,
        'checking never applies',
      );
      await choose(f, locale);
      await f.page.reload();
      await f.page.locator('.workspace-shell').waitFor();
      await openSettings(f.page, 'appearance');
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
    f.state.loginStatus = 401;
    await f.page.getByLabel('Email', { exact: true }).fill('user@example.test');
    await f.page
      .getByLabel(catalogs['vi-VN']['auth.password'], { exact: true })
      .fill('dummy-password');
    await f.page
      .getByRole('button', { name: catalogs['vi-VN']['auth.login'], exact: true })
      .click();
    await f.page.getByText(catalogs['vi-VN']['auth.errors.credentials'], { exact: true }).waitFor();
    await choose(f, 'ru-RU');
    await f.page.getByText(catalogs['ru-RU']['auth.errors.credentials'], { exact: true }).waitFor();
    assert.equal(
      await f.page.getByLabel(catalogs['ru-RU']['auth.password'], { exact: true }).inputValue(),
      'dummy-password',
    );
    f.state.loginStatus = 200;
    let release;
    f.state.loginGate = new Promise((resolve) => {
      release = resolve;
    });
    await f.page
      .getByRole('button', { name: catalogs['ru-RU']['auth.login'], exact: true })
      .click();
    await choose(f, 'en-US');
    release();
    await f.page.locator('.workspace-shell').waitFor();
    assert.equal(
      f.requests.filter((r) => r.api === '/auth/login').length,
      2,
      'locale switch never resubmits pending login',
    );
    assert.deepEqual(f.errors, []);
    checks++;
    let releaseModel;
    f.state.modelGate = new Promise((resolve) => {
      releaseModel = resolve;
    });
    await f.page
      .getByRole('button', { name: catalogs['en-US']['model.choose'], exact: true })
      .click();
    await f.page.getByRole('option', { name: 'Original model B b', exact: true }).click();
    await choose(f, 'ru-RU');
    releaseModel();
    await f.page
      .locator('.workspace-toolbar')
      .getByText('Original model B', { exact: true })
      .waitFor();
    assert.equal(
      f.requests.filter((r) => r.api === '/llm/connection/model').length,
      1,
      'locale never resubmits pending model selection',
    );
    await choose(f, 'en-US');
    checks++;
    await showWorkspaceView(f.page, 'Upload documents');
    await f.page.getByLabel('Project', { exact: true }).selectOption('p');
    await f.page.getByLabel('Document title', { exact: true }).fill('Locale upload');
    await f.page.getByLabel('Software', { exact: true }).fill('App');
    await f.page.getByLabel('Version', { exact: true }).fill('1');
    await f.page
      .getByLabel('File', { exact: true })
      .setInputFiles({ name: 'Locale.txt', mimeType: 'text/plain', buffer: Buffer.from('Text') });
    let releaseUpload;
    f.state.uploadGate = new Promise((resolve) => {
      releaseUpload = resolve;
    });
    await f.page.getByRole('button', { name: 'Upload', exact: true }).click();
    await f.page.getByRole('button', { name: 'Uploading…', exact: true }).waitFor();
    await choose(f, 'ru-RU');
    releaseUpload();
    await f.page.getByText('Ожидает обработки', { exact: true }).waitFor();
    f.state.ready = true;
    await choose(f, 'en-US');
    await f.page.getByText('Ready', { exact: true }).waitFor();
    assert.equal(f.requests.filter((r) => r.api === '/documents/upload').length, 1);
    await showWorkspaceView(f.page, 'Chat');
    checks++;
    // Locale navigation retains an active generation and never submits it twice.
    streamHooks.plan({
      initial: 'Original <b>partial</b>',
      next: ' original final',
      citations: [citation],
    });
    await f.page.locator('#question').fill('Original question');
    await f.page.getByRole('button', { name: catalogs['en-US']['chat.send'], exact: true }).click();
    await f.page.locator('.answer').filter({ hasText: 'Original <b>partial</b>' }).waitFor();
    const sent = f.requests.filter((r) => r.api === '/chat').length;
    await choose(f, 'ru-RU');
    assert.equal(f.requests.filter((r) => r.api === '/chat').length, sent);
    streamHooks.delta();
    await f.page.locator('.answer').filter({ hasText: 'original final' }).waitFor();
    streamHooks.finish();
    await f.page.getByText('1 источник', { exact: true }).waitFor();
    assert.equal(await f.page.locator('.answer b').count(), 0, 'provider text stays escaped');
    await f.page.getByText('1 источник', { exact: true }).click();
    assert.equal(await f.page.locator('.source-title').innerText(), citation.title);
    checks++;
  } finally {
    streamHooks.clear();
    await f.context.close();
  }
  return checks;
}
