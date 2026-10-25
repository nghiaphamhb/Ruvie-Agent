import assert from 'node:assert/strict';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';
import { createServer } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

test('admin form validates identity/password without a confirmation and rejects unknown roles', async () => {
  const module = await import('../src/lib/features/admin/admin-form.ts').catch(() => null);
  assert.ok(module, 'Admin form validator must exist');
  const { validateAccount } = module;
  assert.deepEqual(validateAccount(' An ', 'AN@example.test', ' password12345 ', 'user'), {});
  assert.deepEqual(validateAccount('An', 'an@example.test', '😀'.repeat(12), 'admin'), {});
  for (const [name, email, password, role, field, key] of [
    ['', 'an@example.test', 'password12345', 'user', 'display_name', 'auth.errors.required'],
    [
      'a'.repeat(256),
      'an@example.test',
      'password12345',
      'user',
      'display_name',
      'auth.errors.nameLength',
    ],
    ['An', 'bad', 'password12345', 'user', 'email', 'auth.errors.invalidEmail'],
    ['An', 'an@example.test', 'short', 'user', 'password', 'auth.errors.passwordLength'],
    ['An', 'an@example.test', '😀'.repeat(129), 'user', 'password', 'auth.errors.passwordLength'],
    ['An', 'an@example.test', 'password12345', 'owner', 'system_role', 'auth.errors.invalid'],
  ])
    assert.equal(validateAccount(name, email, password, role)[field].key, key);
});

test('admin form renders identity, one new password, default user and inline admin explanation', async () => {
  const server = await createServer({
    root: fileURLToPath(new URL('../', import.meta.url)),
    cacheDir: fileURLToPath(new URL('../dist/.admin-test-cache', import.meta.url)),
    configFile: false,
    plugins: [svelte()],
    server: { middlewareMode: true },
    appType: 'custom',
  });
  try {
    const { default: Form } = await server.ssrLoadModule(
      '/src/lib/features/admin/CreateAccountForm.svelte',
    );
    const { render } = await server.ssrLoadModule('svelte/server');
    const { initI18n } = await server.ssrLoadModule('/src/lib/i18n/index.ts');
    await initI18n();
    const html = render(Form, {
      props: {
        busy: false,
        uncertain: false,
        fieldErrors: {},
        oncreate: async () => false,
        oncancel() {},
      },
    }).body;
    assert.match(html, /name="display_name"/);
    assert.match(html, /name="email"/);
    assert.equal((html.match(/autocomplete="new-password"/g) ?? []).length, 1);
    assert.doesNotMatch(html, /password_confirmation/);
    assert.match(html, /<option[^>]*value="user"[^>]*selected/);
    assert.match(html, /aria-describedby="admin-role-help"/);
    const locked = render(Form, {
      props: {
        busy: true,
        uncertain: false,
        fieldErrors: {},
        oncreate: async () => false,
        oncancel() {},
      },
    }).body;
    assert.match(locked, /<fieldset[^>]*disabled/);
    assert.match(locked, /aria-busy="true"/);
  } finally {
    await server.close();
  }
});

