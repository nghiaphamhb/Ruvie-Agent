/** F012-008: real built UI with isolated HTTP boundaries; never uses application accounts. */
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
const { chromium } = createRequire(import.meta.url)(
  process.env.RUVIE_PLAYWRIGHT_PATH || 'playwright',
);
const root = path.resolve(fileURLToPath(new URL('../dist/', import.meta.url)));
const streams = [];
const server = createServer(async (req, res) => {
  if (req.url === '/chat') {
    for await (const _part of req) {
      /* Drain request before streaming. */
    }
    res.writeHead(200, { 'Content-Type': 'text/event-stream' });
    res.write('event: delta\ndata: {"text":"Answer in progress"}\n\n');
    streams.push(() => {
      res.write('event: completed\ndata: {}\n\n');
      res.end();
    });
    return;
  }
  const target = path.resolve(
    root,
    '.' + new URL(req.url, 'http://local').pathname.replace(/\/$/, '/index.html'),
  );
  if (!target.startsWith(root + path.sep)) {
    res.writeHead(403).end();
    return;
  }
  try {
    res.setHeader(
      'Content-Type',
      {
        '.js': 'text/javascript',
        '.css': 'text/css',
        '.svg': 'image/svg+xml',
        '.png': 'image/png',
      }[path.extname(target)] || 'text/html',
    );
    res.end(await readFile(target));
  } catch {
    res.writeHead(404).end();
  }
});
await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
const origin = `http://127.0.0.1:${server.address().port}`;
let browser,
  checks = 0;
