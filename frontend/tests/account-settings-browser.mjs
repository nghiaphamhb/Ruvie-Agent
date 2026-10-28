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
const mime = { '.js': 'text/javascript', '.css': 'text/css', '.svg': 'image/svg+xml' };
const server = createServer(async (req, res) => {
  const target = path.resolve(
    root,
    '.' + new URL(req.url, 'http://localhost').pathname.replace(/\/$/, '/index.html'),
  );
  if (!target.startsWith(root + path.sep)) return res.writeHead(403).end();
  try {
    res.setHeader('Content-Type', mime[path.extname(target)] || 'text/html');
    res.end(await readFile(target));
  } catch {
    res.writeHead(404).end();
  }
});
await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
const origin = `http://127.0.0.1:${server.address().port}`;
let browser;
let checks = 0;
try {
  browser = await chromium.launch({
    headless: true,
    executablePath: process.env.RUVIE_BROWSER_PATH || undefined,
  });
  const page = await browser.newPage({ locale: 'vi-VN', viewport: { width: 1280, height: 800 } });
  page.setDefaultTimeout(8000);
  const pageErrors = [];
  page.on('pageerror', (error) => pageErrors.push(error.message));
  let passwordStatus = 204;
  const passwordCalls = [];
  let passwordNetwork = false;
  let heldPassword;
  function deferPassword(status) {
    passwordStatus = status;
    let release, received, finished;
    const gate = new Promise((resolve) => {
      release = resolve;
    });
    const seen = new Promise((resolve) => {
      received = resolve;
    });
    const done = new Promise((resolve) => {
      finished = resolve;
    });
    heldPassword = { gate, received, finished };
    return { release, seen, done };
  }
  await page.route('**/*', async (route) => {
    const url = new URL(route.request().url());
    const api = url.pathname;
    const json = (data, status = 200) => route.fulfill({ status, json: data });
    if (api === '/auth/session')
      return json({
        user: { id: 'account-test', display_name: 'Test User', system_role: 'user' },
        csrf_token: 'test-csrf',
      });
    if (api === '/auth/presence') return route.fulfill({ status: 204 });
    if (api === '/auth/setup') return json({ requires_initial_admin: false });
    if (api === '/auth/password') {
      passwordCalls.push({
        body: route.request().postDataJSON(),
        headers: route.request().headers(),
      });
      const status = passwordStatus,
        network = passwordNetwork,
        held = heldPassword;
      heldPassword = undefined;
      if (held) {
        held.received();
        await held.gate;
      }
      try {
        if (network) return await route.abort('failed');
        if (status === 204) return await route.fulfill({ status: 204 });
        const codes = {
          401: 'authentication_required',
          403: 'csrf_invalid',
          422: 'current_password_incorrect',
          503: 'password_change_unavailable',
        };
        return await json(
          {
            detail: {
              code: codes[status],
              ...(status === 422
                ? { fields: { current_password: 'current_password_incorrect' } }
                : {}),
            },
          },
          status,
        );
      } catch (error) {
        if (!held) throw error;
        // Leaving the form aborts the browser request; the simulated server may still finish.
      } finally {
        held?.finished();
      }
    }
    if (/^\/(auth|admin|projects|llm|models|documents)(\/|$)/.test(api))
      return json({ detail: { code: 'test_unavailable' } }, 503);
    return route.continue();
  });
  await page.goto(origin);
  await page.locator('.account-trigger').click();
  await page.getByRole('menuitem', { name: 'Cài đặt', exact: true }).click();
  await page.getByRole('tab', { name: 'Tài khoản' }).click();
  assert.equal(await page.locator('#settings-tab-appearance').count(), 1);
  assert.equal(await page.locator('#settings-tab-account').count(), 1);
  const current = page.getByLabel('Mật khẩu hiện tại', { exact: true });
  const next = page.getByLabel('Mật khẩu mới', { exact: true });
  const confirm = page.getByLabel('Xác nhận mật khẩu mới', { exact: true });
  assert.equal(await current.inputValue(), '');
  assert.equal(
    await page.getByRole('tab', { name: 'Giao diện' }).getAttribute('aria-selected'),
    'false',
  );
  checks++;

  // Hover previews one navigation highlight without selecting or remounting a panel.
  const appearanceTab = page.locator('#settings-tab-appearance');
  const accountTab = page.locator('#settings-tab-account');
  const tabPaint = () =>
    page.locator('.settings-tabs button').evaluateAll((tabs) =>
      tabs.map((tab) => ({
        background: getComputedStyle(tab).backgroundColor,
        marker: getComputedStyle(tab, '::before').content !== 'none',
      })),
    );
  await appearanceTab.hover();
  let painted = await tabPaint();
  assert.deepEqual(
    painted.map((tab) => tab.marker),
    [true, false],
  );
  assert.notEqual(painted[0].background, painted[1].background);
  assert.equal(await accountTab.getAttribute('aria-selected'), 'true');
  assert.equal(await current.isVisible(), true);
  await accountTab.hover();
  painted = await tabPaint();
  assert.deepEqual(
    painted.map((tab) => tab.marker),
    [false, true],
  );
  await page.locator('.password-settings h3').hover();
  assert.deepEqual(
    (await tabPaint()).map((tab) => tab.marker),
    [false, true],
  );
  checks++;

  const submit = () => page.locator('.password-settings button[type="submit"]').click();
  const fill = async (old = 'current-password', value = 'new-password-123') => {
    await current.fill(old);
    await next.fill(value);
    await confirm.fill(value);
  };
  const toast = page.locator('[data-sonner-toast]');
  await submit();
  await toast.filter({ hasText: 'Hãy nhập trường này' }).waitFor();
  assert.equal(await current.evaluate((input) => input === document.activeElement), true);
  await fill('current-password', 'short');
  await submit();
  await toast.filter({ hasText: 'Độ dài mật khẩu' }).waitFor();
  await fill('current-password', 'current-password');
  await submit();
  await toast.filter({ hasText: 'khác mật khẩu hiện tại' }).waitFor();
  assert.equal(passwordCalls.length, 0);
  checks += 3;

  await current.fill('current-password');
  await next.fill('new-password-123');
  await confirm.fill('different-password');
  await page.getByRole('button', { name: 'Đổi mật khẩu' }).click();
  await page.locator('[data-sonner-toast]').filter({ hasText: 'không khớp' }).waitFor();
  assert.equal(passwordCalls.length, 0);
  assert.equal(await confirm.getAttribute('aria-invalid'), 'true');
  checks++;

  await fill(' current-password ', '😀'.repeat(12));
  await page.getByRole('button', { name: 'Hiện mật khẩu hiện tại', exact: true }).click();
  assert.equal(await current.getAttribute('type'), 'text');
  assert.equal(await next.getAttribute('type'), 'password');
  await page.getByRole('button', { name: 'Hiện mật khẩu mới', exact: true }).click();
  assert.equal(await confirm.getAttribute('type'), 'password');
  await page.getByRole('button', { name: 'Đổi mật khẩu' }).click();
  await page.locator('[data-sonner-toast]').filter({ hasText: 'Đã đổi mật khẩu' }).waitFor();
  assert.equal(passwordCalls.length, 1);
  assert.equal(passwordCalls[0].headers['x-csrf-token'], 'test-csrf');
  assert.equal(passwordCalls[0].body.current_password, ' current-password ');
  assert.equal(passwordCalls[0].body.new_password, '😀'.repeat(12));
  assert.deepEqual(Object.keys(passwordCalls[0].body).sort(), [
    'current_password',
    'new_password',
    'password_confirmation',
  ]);
  assert.equal(await current.inputValue(), '');
  assert.equal(await current.getAttribute('type'), 'password');
  assert.equal(await next.getAttribute('type'), 'password');
  checks++;

  passwordStatus = 422;
  await current.fill('wrong-current');
  await next.fill('another-new-password');
  await confirm.fill('another-new-password');
  await page.getByRole('button', { name: 'Đổi mật khẩu' }).click();
  await page
    .locator('[data-sonner-toast]')
    .filter({ hasText: 'Mật khẩu hiện tại không đúng' })
    .waitFor();
  assert.equal(passwordCalls.length, 2);
  assert.equal(await current.inputValue(), '');
  assert.equal(await current.evaluate((input) => input === document.activeElement), true);
  checks++;

  for (const [status, network, text] of [
    [403, false, 'Không thể xác minh yêu cầu'],
    [503, false, 'Không đổi được mật khẩu'],
    [204, true, 'Chưa xác định được kết quả'],
  ]) {
    passwordStatus = status;
    passwordNetwork = network;
    const before = passwordCalls.length;
    await fill();
    await submit();
    await toast.filter({ hasText: text }).waitFor();
    assert.equal(passwordCalls.length, before + 1);
    assert.equal(await current.inputValue(), '');
    assert.equal(await next.inputValue(), '');
    assert.equal(await confirm.inputValue(), '');
    assert.equal(await toast.count(), 1);
    checks++;
  }
  passwordNetwork = false;

  const pending = deferPassword(204);
  await fill();
  await submit();
  await pending.seen;
  assert.equal(await current.isDisabled(), true);
  assert.equal(await page.locator('.password-settings button[type="submit"]').isDisabled(), true);
  const pendingCalls = passwordCalls.length;
  await page.locator('.password-settings form').evaluate((form) => {
    form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
  });
  assert.equal(passwordCalls.length, pendingCalls);
  await page.locator('#settings-tab-appearance').click();
  pending.release();
  await pending.done;
  await page.locator('#settings-tab-account').click();
  assert.equal(await current.inputValue(), '');
  await page.waitForFunction(() => !document.querySelector('[data-sonner-toast]'));
  checks++;

  const lateExpired = deferPassword(401);
  await fill();
  await submit();
  await lateExpired.seen;
  await page.locator('.sidebar-brand').click();
  await page.locator('.account-trigger').click();
  await page.getByRole('menuitem', { name: 'Cài đặt', exact: true }).click();
  await current.waitFor();
  lateExpired.release();
  await lateExpired.done;
  assert.equal(await current.inputValue(), '');
  assert.equal(await page.locator('.workspace-shell').isVisible(), true);
  await page.waitForFunction(() => !document.querySelector('[data-sonner-toast]'));
  checks++;

  passwordStatus = 422;
  await fill();
  await submit();
  await toast.filter({ hasText: 'Mật khẩu hiện tại không đúng' }).waitFor();
  const callsBeforeLocale = passwordCalls.length;
  const localeWhileActive = (locale) =>
    page.locator('#account-language').evaluate((select, value) => {
      select.value = value;
      select.dispatchEvent(new Event('change', { bubbles: true }));
    }, locale);
  await localeWhileActive('en-US');
  await toast.filter({ hasText: 'The current password is incorrect' }).waitFor();
  assert.equal(await toast.count(), 1);
  await page.getByRole('button', { name: 'Close notification', exact: true }).click();
  await page.waitForFunction(() => !document.querySelector('[data-sonner-toast]'));
  await localeWhileActive('ru-RU');
  assert.equal(await toast.count(), 0);
  await localeWhileActive('vi-VN');
  assert.equal(passwordCalls.length, callsBeforeLocale);
  checks++;

  await page.getByRole('tab', { name: 'Giao diện' }).click();
  await page.locator('#account-language').selectOption('en-US');
  await page.getByRole('tab', { name: 'Account' }).click();
  assert.equal(await page.getByLabel('Current password', { exact: true }).count(), 1);
  await page.locator('#settings-tab-appearance').click();
  await page.locator('#account-language').selectOption('ru-RU');
  await page.getByRole('tab', { name: 'Аккаунт' }).click();
  assert.equal(await page.getByLabel('Текущий пароль', { exact: true }).count(), 1);
  assert.equal(passwordCalls.length, callsBeforeLocale);
  await page.locator('#settings-tab-appearance').press('Home');
  await page.locator('#settings-tab-account').press('End');
  assert.equal(await page.locator('#settings-tab-account').getAttribute('aria-selected'), 'true');
  // The workspace's existing mobile layout uses the user-controlled collapsed sidebar.
  await page.locator('.sidebar-collapse').click();
  await page.setViewportSize({ width: 360, height: 760 });
  await page.waitForFunction(() => {
    const input = document.querySelector('#change-current-password');
    return input && input.getBoundingClientRect().width >= 200;
  });
  assert.ok((await page.locator('#change-current-password').boundingBox()).width >= 200);
  assert.equal(
    await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
    true,
  );
  for (const theme of ['dark', 'light']) {
    await page.locator(`input[name="workspace-theme"][value="${theme}"]`).evaluate((input) => {
      input.checked = true;
      input.dispatchEvent(new Event('change', { bubbles: true }));
    });
    await page.waitForFunction(
      (value) => document.querySelector('.workspace-shell')?.dataset.theme === value,
      theme,
    );
    assert.ok((await page.locator('#change-current-password').boundingBox()).width >= 200);
    const controls = await page.locator('.password-settings').evaluate((form) => {
      const input = form.querySelector('input');
      const toggle = form.querySelector('.password-toggle');
      const button = form.querySelector('button[type="submit"]');
      const fieldBox = input.getBoundingClientRect();
      const toggleBox = toggle.getBoundingClientRect();
      const inputStyle = getComputedStyle(input);
      const buttonStyle = getComputedStyle(button);
      const luminance = (color) => {
        const channels = color
          .match(/[\d.]+/g)
          .slice(0, 3)
          .map(Number);
        return channels
          .map((channel) => {
            const value = channel / 255;
            return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
          })
          .reduce((sum, value, index) => sum + value * [0.2126, 0.7152, 0.0722][index], 0);
      };
      const textLuminance = luminance(buttonStyle.color);
      const backgroundLuminance = luminance(buttonStyle.backgroundColor);
      return {
        height: fieldBox.height,
        radius: parseFloat(inputStyle.borderRadius),
        inputColor: inputStyle.color,
        buttonContrast:
          (Math.max(textLuminance, backgroundLuminance) + 0.05) /
          (Math.min(textLuminance, backgroundLuminance) + 0.05),
        toggleInside: toggleBox.left >= fieldBox.left && toggleBox.right <= fieldBox.right + 1,
      };
    });
    assert.ok(controls.height >= 44);
    assert.ok(controls.radius >= 8);
    assert.equal(controls.toggleInside, true);
    assert.ok(controls.buttonContrast >= 4.5, `submit contrast in ${theme}`);
    assert.equal(controls.inputColor, theme === 'dark' ? 'rgb(240, 246, 252)' : 'rgb(35, 77, 112)');
  }
  checks++;

  const stored = await page.evaluate(() => ({
    local: { ...localStorage },
    session: { ...sessionStorage },
    url: location.href,
  }));
  assert.equal(JSON.stringify(stored).includes('current-password'), false);
  assert.equal(JSON.stringify(stored).includes('new-password-123'), false);
  checks++;

  await localeWhileActive('vi-VN');
  await page.setViewportSize({ width: 1280, height: 800 });
  passwordStatus = 401;
  await fill();
  await submit();
  await page.locator('.auth-card').waitFor();
  await toast.filter({ hasText: 'Phiên đăng nhập đã hết hạn' }).waitFor();
  assert.equal(await toast.count(), 1);
  assert.equal(await page.locator('.password-settings').count(), 0);
  checks++;
  assert.deepEqual(pageErrors, []);
} finally {
  await browser?.close();
  await new Promise((resolve) => server.close(resolve));
}
console.log(`F014 account settings browser checks passed: ${checks}`);
