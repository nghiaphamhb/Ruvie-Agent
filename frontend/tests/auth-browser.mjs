import { logoutFromMenu } from './workspace-actions.mjs';
/** F009 rendered interaction/layout checks use fake API responses, never application data. */
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { readFile, mkdir } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.RUVIE_PLAYWRIGHT_PATH || 'playwright');
const root = path.resolve(fileURLToPath(new URL('../dist/', import.meta.url)));
const types = {
  '.js': 'text/javascript',
  '.css': 'text/css',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
};
const server = createServer(async (req, res) => {
  const target = path.resolve(
    root,
    '.' + new URL(req.url, 'http://localhost').pathname.replace(/\/$/, '/index.html'),
  );
  if (!target.startsWith(root + path.sep)) {
    res.writeHead(403).end();
    return;
  }
  try {
    res.setHeader('Content-Type', types[path.extname(target)] || 'text/html');
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
  const page = await browser.newPage({ viewport: { width: 1366, height: 768 }, locale: 'vi-VN' });
  const exceptions = [];
  page.on('pageerror', (e) => exceptions.push(e.message));
  let current = null,
    status = 201,
    loginStatus = 200,
    release,
    slow = false,
    calls = 0,
    submitted;
  await page.route('**/*', async (route) => {
    const api = new URL(route.request().url()).pathname;
    const json = (data, code = 200) =>
      route.fulfill({ status: code, contentType: 'application/json', body: JSON.stringify(data) });
    if (api === '/auth/session') return json(current || {}, current ? 200 : 401);
    if (api === '/auth/register') {
      calls++;
      submitted = route.request().postDataJSON();
      if (slow)
        await new Promise((resolve) => {
          release = resolve;
        });
      if (status === 409)
        return json({ detail: { code: 'email_taken', fields: { email: 'email_taken' } } }, 409);
      if (status === 422)
        return json(
          { detail: { code: 'validation_error', fields: { password: 'password_length' } } },
          422,
        );
      if (status === 500) return json({ detail: 'private SQL/password detail' }, 500);
      current = { user: { id: 'new', display_name: 'Nguyễn An' }, csrf_token: 'csrf' };
      return json(current, 201);
    }
    if (api === '/auth/login') {
      if (loginStatus !== 200) return json({ detail: 'private login details' }, loginStatus);
      current = { user: { id: 'new', display_name: 'Nguyễn An' }, csrf_token: 'csrf' };
      return json(current);
    }
    if (api === '/auth/logout') {
      current = null;
      return route.fulfill({ status: 204 });
    }
    if (api === '/projects') return json({ items: [] });
    return route.continue();
  });
  await page.setViewportSize({ width: 1280, height: 605 });
  await page.goto(origin + '/?form=register');
  await page.locator('form').waitFor();
  const stage = await page.locator('.auth-stage').boundingBox();
  assert.ok(
    stage.y >= 0 && stage.y + stage.height <= 605,
    'whole stage fits at 100% zoom on a low laptop viewport',
  );
  await page.setViewportSize({ width: 1366, height: 768 });
  await page.goto(origin);
  await page.waitForFunction(() => document.querySelector('[data-slot="inner-curl"]')?.complete);
  const artColor = await page.locator('[data-slot="inner-curl"]').evaluate((image) => {
    const canvas = document.createElement('canvas');
    canvas.width = image.naturalWidth;
    canvas.height = image.naturalHeight;
    const context = canvas.getContext('2d');
    context.drawImage(image, 0, 0);
    const pixels = context.getImageData(0, 0, canvas.width, canvas.height).data;
    let red = 0,
      blue = 0;
    for (let i = 0; i < pixels.length; i += 4) {
      red += pixels[i] * pixels[i + 3];
      blue += pixels[i + 2] * pixels[i + 3];
    }
    return { red, blue };
  });
  assert.ok(
    artColor.blue > artColor.red * 1.3,
    'decorative artwork must retain the blue Figma appearance',
  );
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).waitFor();
  await page.getByRole('link', { name: 'Tạo tài khoản', exact: true }).click();
  await page.getByLabel('Tên hiển thị', { exact: true }).waitFor();
  assert.equal(new URL(page.url()).searchParams.get('form'), 'register');
  await page.getByRole('button', { name: 'Tạo tài khoản', exact: true }).click();
  assert.equal(calls, 0);
  assert.equal(await page.evaluate(() => document.activeElement.id), 'display_name');
  const name = page.getByLabel('Tên hiển thị', { exact: true }),
    email = page.getByLabel('Email', { exact: true });
  const password = page.getByLabel('Mật khẩu', { exact: true });
  const confirmation = page.getByLabel('Nhập lại mật khẩu', { exact: true });
  await name.fill('Nguyễn An');
  await email.fill('an@example.test');
  await password.fill('🔒'.repeat(12));
  await confirmation.fill('🔒'.repeat(12));
  await page.getByRole('button', { name: 'Hiện mật khẩu', exact: true }).click();
  assert.equal(await password.getAttribute('type'), 'text');
  await page.getByRole('link', { name: 'Đăng nhập', exact: true }).click();
  assert.equal(await password.inputValue(), '');
  await page.goBack();
  await name.waitFor();
  assert.equal(await password.inputValue(), '');
  assert.equal(await password.getAttribute('type'), 'password');
  assert.equal(await confirmation.inputValue(), '');
  assert.equal(await confirmation.getAttribute('type'), 'password');
  await page.goForward();
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).waitFor();
  await page.goBack();
  await name.waitFor();
  checks += 6;
  await name.fill('Nguyễn An');
  await email.fill('an@example.test');
  await password.fill('registered-password');
  await confirmation.fill('registered-password');
  await confirmation.fill('different-password');
  const beforeMismatch = calls;
  await page.getByRole('button', { name: 'Tạo tài khoản', exact: true }).click();
  await page.getByText('Mật khẩu nhập lại chưa khớp.', { exact: true }).waitFor();
  assert.equal(calls, beforeMismatch, 'mismatched confirmation must never call the API');
  assert.equal(await page.evaluate(() => document.activeElement.id), 'password_confirmation');
  await page.getByRole('button', { name: 'Hiện mật khẩu nhập lại', exact: true }).click();
  assert.equal(await confirmation.getAttribute('type'), 'text');
  assert.equal(
    await password.getAttribute('type'),
    'password',
    'password visibility is independent',
  );
  await confirmation.fill('registered-password');
  checks += 3;
  status = 409;
  await page.getByRole('button', { name: 'Tạo tài khoản', exact: true }).click();
  await page
    .getByText('Email này đã có tài khoản. Hãy đăng nhập.', { exact: true })
    .first()
    .waitFor();
  assert.equal(await page.evaluate(() => document.activeElement.id), 'email');
  for (const locale of ['en-US', 'ru-RU', 'vi-VN']) {
    await page.locator('#login-language').selectOption(locale);
    await page.waitForFunction((language) => document.documentElement.lang === language, locale);
    assert.equal(await page.getByText('auth.errors.emailTaken', { exact: true }).count(), 0);
  }
  status = 422;
  await password.fill('registered-password-new');
  await confirmation.fill('registered-password-new');
  await page.getByRole('button', { name: 'Tạo tài khoản', exact: true }).click();
  await page.getByText('Mật khẩu phải có 12–128 ký tự.', { exact: true }).waitFor();
  assert.equal(await page.evaluate(() => document.activeElement.id), 'password');
  checks++;
  status = 500;
  await password.fill('registered-password-newer');
  await confirmation.fill('registered-password-newer');
  await page.getByRole('button', { name: 'Tạo tài khoản', exact: true }).click();
  await page.getByText('Không thể tạo tài khoản. Vui lòng thử lại.', { exact: true }).waitFor();
  assert.equal((await page.locator('body').innerText()).includes('private SQL'), false);
  assert.equal(
    await page.locator('[data-sonner-toast][data-type="error"]').count(),
    1,
    'server errors appear in the reference toast layer',
  );
  assert.equal(
    await page.locator('.auth-form-error').count(),
    0,
    'server errors no longer resize the form',
  );
  checks += 2;
  status = 201;
  slow = true;
  await password.fill(' registered-password ');
  await confirmation.fill(' registered-password ');
  await page.getByRole('button', { name: 'Tạo tài khoản', exact: true }).click();
  await page.waitForFunction(
    () => document.querySelector('form')?.getAttribute('aria-busy') === 'true',
  );
  assert.equal(
    await page.getByRole('button', { name: 'Đang tạo tài khoản…', exact: true }).isDisabled(),
    true,
  );
  assert.equal(
    await page.getByRole('link', { name: 'Đăng nhập', exact: true }).getAttribute('aria-disabled'),
    'true',
  );
  const before = calls;
  await page.locator('form').press('Enter');
  assert.equal(calls, before);
  release();
  slow = false;
  await page.getByRole('navigation', { name: 'Điều hướng chính' }).waitFor();
  await page
    .locator('[data-sonner-toast][data-type="success"]')
    .getByText('Tạo tài khoản thành công.', { exact: true })
    .waitFor();
  checks++;
  assert.equal(submitted.password, ' registered-password ');
  assert.deepEqual(Object.keys(submitted).sort(), ['display_name', 'email', 'password']);
  assert.equal(new URL(page.url()).searchParams.has('form'), false);
  await page.reload();
  await page.getByRole('navigation', { name: 'Điều hướng chính' }).waitFor();
  await logoutFromMenu(page);
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).waitFor();
  checks += 7;
  const dropdown = page.getByRole('combobox', { name: 'Ngôn ngữ', exact: true });
  assert.ok((await dropdown.boundingBox()).height <= 44.1, 'single compact dropdown');
  assert.equal(
    await page
      .locator('label[for="login-language"]')
      .evaluate((el) => getComputedStyle(el).clipPath),
    'inset(50%)',
  );
  const border = await page.locator('.auth-card').evaluate((el) => ({
    width: parseFloat(getComputedStyle(el).borderTopWidth),
    color: getComputedStyle(el).borderTopColor,
  }));
  assert.ok(
    border.width <= 1 && Number(border.color.match(/[\d.]+/g)[3]) <= 0.2,
    'glass border is thin and subtle',
  );
  checks += 2;
  const sizes = [
    { width: 1920, height: 1080 },
    { width: 1366, height: 768 },
    { width: 1526, height: 702 },
    { width: 1280, height: 720 },
    { width: 1280, height: 605 },
    { width: 1366, height: 650 },
    { width: 1024, height: 600 },
    { width: 768, height: 1024 },
    { width: 375, height: 812 },
    { width: 320, height: 568 },
    { width: 640, height: 360 },
  ];
  await mkdir(fileURLToPath(new URL('../../logs/f009/', import.meta.url)), { recursive: true });
  for (const size of sizes) {
    await page.setViewportSize(size);
    for (const mode of ['login', 'register']) {
      await page.goto(origin + '/?form=' + mode);
      await page.locator('form').waitFor();
      assert.equal(await page.locator('#password-hint').count(), 0, 'password hint removed');
      assert.ok(
        (await page
          .locator('.auth-submit')
          .evaluate((el) => parseFloat(getComputedStyle(el).marginTop))) >= 16,
        'extra spacing above submit',
      );
      assert.equal(
        await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1),
        true,
        `no horizontal overflow at ${size.width} ${mode}`,
      );
      for (const el of await page.locator('input,.auth-submit,.password-toggle').all())
        assert.ok((await el.boundingBox()).height >= 43.9, 'controls are at least 44 px');
      await page.waitForFunction(() =>
        [...document.querySelectorAll('.auth-page img')].every((i) => i.complete),
      );
      assert.equal(
        await page
          .locator('.auth-page img')
          .evaluateAll((images) => images.every((i) => i.naturalWidth > 0)),
        true,
        'static assets loaded',
      );
      if (size.width >= 1024 && size.height >= 600) {
        const card = await page.locator('.auth-card').boundingBox();
        const frame = await page.locator('.auth-stage').boundingBox();
        assert.ok(
          frame.y >= 0 && frame.y + frame.height <= size.height,
          'entire decorative frame fits',
        );
        assert.ok(
          card.y >= 0 && card.y + card.height <= size.height,
          `whole ${mode} card fits at 100% zoom in ${size.width}x${size.height}`,
        );
        assert.equal(
          await page.evaluate(() => document.documentElement.scrollHeight <= innerHeight + 1),
          true,
          'normal desktop layout needs no vertical scrolling',
        );
      }
      const frameBox = await page.locator('.auth-stage').boundingBox();
      const artBox = await page.locator('.inner-art').boundingBox();
      assert.ok(
        artBox.y <= frameBox.y + 0.5 &&
          artBox.y + artBox.height >= frameBox.y + frameBox.height - 0.5,
        'gradient canvas covers the frame without dark bands',
      );
      await page.locator('.auth-submit').scrollIntoViewIfNeeded();
      assert.equal(await page.locator('.auth-submit').isVisible(), true);
      checks++;
      if ([1920, 1526, 1280, 375, 320].includes(size.width))
        await page.screenshot({
          path: fileURLToPath(
            new URL(`../../logs/f009/${mode}-${size.width}.png`, import.meta.url),
          ),
          fullPage: true,
        });
    }
  }

  await page.setViewportSize({ width: 1526, height: 702 });
  for (const locale of ['vi-VN', 'en-US', 'ru-RU']) {
    await page.goto(origin + '/?form=register');
    await page.locator('form').waitFor();
    await page.locator('#login-language').selectOption(locale);
    await page.waitForFunction((language) => document.documentElement.lang === language, locale);
    const card = await page.locator('.auth-card').boundingBox();
    assert.ok(card.y >= 0 && card.y + card.height <= 702, `registration fits desktop in ${locale}`);
    checks++;
  }

  // Russian text and 200% zoom use the actual browser, not source-string comparisons.
  await page.setViewportSize({ width: 320, height: 568 });
  for (const locale of ['vi-VN', 'en-US', 'ru-RU']) {
    await page.goto(origin + '/?form=register');
    await page.locator('#login-language').selectOption(locale);
    await page.waitForFunction((language) => document.documentElement.lang === language, locale);
    assert.equal(
      await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1),
      true,
    );
    for (const label of await page.locator('.auth-field label,.auth-hint,.auth-switch').all())
      assert.ok((await label.evaluate((el) => parseFloat(getComputedStyle(el).fontSize))) >= 14);
    for (const input of await page.locator('.auth-input').all())
      assert.ok((await input.evaluate((el) => parseFloat(getComputedStyle(el).fontSize))) >= 16);
    await page
      .getByLabel(
        locale === 'vi-VN'
          ? 'Tên hiển thị'
          : locale === 'en-US'
            ? 'Display name'
            : 'Отображаемое имя',
        { exact: true },
      )
      .focus();
    assert.notEqual(
      await page.locator('#display_name').evaluate((el) => getComputedStyle(el).outlineStyle),
      'none',
    );
    checks++;
  }
  const zoom = await browser.newPage({
    viewport: { width: 640, height: 360 },
    deviceScaleFactor: 2,
    locale: 'vi-VN',
  });
  await zoom.route('**/auth/session', (route) => route.fulfill({ status: 401 }));
  for (const mode of ['login', 'register']) {
    await zoom.goto(origin + '/?form=' + mode);
    await zoom.locator('.auth-form').waitFor();
    assert.equal(await zoom.evaluate(() => devicePixelRatio), 2);
    assert.equal(
      await zoom.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1),
      true,
    );
    await zoom.locator('.auth-submit').scrollIntoViewIfNeeded();
    assert.equal(await zoom.locator('.auth-submit').isVisible(), true);
    checks++;
  }
  await zoom.close();

  await page.goto(origin + '/?form=login');
  await page.locator('.password-toggle img').waitFor();
  await page.waitForFunction(() => document.querySelector('.password-toggle img')?.complete);
  const iconContrast = await page.locator('.password-toggle').evaluate((button) => {
    const image = button.querySelector('img');
    const canvas = document.createElement('canvas');
    canvas.width = image.naturalWidth;
    canvas.height = image.naturalHeight;
    const context = canvas.getContext('2d');
    context.filter = getComputedStyle(image).filter;
    context.drawImage(image, 0, 0);
    const pixels = context.getImageData(0, 0, canvas.width, canvas.height).data;
    const rgb = [0, 0, 0];
    let total = 0;
    for (let i = 0; i < pixels.length; i += 4) {
      total += pixels[i + 3];
      for (let c = 0; c < 3; c++) rgb[c] += pixels[i + c] * pixels[i + 3];
    }
    const paint = getComputedStyle(button)
      .backgroundColor.match(/[\d.]+/g)
      .map(Number);
    const alpha = paint[3] ?? 1;
    const surface = paint.slice(0, 3).map((c) => c * alpha + 255 * (1 - alpha));
    const luminance = (values) =>
      values
        .map((c) => {
          c /= 255;
          return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
        })
        .reduce((sum, c, i) => sum + c * [0.2126, 0.7152, 0.0722][i], 0);
    const opacity = Number(getComputedStyle(image).opacity);
    const a = luminance(rgb.map((c, i) => (c / total) * opacity + surface[i] * (1 - opacity))),
      b = luminance(surface);
    return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
  });
  assert.ok(iconContrast >= 3, 'password visibility icon has perceptible contrast');
  checks++;
  await page.emulateMedia({ reducedMotion: 'reduce' });
  assert.equal(await page.locator('.auth-submit').isVisible(), true);
  // Composite the glass against the brightest reference backdrop to bound label contrast.
  const contrast = await page.locator('.auth-card').evaluate((card) => {
    const bg = getComputedStyle(card)
      .backgroundColor.match(/[\d.]+/g)
      .map(Number);
    const alpha = bg[3] ?? 1;
    const backdrop = [0, 133, 255];
    const rgb = bg.slice(0, 3).map((c, i) => c * alpha + backdrop[i] * (1 - alpha));
    const luminance = (values) =>
      values
        .map((c) => {
          c /= 255;
          return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
        })
        .reduce((sum, c, i) => sum + c * [0.2126, 0.7152, 0.0722][i], 0);
    const surface = luminance(rgb);
    const text = luminance([229, 242, 255]);
    return (text + 0.05) / (surface + 0.05);
  });
  assert.ok(
    (await page
      .locator('.auth-card')
      .evaluate((card) => Number(getComputedStyle(card).backgroundColor.match(/[\d.]+/g)[3]))) <=
      0.45,
    'glass background is more transparent',
  );
  assert.ok(contrast >= 4.5, 'glass keeps text legible against the brightest design background');
  checks++;

  // Activate the compiled fallback rule, so removing it or making it translucent fails this check.
  const fallback = await page.evaluate(() => {
    function find(rules) {
      for (const rule of rules) {
        if (rule.conditionText?.includes('not') && rule.conditionText.includes('backdrop-filter')) {
          const child = [...rule.cssRules].find((item) =>
            item.selectorText?.includes('.auth-card'),
          );
          if (child) return { css: child.cssText, color: child.style.backgroundColor };
        }
        if (rule.cssRules) {
          const found = find([...rule.cssRules]);
          if (found) return found;
        }
      }
      return null;
    }
    for (const sheet of document.styleSheets) {
      const found = find([...sheet.cssRules]);
      if (found) return found;
    }
    return null;
  });
  assert.ok(fallback, 'unsupported-blur fallback rule must exist');
  await page.addStyleTag({
    content: fallback.css + ' .auth-card {backdrop-filter:none !important;}',
  });
  await page.waitForFunction(
    (color) => getComputedStyle(document.querySelector('.auth-card')).backgroundColor === color,
    fallback.color,
    { timeout: 5000 },
  );
  const fallbackPaint = await page.locator('.auth-card').evaluate((card) => {
    const channels = getComputedStyle(card)
      .backgroundColor.match(/[\d.]+/g)
      .map(Number);
    const alpha = channels[3] ?? 1;
    const luminance = channels
      .slice(0, 3)
      .map((c) => {
        c /= 255;
        return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
      })
      .reduce((sum, c, i) => sum + c * [0.2126, 0.7152, 0.0722][i], 0);
    return {
      alpha,
      ratio: (1 + 0.05) / (luminance + 0.05),
      blur: getComputedStyle(card).backdropFilter,
    };
  });
  assert.equal(fallbackPaint.alpha, 1);
  assert.equal(fallbackPaint.blur, 'none');
  assert.ok(fallbackPaint.ratio >= 4.5);
  assert.equal(await page.locator('.auth-submit').isVisible(), true);
  checks++;
  // Server feedback uses the shared root toast; client validation stays beside its field.
  await page.setViewportSize({ width: 1280, height: 605 });
  await page.goto(origin + '/?form=login');
  await page.locator('form').waitFor();
  await page.locator('#login-language').selectOption('vi-VN');
  assert.equal(
    await page.locator('[data-sonner-toast]').count(),
    0,
    'signed-out session is not an error',
  );
  await page.getByLabel('Email', { exact: true }).fill('an@example.test');
  await page.getByLabel('Mật khẩu', { exact: true }).fill('registered-password');
  const heightBefore = (await page.locator('.auth-card').boundingBox()).height;
  loginStatus = 401;
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click();
  const toast = page.locator('[data-sonner-toast]');
  await toast.getByText('Email hoặc mật khẩu không đúng.', { exact: true }).waitFor();
  assert.equal((await page.locator('.auth-card').boundingBox()).height, heightBefore);
  assert.equal((await page.locator('body').innerText()).includes('private login'), false);
  assert.ok((await toast.boundingBox()).y >= 76, 'toast does not overlap the language selector');
  await page.getByRole('button', { name: 'Đóng thông báo', exact: true }).click();
  await page.waitForFunction(() => !document.querySelector('[data-sonner-toast]'));
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click();
  await toast.getByText('Email hoặc mật khẩu không đúng.', { exact: true }).waitFor();
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click();
  assert.equal(await toast.count(), 1, 'repeated failures replace the existing toast');
  await page.locator('#login-language').selectOption('en-US');
  await toast.getByText('Incorrect email or password.', { exact: true }).waitFor();
  assert.equal(await toast.count(), 1, 'locale changes update the existing toast');
  await page.mouse.move(10, 10);
  await page.waitForFunction(() => !document.querySelector('[data-sonner-toast]'), null, {
    timeout: 8000,
  });
  checks += 5;
  await page.setViewportSize({ width: 320, height: 568 });
  await page.locator('#login-language').selectOption('vi-VN');
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click();
  await toast.getByText('Email hoặc mật khẩu không đúng.', { exact: true }).waitFor();
  const box = await toast.boundingBox();
  assert.ok(box.x >= 0 && box.x + box.width <= 320, 'mobile toast fits the viewport');
  await page.screenshot({
    path: fileURLToPath(new URL('../../logs/f009/login-toast-mobile.png', import.meta.url)),
    fullPage: true,
  });
  await page.getByRole('button', { name: 'Đóng thông báo', exact: true }).click();
  await page.waitForFunction(() => !document.querySelector('[data-sonner-toast]'));
  await page.unroute('**/*');
  await page.route('**/auth/session', (route) => route.abort('failed'));
  await page.goto(origin + '/?form=login');
  await toast.getByRole('button', { name: 'Thử lại', exact: true }).waitFor();
  await page.unroute('**/auth/session');
  await page.route('**/auth/session', (route) => route.fulfill({ status: 401 }));
  await toast.getByRole('button', { name: 'Thử lại', exact: true }).click();
  await page.locator('form').waitFor();
  await page.getByRole('button', { name: 'Đóng thông báo', exact: true }).click();
  await page.waitForFunction(() => !document.querySelector('[data-sonner-toast]'));
  checks += 2;

  assert.deepEqual(exceptions, []);
  console.log(`Auth browser: ${checks} checks passed`);
} finally {
  if (browser) await browser.close();
  await new Promise((resolve) => server.close(resolve));
}
