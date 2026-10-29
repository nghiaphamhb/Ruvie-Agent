/** F015 browser: exercise the built UI against an isolated HTTP boundary. */
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
const server = createServer(async (req, res) => {
  const target = path.resolve(
    root,
    '.' + new URL(req.url, 'http://local').pathname.replace(/\/$/, '/index.html'),
  );
  if (!target.startsWith(root + path.sep)) return res.writeHead(403).end();
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
let browser;
try {
  browser = await chromium.launch({
    executablePath: process.env.RUVIE_BROWSER_PATH,
    headless: true,
  });
  const page = await browser.newPage({ locale: 'vi-VN', viewport: { width: 1366, height: 900 } });
  let patches = 0;
  let failure = null;
  let sessionRole = 'admin';
  let sessionId = 'actor';
  let lookupFailure = false;
  let release;
  let committed;
  let slow = false;
  let account = {
    id: 'target',
    display_name: 'Directory User',
    email: 'target@example.test',
    system_role: 'user',
    is_active: true,
    created_at: '2026-10-23T12:00:00Z',
  };
  const actor = {
    ...account,
    id: 'actor',
    display_name: 'Admin',
    email: 'admin@example.test',
    system_role: 'admin',
  };
  const errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.route('**/*', async (route) => {
    const url = new URL(route.request().url());
    if (!/^\/(auth|admin|projects|llm|models|documents)(\/|$)/.test(url.pathname))
      return route.continue();
    const json = (data, status = 200) => route.fulfill({ status, json: data });
    if (url.pathname === '/auth/session')
      return json({
        user: { id: sessionId, display_name: 'Admin', system_role: sessionRole },
        csrf_token: 'csrf',
      });
    if (url.pathname === '/auth/setup') return json({ requires_initial_admin: false });
    if (url.pathname === '/projects') return json({ items: [] });
    if (url.pathname === '/llm/connection')
      return json({
        source: 'server',
        base_url: 'https://example.test',
        has_api_key: true,
        selected_model_id: 'one',
      });
    if (url.pathname === '/models')
      return json({
        models: [{ id: 'one', name: 'Model' }],
        selected_model_id: 'one',
        selection_required: false,
      });
    if (url.pathname === '/admin/users/list')
      return json({
        users: [account, actor],
        total: 2,
        page: Number(url.searchParams.get('page')),
        page_size: Number(url.searchParams.get('page_size')),
        presence: {
          target: { is_online: account.is_active, last_active_at: null },
          actor: { is_online: true, last_active_at: null },
        },
      });
    if (url.pathname === '/admin/users/target/activity') {
      patches++;
      assert.equal(route.request().headers()['x-csrf-token'], 'csrf');
      if (slow)
        await new Promise((resolve) => {
          release = resolve;
        });
      if (failure === 'network') return route.abort();
      if (failure === 'malformed') return json({});
      if (failure) {
        const status =
          failure === 'authentication_required'
            ? 401
            : failure === 'account_not_found'
              ? 404
              : ['last_active_admin', 'self_deactivation_forbidden'].includes(failure)
                ? 409
                : failure === 'validation_error'
                  ? 422
                  : failure === 'account_activity_unavailable'
                    ? 503
                    : 403;
        return json({ detail: { code: failure } }, status);
      }
      account = { ...account, is_active: route.request().postDataJSON().is_active };
      committed?.();
      try {
        return await json({ user: account });
      } catch {
        // The browser can leave after the server has committed the operation.
        return;
      }
    }
    if (url.pathname === '/admin/users/target')
      return lookupFailure ? json({}, 503) : json({ user: account });
    return json({});
  });
  const origin = `http://127.0.0.1:${server.address().port}`;
  await page.goto(origin + '/?view=admin-users');
  await page.getByText('Directory User', { exact: true }).waitFor();
  assert.equal(await page.getByRole('button', { name: 'Khóa tài khoản Admin' }).isDisabled(), true);
  const ownAction = page.getByRole('button', { name: 'Khóa tài khoản Admin' });
  const targetAction = page.getByRole('button', { name: 'Khóa tài khoản Directory User' });
  const actionSizes = await targetAction
    .locator('..')
    .locator('button')
    .evaluateAll((buttons) =>
      buttons.map((button) => {
        const { width, height } = button.getBoundingClientRect();
        return { width, height };
      }),
    );
  assert.deepEqual(actionSizes, [
    { width: 40, height: 40 },
    { width: 40, height: 40 },
  ]);
  assert.equal(await targetAction.innerText(), '');
  assert.equal(await targetAction.locator('svg[aria-hidden="true"]').count(), 1);
  await ownAction.hover();
  await page.getByRole('tooltip', { name: 'Không thể tự khóa' }).waitFor();
  await page.mouse.move(0, 0);
  await ownAction.focus();
  await page.getByRole('tooltip', { name: 'Không thể tự khóa' }).waitFor();
  await page.keyboard.press('Enter');
  assert.equal(await page.getByRole('dialog').count(), 0);
  await page.keyboard.press('Escape');
  await page.getByRole('tooltip').waitFor({ state: 'hidden' });
  const cdp = await page.context().newCDPSession(page);
  await cdp.send('Emulation.setPageScaleFactor', { pageScaleFactor: 1.25 });
  assert.equal(await page.evaluate(() => window.visualViewport.scale), 1.25);
  await page.getByRole('button', { name: 'Khóa tài khoản Directory User' }).focus();
  await page.keyboard.press('Enter');
  let dialog = page.getByRole('dialog', { name: 'Khóa tài khoản?' });
  await dialog.waitFor();
  const destructiveColor = await dialog
    .getByRole('button', { name: 'Khóa tài khoản', exact: true })
    .evaluate((button) => getComputedStyle(button).backgroundColor);
  const channels = destructiveColor.match(/\d+/g).map(Number);
  assert.ok(
    channels[0] > channels[1] * 2 && channels[0] > channels[2] * 2,
    'deactivation confirmation has a red background',
  );
  await page.screenshot({
    path: fileURLToPath(new URL('../../logs/f015-actions-light.png', import.meta.url)),
  });
  assert.equal(
    await dialog
      .getByRole('button', { name: 'Hủy' })
      .evaluate((el) => el === document.activeElement),
    true,
  );
  await page.keyboard.press('Enter');
  await cdp.send('Emulation.setPageScaleFactor', { pageScaleFactor: 1 });
  assert.equal(patches, 0);
  await page.getByRole('button', { name: 'Khóa tài khoản Directory User' }).click();
  await dialog.getByRole('button', { name: 'Khóa tài khoản', exact: true }).click();
  await page.getByRole('button', { name: 'Mở lại tài khoản Directory User' }).waitFor();
  assert.equal(
    await page.getByRole('button', { name: 'Mở lại tài khoản Directory User' }).innerText(),
    '',
  );
  assert.equal(patches, 1);
  await page.getByRole('button', { name: 'Mở lại tài khoản Directory User' }).click();
  dialog = page.getByRole('dialog', { name: 'Mở lại tài khoản?' });
  const reactivateColor = await dialog
    .getByRole('button', { name: 'Mở lại', exact: true })
    .evaluate((button) => getComputedStyle(button).backgroundColor);
  const greenChannels = reactivateColor.match(/\d+/g).map(Number);
  assert.ok(
    greenChannels[1] > greenChannels[0] * 2 && greenChannels[1] > greenChannels[2],
    'reactivation confirmation has a green background',
  );
  await dialog.getByRole('button', { name: 'Mở lại', exact: true }).click();
  await page.getByRole('button', { name: 'Khóa tài khoản Directory User' }).waitFor();
  assert.equal(patches, 2);
  failure = 'last_active_admin';
  await page.getByRole('button', { name: 'Khóa tài khoản Directory User' }).click();
  dialog = page.getByRole('dialog', { name: 'Khóa tài khoản?' });
  await dialog.getByRole('button', { name: 'Khóa tài khoản', exact: true }).click();
  await page.getByText('Không thể khóa quản trị viên đang hoạt động cuối cùng.').waitFor();
  assert.equal(account.is_active, true);
  assert.equal(patches, 3);
  for (const [code, message] of [
    ['csrf_invalid', 'Không thể xác minh yêu cầu. Hãy tải lại trang trước khi gửi lại.'],
    ['origin_not_allowed', 'Nguồn gửi yêu cầu không được chấp nhận.'],
    ['validation_error', 'Hãy kiểm tra các trường thông tin.'],
    ['account_not_found', 'Tài khoản không còn tồn tại. Hãy tải lại danh sách rồi thử lại.'],
    ['self_deactivation_forbidden', 'Không thể tự khóa tài khoản của mình.'],
    ['account_activity_unavailable', 'Đã cập nhật trạng thái hiện tại.'],
    ['network', 'Đã cập nhật trạng thái hiện tại.'],
    ['malformed', 'Đã cập nhật trạng thái hiện tại.'],
  ]) {
    failure = code;
    await page.getByRole('button', { name: 'Khóa tài khoản Directory User' }).click();
    await dialog.getByRole('button', { name: 'Khóa tài khoản', exact: true }).click();
    await dialog.waitFor({ state: 'hidden' });
    await page.getByText(message, { exact: true }).waitFor();
    assert.equal(account.is_active, true, message);
    assert.equal(
      await page.getByRole('button', { name: 'Khóa tài khoản Directory User' }).isVisible(),
      true,
    );
  }
  failure = 'network';
  lookupFailure = true;
  await page.getByRole('button', { name: 'Khóa tài khoản Directory User' }).click();
  await dialog.getByRole('button', { name: 'Khóa tài khoản', exact: true }).click();
  await page
    .getByText('Chưa xác định được kết quả. Hãy tải lại trạng thái trước khi thao tác tiếp.')
    .waitFor();
  assert.equal(
    await page.getByRole('button', { name: 'Khóa tài khoản Directory User' }).isDisabled(),
    true,
  );
  lookupFailure = false;
  await page.evaluate(() => document.dispatchEvent(new Event('visibilitychange')));
  await page
    .getByRole('button', { name: 'Khóa tài khoản Directory User' })
    .waitFor({ state: 'visible' });
  await page.waitForFunction(() =>
    [...document.querySelectorAll('button')].some(
      (button) =>
        button.getAttribute('aria-label') === 'Khóa tài khoản Directory User' && !button.disabled,
    ),
  );
  failure = null;
  slow = true;
  await page.getByRole('button', { name: 'Khóa tài khoản Directory User' }).click();
  await dialog.getByRole('button', { name: 'Khóa tài khoản', exact: true }).click();
  const pendingButton = dialog.locator('button:disabled').last();
  await pendingButton.waitFor();
  assert.equal(await pendingButton.isDisabled(), true);
  assert.equal(patches, 13);
  assert.equal(await dialog.getByRole('button', { name: 'Hủy' }).isEnabled(), true);
  await dialog.getByRole('button', { name: 'Hủy' }).click();
  await dialog.waitFor({ state: 'hidden' });
  release();
  await page.getByRole('button', { name: 'Mở lại tài khoản Directory User' }).waitFor();
  assert.equal(patches, 13);
  assert.equal(await page.getByText('Đã khóa tài khoản.', { exact: true }).count(), 0);
  slow = false;
  for (const [locale, action, title] of [
    ['en-US', 'Reactivate Directory User', 'Reactivate account?'],
    ['ru-RU', 'Разблокировать Directory User', 'Разблокировать аккаунт?'],
  ]) {
    await page.locator('.account-trigger').click();
    await page.locator('.account-settings').click();
    await page.locator('#account-language').selectOption(locale);
    await page.locator('input[type=radio][value=dark]').check();
    await page.goBack();
    await page.getByRole('button', { name: action }).click();
    const localizedDialog = page.getByRole('dialog', { name: title });
    await localizedDialog.waitFor();
    await page.keyboard.press('Escape');
    await localizedDialog.waitFor({ state: 'hidden' });
    assert.equal(await page.locator('.workspace-shell').getAttribute('data-theme'), 'dark');
    if (locale === 'en-US') {
      await page.getByRole('button', { name: 'Deactivate Admin', exact: true }).focus();
      await page.getByRole('tooltip', { name: 'You cannot deactivate yourself' }).waitFor();
      await page.screenshot({
        path: fileURLToPath(new URL('../../logs/f015-actions-dark.png', import.meta.url)),
      });
      await page.keyboard.press('Escape');
    }
  }
  slow = true;
  await page.getByRole('button', { name: 'Разблокировать Directory User' }).click();
  const delayedDialog = page.getByRole('dialog', { name: 'Разблокировать аккаунт?' });
  await delayedDialog.getByRole('button', { name: 'Разблокировать', exact: true }).click();
  await delayedDialog.locator('button:disabled').last().waitFor();
  await page.keyboard.press('Escape');
  await delayedDialog.waitFor({ state: 'hidden' });
  await page.locator('.account-trigger').click();
  await page.locator('.account-settings').click();
  await page.locator('#account-language').waitFor();
  const delayedResponse = page.waitForResponse((response) =>
    response.url().endsWith('/admin/users/target/activity'),
  );
  release();
  await delayedResponse;
  assert.equal(await page.getByText('Аккаунт разблокирован.', { exact: true }).count(), 0);
  slow = false;
  await page.goBack();
  await page.evaluate(() => document.dispatchEvent(new Event('visibilitychange')));
  await page.getByRole('button', { name: 'Заблокировать Directory User' }).waitFor();
  slow = true;
  await page.getByRole('button', { name: 'Заблокировать Directory User' }).click();
  const identityDialog = page.getByRole('dialog', { name: 'Заблокировать аккаунт?' });
  await identityDialog.getByRole('button', { name: 'Заблокировать', exact: true }).click();
  await identityDialog.locator('button:disabled').last().waitFor();
  sessionId = 'new-actor';
  await page.goto(origin + '/?view=admin-users');
  await page.getByText('Directory User', { exact: true }).waitFor();
  const committedAfterNavigation = new Promise((resolve) => {
    committed = resolve;
  });
  release();
  await committedAfterNavigation;
  await page.waitForFunction(() => document.querySelector('.workspace-shell') !== null);
  assert.equal(await page.getByText('Аккаунт заблокирован.', { exact: true }).count(), 0);
  slow = false;
  await page.evaluate(() => document.dispatchEvent(new Event('visibilitychange')));
  await page.getByRole('button', { name: 'Разблокировать Directory User' }).waitFor();
  failure = 'admin_required';
  sessionRole = 'user';
  await page.getByRole('button', { name: 'Разблокировать Directory User' }).click();
  await page
    .getByRole('dialog', { name: 'Разблокировать аккаунт?' })
    .getByRole('button', { name: 'Разблокировать', exact: true })
    .click();
  await page.locator('.accounts-panel').waitFor({ state: 'hidden' });
  sessionRole = 'admin';
  await page.goto(origin + '/?view=admin-users');
  await page.getByRole('button', { name: 'Разблокировать Directory User' }).waitFor();
  failure = 'authentication_required';
  await page.getByRole('button', { name: 'Разблокировать Directory User' }).click();
  await page
    .getByRole('dialog', { name: 'Разблокировать аккаунт?' })
    .getByRole('button', { name: 'Разблокировать', exact: true })
    .click();
  await page.locator('#email').waitFor();
  assert.deepEqual(errors, []);
  console.log('F015 activity browser: 51 checks passed');
} finally {
  await browser?.close();
  await new Promise((resolve) => server.close(resolve));
}