test(
  'rendered admin page clears passwords, restores focus, locks submit and verifies uncertain outcomes',
  { skip: !process.env.RUVIE_PLAYWRIGHT_PATH },
  async () => {
    const server = await createServer({
      root: fileURLToPath(new URL('../', import.meta.url)),
      cacheDir: fileURLToPath(new URL('../dist/.admin-test-cache', import.meta.url)),
      configFile: false,
      plugins: [
        svelte(),
        {
          name: 'admin-test-entry',
          resolveId(id) {
            if (id === '/__admin_entry.js') return '\0admin-test-entry';
          },
          load(id) {
            if (id === '\0admin-test-entry')
              return `
        import { mount, unmount } from 'svelte';
        import { initI18n } from '/src/lib/i18n/index.ts';
        import Page from '/src/lib/pages/AdminPage.svelte';
        import '/src/styles/base.css';
        await initI18n();
        const page = mount(Page, { target: document.getElementById('app'), props: { csrfToken:'actor', onexpired(){}, onforbidden(){} } });
        window.disposeAdmin = () => unmount(page);
      `;
          },
        },
      ],
      optimizeDeps: { noDiscovery: true, include: [] },
      server: { host: '127.0.0.1', port: 0 },
      appType: 'custom',
    });
    server.middlewares.use('/__admin_test', (_req, res) => {
      res.setHeader('Content-Type', 'text/html');
      res.end(
        `<html lang="vi"><head><meta name="viewport" content="width=device-width, initial-scale=1"></head><body><div id="app"></div><script type="module" src="/__admin_entry.js"></script></body></html>`,
      );
    });
    let browser;
    try {
      await server.listen();
      const { chromium } = createRequire(import.meta.url)(process.env.RUVIE_PLAYWRIGHT_PATH);
      browser = await chromium.launch({
        executablePath: process.env.RUVIE_BROWSER_PATH,
        headless: true,
      });
      const page = await browser.newPage({ locale: 'vi-VN' });
      page.setDefaultTimeout(8000);
      const errors = [];
      page.on('pageerror', (error) => errors.push(error.message));
      const account = {
        id: 'new',
        display_name: 'An',
        email: 'an@example.test',
        system_role: 'admin',
        is_active: true,
        created_at: '2026-10-23T12:00:00Z',
      };
      let mode = 'reject',
        release,
        posted = 0;
      await page.route('**/admin/users**', async (route) => {
        if (route.request().method() === 'GET') {
          await route.fulfill({ json: { users: [account] } });
          return;
        }
        posted++;
        if (mode === 'lost') {
          await route.abort();
          return;
        }
        if (mode === 'slow')
          await new Promise((resolve) => {
            release = resolve;
          });
        await route.fulfill(
          mode === 'reject'
            ? {
                status: 422,
                json: {
                  detail: { code: 'validation_error', fields: { password: 'password_length' } },
                },
              }
            : { status: 201, json: { user: account } },
        );
      });
      await page.goto(`http://127.0.0.1:${server.httpServer.address().port}/__admin_test`);
      const open = page.locator('.accounts-panel > header button');
      try {
        await open.click();
      } catch (error) {
        throw new Error(JSON.stringify(errors), { cause: error });
      }
      const form = page.getByRole('form');
      await form.waitFor();
      const dialog = page.getByRole('dialog', { name: 'Tạo tài khoản', exact: true });
      assert.equal(await dialog.count(), 1, 'Create account opens a modal');
      assert.equal(await dialog.evaluate((el) => el.matches(':modal')), true);
      assert.equal(await page.evaluate(() => document.body.style.overflow), 'hidden');
      assert.equal(await dialog.getByRole('heading', { name: 'Tạo tài khoản' }).count(), 1);
      const backdrop = await dialog.evaluate(
        (el) => getComputedStyle(el, '::backdrop').backgroundColor,
      );
      assert.ok(Number(backdrop.match(/[\d.]+/g).at(-1)) >= 0.7, 'modal dims the background');
      await dialog.getByRole('button', { name: 'Đóng', exact: true }).focus();
      await page.keyboard.press('Shift+Tab');
      assert.equal(
        await form
          .getByRole('button', { name: 'Tạo tài khoản', exact: true })
          .evaluate((el) => el === document.activeElement),
        true,
        'focus stays in the modal',
      );
      await page.keyboard.press('Escape');
      await dialog.waitFor({ state: 'detached' });
      assert.equal(await open.evaluate((el) => el === document.activeElement), true);
      await open.click();
      await form.getByRole('button', { name: 'Tạo tài khoản', exact: true }).click();
      assert.equal(
        await page.locator('#admin-name').evaluate((el) => el === document.activeElement),
        true,
      );
      await page.locator('#admin-name').fill('An');
      await page.locator('#admin-email').fill('an@example.test');
      await form.getByRole('button', { name: 'Tạo tài khoản', exact: true }).click();
      assert.equal(
        await page.locator('#admin-password').evaluate((el) => el === document.activeElement),
        true,
      );
      await page.locator('#admin-password').fill('password12345');
      await page.locator('#admin-role').selectOption('admin');
      await page.screenshot({
        path: fileURLToPath(new URL('../../logs/admin-task007.png', import.meta.url)),
        fullPage: true,
      });
      await form.getByRole('button', { name: 'Tạo tài khoản', exact: true }).click();
      await page.waitForFunction(
        () =>
          document.querySelector('#admin-password')?.value === '' &&
          document.querySelector('#admin-password-error'),
      );
      assert.equal(
        await page.locator('#admin-password').evaluate((el) => el === document.activeElement),
        true,
      );
      assert.equal(await page.locator('#admin-email').inputValue(), 'an@example.test');
      assert.equal(await page.locator('#admin-role').inputValue(), 'admin');
      mode = 'slow';
      await page.locator('#admin-password').fill('password12345');
      await form.getByRole('button', { name: 'Tạo tài khoản', exact: true }).click();
      await page.waitForFunction(() => document.querySelector('fieldset')?.disabled);
      await page.keyboard.press('Escape');
      assert.equal(await form.count(), 1);
      assert.equal(
        await dialog.getByRole('button', { name: 'Đóng', exact: true }).isDisabled(),
        true,
      );
      assert.equal(await form.getByRole('button', { name: 'Hủy', exact: true }).isDisabled(), true);
      while (!release) await new Promise((resolve) => setTimeout(resolve, 10));
      release();
      await page.getByRole('heading', { name: 'Đã tạo tài khoản', exact: true }).waitFor();
      assert.equal(await form.count(), 0);
      assert.equal(await open.evaluate((el) => el === document.activeElement), true);
      await open.click();
      assert.equal(await page.locator('#admin-name').inputValue(), '');
      assert.equal(await page.locator('#admin-role').inputValue(), 'user');
      mode = 'lost';
      await page.locator('#admin-name').fill('An');
      await page.locator('#admin-email').fill('an@example.test');
      await page.locator('#admin-password').fill('password12345');
      await form.getByRole('button', { name: 'Tạo tài khoản', exact: true }).click();
      await page.getByText('Chưa xác định được kết quả tạo tài khoản.', { exact: false }).waitFor();
      assert.equal(await page.locator('#admin-password').inputValue(), '');
      assert.equal(posted, 3);
      await page.getByRole('button', { name: 'Kiểm tra email đã gửi', exact: true }).click();
      await page.getByRole('heading', { name: 'Tài khoản hiện có để đối chiếu' }).waitFor();
      assert.equal(
        await form.getByRole('button', { name: 'Tạo tài khoản', exact: true }).isDisabled(),
        true,
      );
      await form.getByRole('button', { name: 'Hủy', exact: true }).click();
      await open.click();
      await page.locator('#admin-password').fill('never-store-this');
      await page.evaluate(() => window.disposeAdmin());
      assert.equal(await page.locator('input[type=password]').count(), 0);
      assert.equal(
        await page.evaluate(() =>
          JSON.stringify({ ...localStorage, ...sessionStorage }).includes('never-store-this'),
        ),
        false,
      );
      assert.deepEqual(errors, []);
    } finally {
      await browser?.close();
      await server.close();
    }
  },
);