try {
  browser = await chromium.launch({
    executablePath: process.env.RUVIE_BROWSER_PATH,
    headless: true,
  });
  const page = await browser.newPage({ locale: 'vi-VN', viewport: { width: 1366, height: 900 } });
  page.setDefaultTimeout(7000);
  let role = 'user',
    signedIn = true,
    setup = false,
    resultCode = 'validation_error',
    slow = false,
    release;
  let uploadRelease,
    sessionRelease,
    sessionMode = 'normal';
  let directoryAccount = {
    id: 'user-1',
    display_name: 'Directory User',
    email: 'directory@example.test',
    system_role: 'user',
    is_active: true,
    created_at: '2026-10-23T12:00:00Z',
  };
  let receivedResetPassword;
  let activity = { is_online: true, last_active_at: new Date().toISOString() };
  let presenceFailure = false;
  const errors = [],
    calls = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.route('**/*', async (route) => {
    const url = new URL(route.request().url()),
      api = url.pathname;
    if (!/^\/(auth|admin|projects|llm|models|documents)(\/|$)/.test(api)) return route.continue();
    calls.push({ api, method: route.request().method() });
    const json = (data, status = 200) => route.fulfill({ status, json: data });
    const session = () => ({
      user: { id: 'actor', display_name: 'Admin', system_role: role },
      csrf_token: 'actor-csrf',
    });
    if (api === '/auth/session') {
      const current = session();
      if (sessionMode === 'error') return json({}, 503);
      if (sessionMode === 'slow')
        await new Promise((resolve) => {
          sessionRelease = resolve;
        });
      return json(signedIn ? current : {}, signedIn ? 200 : 401);
    }
    if (api === '/auth/setup') return json({ requires_initial_admin: setup });
    if (api === '/auth/register') {
      signedIn = true;
      role = 'admin';
      setup = false;
      return json(session(), 201);
    }
    if (api === '/auth/login') {
      signedIn = true;
      return json(session());
    }
    if (api === '/auth/logout') {
      signedIn = false;
      return route.fulfill({ status: 204 });
    }
    if (api === '/projects') return json({ items: [{ id: 'p', name: 'Project', code: 'P' }] });
    if (api === '/llm/connection')
      return json({
        source: 'server',
        base_url: 'https://example.test',
        has_api_key: true,
        selected_model_id: 'one',
      });
    if (api === '/models')
      return json({
        models: [{ id: 'one', name: 'First model' }],
        selected_model_id: 'one',
        selection_required: false,
      });
    if (api === '/documents/upload') {
      await new Promise((resolve) => {
        uploadRelease = resolve;
      });
      return json(
        { document_id: 'doc', revision_id: 'rev', job_id: 'job', status: 'pending' },
        202,
      );
    }
    if (api === '/documents/revisions/rev/status')
      return json({ revision_id: 'rev', status: 'ready', error_code: null });
    if (api === '/admin/users/list') {
      if (presenceFailure) return json({ detail: { code: 'account_lookup_unavailable' } }, 503);
      const query = new URLSearchParams(url.search);
      const secondPage = query.get('page') === '2';
      return json({
        users: [
          secondPage
            ? {
                id: 'user-21',
                display_name: 'Second page',
                email: 'second@example.test',
                system_role: 'admin',
                is_active: true,
                created_at: '2026-10-23T12:00:00Z',
              }
            : directoryAccount,
        ],
        total: 21,
        page: Number(query.get('page')),
        page_size: Number(query.get('page_size')),
        presence: { [secondPage ? 'user-21' : directoryAccount.id]: activity },
      });
    }
    if (api === '/admin/users/user-1' || api === '/admin/users/actor') {
      if (route.request().method() === 'PATCH') {
        const changes = route.request().postDataJSON();
        receivedResetPassword = changes.password;
        directoryAccount = { ...directoryAccount, ...changes };
        delete directoryAccount.password;
        if (directoryAccount.id === 'actor') role = directoryAccount.system_role;
        return json({ user: directoryAccount });
      }
      return json({ user: directoryAccount });
    }
    if (api === '/admin/users') {
      if (slow)
        await new Promise((resolve) => {
          release = resolve;
        });
      if (resultCode === 'success')
        return json(
          {
            user: {
              id: 'recipient',
              display_name: 'Recipient',
              email: 'recipient@example.test',
              system_role: 'user',
              is_active: true,
              created_at: '2026-10-23T12:00:00Z',
            },
          },
          201,
        );
      return json(
        { detail: { code: resultCode, fields: { password: 'password_length' } } },
        resultCode === 'authentication_required'
          ? 401
          : resultCode === 'validation_error'
            ? 422
            : 403,
      );
    }
    return json({});
  });
  const heading = page.locator('#admin-users-heading');
  const menu = () => page.locator('.account-trigger').click();
  async function openAdmin() {
    await menu();
    await page.getByRole('menuitem', { name: 'Quản trị', exact: true }).click();
    await heading.waitFor();
  }
  async function openForm() {
    await page.locator('#admin-users-heading').locator('..').getByRole('button').click();
  }
  async function closeForm() {
    await page.locator('.create-account-dialog > header button').click();
    await page.locator('.create-account-dialog').waitFor({ state: 'hidden' });
  }
  async function submit() {
    await page.locator('#admin-name').fill('Recipient');
    await page.locator('#admin-email').fill('recipient@example.test');
    await page.locator('#admin-password').fill('password12345');
    await page.locator('form[aria-label]').locator('button[type=submit]').click();
  }
  await page.goto(origin + '/?view=admin-users&keep=value');
  await page.locator('#question').waitFor();
  assert.notEqual(new URL(page.url()).searchParams.get('view'), 'admin-users');
  assert.equal(new URL(page.url()).searchParams.get('keep'), 'value');
  await menu();
  assert.equal(await page.locator('.account-admin').count(), 0);
  await page.keyboard.press('Escape');
  assert.equal(
    calls.some((call) => call.api.startsWith('/admin')),
    false,
  );
  checks++;

  await page.locator('#question').fill('User settings draft');
  await menu();
  await page.locator('.account-settings').click();
  await page.locator('#settings-heading').waitFor();
  assert.equal(new URL(page.url()).searchParams.get('view'), 'settings');
  assert.equal(await page.locator('.workspace-sidebar').isVisible(), true);
  assert.equal(await page.locator('#question').isVisible(), false);
  assert.equal(await page.locator('dialog[open]').count(), 0);
  assert.equal(await page.getByRole('tab').count(), 2);
  assert.equal(await page.getByRole('tab', { name: 'Tài khoản', exact: true }).isVisible(), true);
  assert.equal(await page.getByRole('tab', { name: 'Giao diện', exact: true }).isVisible(), true);
  assert.equal(await page.locator('#llm-url').count(), 0);
  await page.getByRole('radio', { name: 'Sáng', exact: true }).check();
  await page.reload();
  await page.locator('#settings-heading').waitFor();
  assert.equal(await page.getByRole('radio', { name: 'Sáng', exact: true }).isChecked(), true);
  await page.locator('.sidebar-brand').click();
  await page.locator('#question').fill('Back from personal settings');
  await menu();
  await page.locator('.account-settings').click();
  await page.locator('#settings-heading').waitFor();
  await page.goBack();
  await page.locator('#question').waitFor();
  assert.equal(await page.locator('#question').inputValue(), 'Back from personal settings');
  await page.goForward();
  await page.locator('#settings-heading').waitFor();
  await page.locator('.sidebar-brand').click();
  checks++;

  role = 'admin';
  await page.reload();
  await page.locator('#question').fill('Draft survives navigation');
  await openAdmin();
  assert.equal(new URL(page.url()).searchParams.get('view'), 'admin-users');
  assert.equal(await heading.evaluate((el) => el === document.activeElement), true);
  await page.getByText('Directory User', { exact: true }).waitFor();
  const [searchBox, createBox, tableBox, footerBox] = await Promise.all([
    page.locator('.accounts-panel > header input').boundingBox(),
    page.locator('.accounts-panel > header button').boundingBox(),
    page.locator('.directory table').boundingBox(),
    page.locator('.directory .pagination').boundingBox(),
  ]);
  assert.ok(Math.abs(searchBox.y - createBox.y) < 1, 'search and create share one toolbar row');
  assert.ok(Math.abs(searchBox.x - tableBox.x) < 1, 'search aligns with the table left edge');
  assert.ok(
    Math.abs(createBox.x + createBox.width - tableBox.x - tableBox.width) < 1,
    'create aligns with the table right edge',
  );
  assert.ok(
    tableBox.y - searchBox.y - searchBox.height >= 12 &&
      tableBox.y - searchBox.y - searchBox.height <= 20,
    'table sits directly below the toolbar',
  );
  assert.ok(
    Math.abs(footerBox.x - tableBox.x) < 1 && Math.abs(footerBox.width - tableBox.width) < 1,
    'pagination shares the table edges',
  );
  await page.screenshot({
    path: fileURLToPath(new URL('../../logs/admin-users-layout.png', import.meta.url)),
  });
  assert.equal(await page.getByRole('columnheader', { name: 'Hoạt động gần nhất' }).count(), 1);
  await page.locator('.directory .presence.online').getByText('Online', { exact: true }).waitFor();
  presenceFailure = true;
  await page.evaluate(() => document.dispatchEvent(new Event('visibilitychange')));
  await page.locator('.directory .presence').getByText('Chưa cập nhật', { exact: true }).waitFor();
  assert.equal(
    await page.getByRole('cell', { name: 'Directory User', exact: true }).isVisible(),
    true,
  );
  presenceFailure = false;
  activity = { is_online: false, last_active_at: new Date(Date.now() - 5 * 60000).toISOString() };
  await page.evaluate(() => document.dispatchEvent(new Event('visibilitychange')));
  await page.locator('.directory .presence').getByText('5 phút trước', { exact: true }).waitFor();
  activity = { is_online: false, last_active_at: null };
  await page.evaluate(() => document.dispatchEvent(new Event('visibilitychange')));
  await page.locator('.directory .presence').getByText('Chưa hoạt động', { exact: true }).waitFor();
  activity = { is_online: true, last_active_at: new Date().toISOString() };
  await page.evaluate(() => document.dispatchEvent(new Event('visibilitychange')));
  await page.locator('.directory .presence.online').waitFor();
  checks++;
  assert.equal(await page.getByRole('columnheader', { name: 'Ngày tạo' }).count(), 1);
  assert.equal(
    await page.getByRole('button', { name: 'Chỉnh sửa Directory User' }).isDisabled(),
    false,
  );
  assert.equal(await page.getByText('Trang 1 / 2').count(), 1);
  await page.getByRole('button', { name: 'Sau', exact: true }).click();
  await page.getByText('Second page', { exact: true }).waitFor();
  assert.equal(await page.getByText('Trang 2 / 2').count(), 1);
  await page.getByRole('searchbox', { name: 'Tìm theo tên hoặc email' }).fill('filter');
  await page.getByText('Trang 1 / 2').waitFor();
  assert.ok(calls.some((call) => call.api === '/admin/users/list'));
  let editButton = page.getByRole('button', { name: 'Chỉnh sửa Directory User' });
  await editButton.click();
  const editDialog = page.getByRole('dialog', { name: 'Chỉnh sửa người dùng' });
  await editDialog.waitFor();
  await page.screenshot({
    path: fileURLToPath(new URL('../../logs/admin-edit-modal.png', import.meta.url)),
  });
  await editDialog.locator('select').click();
  await page.screenshot({
    path: fileURLToPath(new URL('../../logs/admin-edit-role-dropdown.png', import.meta.url)),
  });
  await page.keyboard.press('Escape');
  assert.equal(await editDialog.isVisible(), true, 'picker Escape keeps Edit User open');
  assert.equal(await editDialog.getByLabel('Tên').inputValue(), 'Directory User');
  assert.equal(await editDialog.getByLabel('Email').inputValue(), 'directory@example.test');
  assert.equal(await editDialog.getByLabel('Mật khẩu mới').inputValue(), '');
  assert.equal(await editDialog.getByLabel('Vai trò').isDisabled(), false);
  assert.equal(await editDialog.getByLabel('Mật khẩu mới').isDisabled(), false);
  assert.equal(await editDialog.getByRole('button', { name: 'Lưu' }).isDisabled(), true);
  await editDialog.getByLabel('Mật khẩu mới').fill('  reset-password-456  ');
  assert.equal(await editDialog.getByRole('button', { name: 'Lưu' }).isDisabled(), false);
  await editDialog.getByRole('button', { name: 'Lưu' }).click();
  await page
    .getByText('Mật khẩu đã được cập nhật và các phiên của người dùng đã đăng xuất.', {
      exact: true,
    })
    .waitFor();
  assert.equal(receivedResetPassword, '  reset-password-456  ');
  assert.equal(await editDialog.getByLabel('Mật khẩu mới').inputValue(), '');
  assert.equal(await editDialog.getByRole('button', { name: 'Lưu' }).isDisabled(), true);
  assert.equal(JSON.stringify(directoryAccount).includes('reset-password'), false);
  assert.equal(await page.evaluate(() => document.body.style.overflow), 'hidden');
  const closeEditButton = editDialog.getByRole('button', { name: 'Đóng' });
  await closeEditButton.focus();
  await page.keyboard.press('Shift+Tab');
  assert.equal(
    await editDialog
      .getByRole('button', { name: 'Hủy' })
      .evaluate((el) => el === document.activeElement),
    true,
  );
  await page.keyboard.press('Tab');
  assert.equal(await closeEditButton.evaluate((el) => el === document.activeElement), true);
  await editDialog.getByRole('button', { name: 'Hiện mật khẩu' }).click();
  assert.equal(await editDialog.getByLabel('Mật khẩu mới').getAttribute('type'), 'text');
  await page.keyboard.press('Escape');
  await editDialog.waitFor({ state: 'hidden' });
  assert.equal(await editButton.evaluate((el) => el === document.activeElement), true);
  await editButton.click();
  await editDialog.waitFor();
  assert.equal(await editDialog.getByLabel('Mật khẩu mới').inputValue(), '');
  await editDialog.getByLabel('Tên').fill('  Directory User  ');
  await editDialog.getByLabel('Email').fill(' DIRECTORY@example.test ');
  assert.equal(await editDialog.getByRole('button', { name: 'Lưu' }).isDisabled(), true);
  await editDialog.getByLabel('Tên').fill('Updated Directory User');
  await editDialog.getByLabel('Email').fill('UPDATED@example.test');
  await editDialog.getByLabel('Vai trò').selectOption('admin');
  assert.equal(await editDialog.getByRole('button', { name: 'Lưu' }).isDisabled(), false);
  await editDialog.getByRole('button', { name: 'Lưu' }).click();
  await page.getByText('Thông tin người dùng đã được cập nhật.', { exact: true }).waitFor();
  assert.equal(await editDialog.isVisible(), true);
  assert.equal(await editDialog.getByLabel('Tên').inputValue(), 'Updated Directory User');
  assert.equal(await editDialog.getByLabel('Email').inputValue(), 'updated@example.test');
  assert.equal(await editDialog.getByLabel('Vai trò').inputValue(), 'admin');
  assert.equal(await editDialog.getByRole('button', { name: 'Lưu' }).isDisabled(), true);
  await page.getByRole('cell', { name: 'Updated Directory User', exact: true }).waitFor();
  await editDialog.getByRole('button', { name: 'Đóng' }).click();
  editButton = page.getByRole('button', { name: 'Chỉnh sửa Updated Directory User' });
  assert.equal(await editButton.evaluate((el) => el === document.activeElement), true);
  await editButton.click();
  await editDialog.waitFor();
  await page.locator('[data-edit-user-backdrop]').click({ position: { x: 2, y: 2 } });
  await editDialog.waitFor({ state: 'hidden' });
  checks++;
  await openForm();
  await page.locator('#admin-password').fill('discard-on-exit');
  await page.goBack();
  await page.locator('#question').waitFor();
  assert.equal(await page.locator('#question').inputValue(), 'Draft survives navigation');
  assert.equal(await page.locator('#admin-password').count(), 0);
  await page.goForward();
  await heading.waitFor();
  await openForm();
  assert.equal(await page.locator('#admin-password').inputValue(), '');
  checks++;
  await page.reload();
  await heading.waitFor();
  checks++;

  // Stream and drafts stay owned by the same workspace while its admin page comes and goes.
  await page.goBack();
  await page.locator('#question').waitFor();
  await page.locator('#question').fill('Question while navigating');
  await page.locator('#question').press('Enter');
  await page.getByText('Answer in progress', { exact: false }).first().waitFor();
  const modelsBeforeAdmin = calls.filter((call) => call.api === '/models').length;
  await openAdmin();
  assert.equal(calls.filter((call) => call.api === '/models').length, modelsBeforeAdmin);
  streams.at(-1)();
  await page.goBack();
  await page.getByText('Answer in progress', { exact: false }).first().waitFor();
  checks++;

  await page.getByRole('navigation').getByRole('button', { name: 'Tài liệu', exact: true }).click();
  await page.locator('.upload-form select').selectOption('p');
  await page.getByLabel('Tên tài liệu', { exact: true }).fill('Upload survives navigation');
  await page.getByLabel('Phần mềm', { exact: true }).fill('CAD');
  await page.getByLabel('Phiên bản', { exact: true }).fill('1');
  await page
    .locator('.upload-form input[type=file]')
    .setInputFiles({ name: 'sample.txt', mimeType: 'text/plain', buffer: Buffer.from('sample') });
  await page.evaluate(() => {
    window.originalUploadInput = document.querySelector('.upload-form input[type=file]');
  });
  await page.locator('.upload-submit').click();
  await openAdmin();
  assert.equal(
    await page.evaluate(
      () => window.originalUploadInput === document.querySelector('.upload-form input[type=file]'),
    ),
    true,
  );
  while (!uploadRelease) await new Promise((resolve) => setTimeout(resolve, 10));
  uploadRelease();
  await page.goBack();
  await page.locator('.upload-status').getByText('Sẵn sàng', { exact: true }).waitFor();
  assert.equal(
    await page.getByLabel('Tên tài liệu', { exact: true }).inputValue(),
    'Upload survives navigation',
  );
  assert.equal(
    await page.locator('.upload-form input[type=file]').evaluate((el) => el.files[0].name),
    'sample.txt',
  );
  checks++;

  await openAdmin();
  await openForm();
  await page.locator('#admin-name').fill('Locale draft');
  await page.locator('#admin-password').fill('secret-locale');
  await closeForm();
  await menu();
  await page.locator('.account-settings').click();
  await page.locator('#account-language').selectOption('en-US');
  await page.goBack();
  await heading.waitFor();
  assert.equal(await heading.textContent(), 'Users');
  await openForm();
  assert.equal(await page.locator('#admin-name').inputValue(), '');
  assert.equal(await page.locator('#admin-password').inputValue(), '');
  checks++;
  await closeForm();
  await menu();
  await page.locator('.account-settings').click();
  await page.locator('#account-language').selectOption('ru-RU');
  await page.locator('input[type=radio][value=dark]').check();
  await page.goBack();
  await heading.waitFor();
  assert.equal(await heading.textContent(), 'Пользователи');
  await openForm();
  checks++;
  assert.equal(await page.locator('.workspace-shell').getAttribute('data-theme'), 'dark');
  await page.screenshot({
    path: fileURLToPath(new URL('../../logs/admin-task008-dark.png', import.meta.url)),
    fullPage: true,
  });
  checks++;
  await closeForm();
  await menu();
  await page.locator('.account-settings').click();
  await page.locator('#account-language').selectOption('vi-VN');
  await page.getByRole('radio', { name: 'Sáng', exact: true }).check();
  await page.goBack();
  await heading.waitFor();
  assert.equal(await page.locator('.workspace-shell').getAttribute('data-theme'), 'light');
  await menu();
  await page.keyboard.press('ArrowDown');
  assert.equal(
    await page.locator('.account-settings').evaluate((el) => el === document.activeElement),
    true,
  );
  await page.keyboard.press('Escape');
  assert.equal(await page.locator('#admin-password').count(), 0);
  await page.locator('.sidebar-collapse').click();
  checks++;
  await page.setViewportSize({ width: 1366, height: 900 });

  resultCode = 'success';
  await openForm();
  await submit();
  await page.getByRole('heading', { name: 'Đã tạo tài khoản', exact: true }).waitFor();
  assert.equal(await page.locator('.account-name').textContent(), 'Admin');
  await menu();
  await page.locator('.account-settings').click();
  await page.locator('#account-language').selectOption('en-US');
  await page.goBack();
  await heading.waitFor();
  await page.getByRole('heading', { name: 'Account created', exact: true }).waitFor();
  assert.equal(await page.locator('.result').getByText('User', { exact: true }).count(), 1);
  checks++;
  await menu();
  await page.locator('.account-settings').click();
  await page.locator('#account-language').selectOption('vi-VN');
  await page.goBack();
  await heading.waitFor();
  await openForm();

  // CSRF rejection stays in administration; demotion leaves it without logging out.
  resultCode = 'csrf_invalid';
  await submit();
  await page.getByRole('alert').filter({ hasText: 'xác minh' }).waitFor();
  assert.equal(await heading.isVisible(), true);
  checks++;
  await closeForm();
  await menu();
  await page.locator('.account-settings').click();
  await page.locator('#account-language').selectOption('en-US');
  await page.goBack();
  await heading.waitFor();
  await openForm();
  await submit();
  await page.getByRole('alert').filter({ hasText: 'could not be verified' }).waitFor();
  assert.equal(await page.locator('#admin-name').inputValue(), 'Recipient');
  await closeForm();
  await menu();
  await page.locator('.account-settings').click();
  await page.locator('#account-language').selectOption('vi-VN');
  await page.goBack();
  await heading.waitFor();
  await openForm();
  checks++;
  resultCode = 'origin_not_allowed';
  await submit();
  await page.getByRole('alert').filter({ hasText: 'Nguồn gửi' }).waitFor();
  assert.equal(await heading.isVisible(), true);
  checks++;
  resultCode = 'admin_required';
  role = 'user';
  await submit();
  await page.locator('#question').waitFor();
  await menu();
  assert.equal(await page.locator('.account-admin').count(), 0);
  await page.keyboard.press('Escape');
  checks++;
  role = 'user';
  await page.goto(origin + '/?view=admin-users');
  await page.locator('#question').waitFor();
  checks++;

  role = 'admin';
  await page.goto(origin);
  await openAdmin();
  await openForm();
  slow = true;
  const prior = calls.filter((call) => call.api === '/admin/users').length;
  await submit();
  while (!release) await new Promise((resolve) => setTimeout(resolve, 10));
  await page.goBack();
  await page.locator('#question').waitFor();
  release();
  slow = false;
  await page.waitForTimeout(100);
  assert.equal(await page.locator('#admin-password').count(), 0);
  assert.equal(calls.filter((call) => call.api === '/admin/users').length, prior + 1);
  checks++;

  await openAdmin();
  await openForm();
  resultCode = 'authentication_required';
  await submit();
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).waitFor();
  checks++;
  signedIn = false;
  setup = true;
  await page.goto(origin);
  await page.getByLabel('Tên hiển thị').fill('Initial admin');
  await page.getByLabel('Email', { exact: true }).fill('first@example.test');
  await page.getByLabel('Mật khẩu', { exact: true }).fill('password12345');
  await page.locator('#password_confirmation').fill('password12345');
  await page.locator('form:has(#password_confirmation) button[type=submit]').click();
  await heading.waitFor();
  assert.equal(new URL(page.url()).searchParams.get('view'), 'admin-users');
  checks++;
  // A navigation read may become stale or fail without expiring the current login.
  await page.locator('.sidebar-brand').click();
  await page.locator('#question').waitFor();
  sessionMode = 'error';
  await menu();
  await page.locator('.account-admin').click();
  await page.getByRole('alert').filter({ hasText: 'Không thể kiểm tra quyền' }).waitFor();
  assert.equal(await page.locator('.workspace-shell').count(), 1);
  checks++;
  sessionMode = 'slow';
  await menu();
  await page.locator('.account-admin').click();
  while (!sessionRelease) await new Promise((resolve) => setTimeout(resolve, 10));
  await page.locator('.sidebar-brand').click();
  sessionRelease();
  sessionMode = 'normal';
  await page.waitForTimeout(100);
  assert.equal(await heading.count(), 0);
  checks++;
  role = 'user';
  await menu();
  await page.locator('.account-admin').click();
  await page.getByRole('alert').filter({ hasText: 'không có quyền' }).waitFor();
  assert.equal(await heading.count(), 0);
  checks++;
  await menu();
  await page.getByRole('menuitem', { name: 'Đăng xuất', exact: true }).click();
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).waitFor();
  assert.equal(new URL(page.url()).searchParams.has('view'), false);
  assert.equal(
    await page.evaluate(() =>
      JSON.stringify({ ...localStorage, ...sessionStorage }).includes('secret-locale'),
    ),
    false,
  );
  checks++;
  signedIn = true;
  role = 'admin';
  resultCode = 'validation_error';
  await page.goto(origin);
  await openAdmin();
  await openForm();
  slow = true;
  release = undefined;
  await submit();
  while (!release) await new Promise((resolve) => setTimeout(resolve, 10));
  await page.goBack();
  await page.locator('#question').waitFor();
  await menu();
  await page.getByRole('menuitem', { name: 'Đăng xuất', exact: true }).click();
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).waitFor();
  release();
  slow = false;
  role = 'user';
  await page.getByLabel('Email', { exact: true }).fill('other@example.test');
  await page.getByLabel('Mật khẩu', { exact: true }).fill('password12345');
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click();
  await page.locator('#question').waitFor();
  assert.equal(await page.locator('#admin-password').count(), 0);
  assert.equal(await page.locator('.account-admin').count(), 0);
  checks++;
  // F013-002: both admin views share the workspace and revalidate server identity.
  role = 'admin';
  await page.goto(origin);
  await page.locator('#question').fill('Chat draft beside administration');
  await openAdmin();
  const usersTab = page.locator('#admin-tab-users');
  const settingTab = page.locator('#admin-tab-setting');
  await usersTab.waitFor();
  assert.equal(await usersTab.getAttribute('aria-selected'), 'true');
  assert.equal(await page.locator('.workspace-sidebar').isVisible(), true);
  assert.equal(await page.locator('#question').isVisible(), false);
  checks++;

  await settingTab.click();
  const settingsHeading = page.locator('#admin-settings-heading');
  await settingsHeading.waitFor();
  assert.equal(new URL(page.url()).searchParams.get('view'), 'admin-settings');
  assert.equal(await settingTab.getAttribute('aria-selected'), 'true');
  assert.equal(await heading.isVisible(), false);
  assert.equal(await page.locator('dialog[open]').count(), 0);
  assert.equal(await settingTab.innerText(), 'Cài đặt hệ thống');
  const settings = page.locator('#admin-panel-setting .settings-embedded');
  assert.equal(await settings.locator('[role=tab]').count(), 1);
  assert.equal(await settings.getByRole('tab', { name: 'Giao diện', exact: true }).count(), 0);
  await page.locator('#admin-settings-tab-llm').click();
  await settings.locator('#llm-url').fill('https://draft.example.test/v1');
  await page.locator('#admin-settings-tab-llm').press('Home');
  assert.equal(await page.locator('#admin-settings-llm').isVisible(), true);
  await menu();
  await page.locator('.account-settings').click();
  await page.locator('#settings-heading').waitFor();
  assert.equal(await page.locator('#admin-panel-setting').isVisible(), false);
  assert.equal(await page.locator('#llm-url').isVisible(), false);
  await page.getByRole('radio', { name: 'Sáng', exact: true }).check();
  assert.equal(await page.locator('.workspace-shell').getAttribute('data-theme'), 'light');
  await page.goBack();
  await settingsHeading.waitFor();
  checks++;

  await usersTab.click();
  await heading.waitFor();
  await usersTab.press('ArrowRight');
  await settingsHeading.waitFor();
  assert.equal(await settingTab.evaluate((el) => el === document.activeElement), true);
  await page.goBack();
  await heading.waitFor();
  assert.equal(await usersTab.getAttribute('aria-selected'), 'true');
  await page.goForward();
  await settingsHeading.waitFor();
  await page.locator('#admin-settings-tab-llm').click();
  assert.equal(await settings.locator('#llm-url').inputValue(), 'https://draft.example.test/v1');
  checks++;

  // A fresh URL restores the selected admin view.
  await page.reload();
  await settingsHeading.waitFor();
  await page.locator('#admin-tab-users').click();
  await page.getByText(directoryAccount.display_name, { exact: true }).waitFor();
  await page.locator('#admin-tab-setting').click();
  await page.locator('#admin-settings-tab-llm').click();
  assert.equal(await settings.locator('#llm-url').isVisible(), true);
  await menu();
  await page.locator('.account-settings').click();
  await page.getByRole('radio', { name: 'Tối', exact: true }).check();
  await page.goBack();
  await settingsHeading.waitFor();
  await page.screenshot({
    path: fileURLToPath(new URL('../../logs/admin-task013-setting-dark.png', import.meta.url)),
    fullPage: true,
  });
  checks++;

  // A retained admin page must release its native modal while personal settings are shown.
  await menu();
  await page.locator('.account-settings').click();
  await page.locator('#settings-heading').waitFor();
  await openAdmin();
  const directoryBeforeModal = await page.locator('.directory').boundingBox();
  await openForm();
  const createDialog = page.locator('.create-account-dialog');
  await createDialog.waitFor();
  assert.deepEqual(await page.locator('.directory').boundingBox(), directoryBeforeModal);
  await page.locator('#admin-name').fill('New user');
  await page.locator('#admin-email').fill('new-user@example.test');
  await page.locator('#admin-password').fill('retained-modal-draft');
  await page.screenshot({
    path: fileURLToPath(new URL('../../logs/admin-create-modal.png', import.meta.url)),
  });
  await createDialog.locator('select').click();
  await page.screenshot({
    path: fileURLToPath(new URL('../../logs/admin-create-role-dropdown.png', import.meta.url)),
  });
  await page.keyboard.press('Escape');
  assert.equal(await createDialog.isVisible(), true, 'picker Escape keeps Create account open');
  await page.goBack();
  await page.locator('#settings-heading').waitFor();
  assert.equal(await page.locator('dialog:modal').count(), 0);
  assert.equal(await page.evaluate(() => document.body.style.overflow), '');
  await page.getByRole('radio', { name: 'Tối', exact: true }).check();
  await page.goForward();
  await createDialog.waitFor();
  assert.equal(await page.locator('#admin-password').inputValue(), 'retained-modal-draft');
  await page.mouse.click(4, 4);
  await createDialog.waitFor({ state: 'hidden' });
  assert.equal(await page.locator('#admin-password').count(), 0);
  assert.equal(
    await page
      .locator('.accounts-panel > header button')
      .evaluate((el) => el === document.activeElement),
    true,
  );
  checks++;

  await page.locator('.sidebar-brand').click();
  await page.locator('#question').fill('Keep this draft after role revocation');
  await openAdmin();
  role = 'user';
  await settingTab.click();
  await page.locator('#question').waitFor();
  assert.equal(
    await page.locator('#question').inputValue(),
    'Keep this draft after role revocation',
  );
  assert.equal(await page.locator('.admin-panel .settings-embedded').count(), 0);
  assert.equal(await page.locator('.account-admin').count(), 0);
  await page.goto(origin + '/?view=admin-settings&keep=value');
  await page.locator('#question').waitFor();
  assert.equal(new URL(page.url()).searchParams.has('view'), false);
  assert.equal(new URL(page.url()).searchParams.get('keep'), 'value');
  assert.equal(await page.locator('.admin-panel .settings-embedded').count(), 0);
  checks++;

  // Self-demotion updates the live session role and leaves the user in chat.
  role = 'admin';
  directoryAccount = {
    ...directoryAccount,
    id: 'actor',
    display_name: 'Admin',
    email: 'admin@example.test',
    system_role: 'admin',
  };
  await page.goto(origin + '/?view=admin-users');
  await heading.waitFor();
  const selfEdit = page.getByRole('button', { name: 'Chỉnh sửa Admin' });
  const logoutCountBeforeSelfDemotion = calls.filter((call) => call.api === '/auth/logout').length;
  await selfEdit.click();
  const selfDialog = page.getByRole('dialog', { name: 'Chỉnh sửa người dùng' });
  await selfDialog.getByLabel('Vai trò').selectOption('user');
  await selfDialog.getByRole('button', { name: 'Lưu' }).click();
  await page.locator('#question').waitFor();
  assert.equal(new URL(page.url()).searchParams.has('view'), false);
  assert.equal(await page.locator('.account-admin').count(), 0);
  const refreshedSession = await page.evaluate(async () => {
    const response = await fetch('/auth/session');
    return response.ok ? response.json() : null;
  });
  assert.equal(refreshedSession.user.system_role, 'user');
  assert.equal(
    calls.filter((call) => call.api === '/auth/logout').length,
    logoutCountBeforeSelfDemotion,
  );
  checks++;
  assert.deepEqual(errors, []);
  checks++;
  console.log(`Admin browser: ${checks} groups passed`);
} finally {
  await browser?.close();
  for (const finish of streams) finish();
  await new Promise((resolve) => server.close(resolve));
}
