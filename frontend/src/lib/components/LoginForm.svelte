<script lang="ts">
  import { i18n } from '../i18n/index.ts';
  import type { UiMessage } from '../i18n/messages.ts';
  import { onDestroy } from 'svelte';
  let { busy, error, onlogin }: {
    busy: boolean; error: UiMessage | null;
    onlogin: (email: string, password: string) => Promise<boolean>;
  } = $props();
  let email = $state('');
  let password = $state('');
  /** Submit credentials once; App owns the session and safe API error. */
  async function submit(event: SubmitEvent) {
    event.preventDefault();
    if (busy) return;
    if (await onlogin(email.trim(), password)) password = '';
  }
  onDestroy(() => {password = '';});
</script>

<!-- Compact labeled form adapted from references/src/routes/auth/+page.svelte.
     No signup, external auth, or browser token storage. -->
<form class="auth-card" onsubmit={submit} aria-busy={busy}>
  <span class="welcome-mark" aria-hidden="true">R</span>
  <h1>{$i18n.t('auth.login')}</h1>
  <p class="auth-description">{$i18n.t('auth.description')}</p>
  {#if error}<p class="auth-error" role="alert">{$i18n.message(error)}</p>{/if}
  <fieldset disabled={busy}>
    <label for="email">{$i18n.t('auth.email')}</label>
    <input id="email" type="email" autocomplete="username" required maxlength="320" bind:value={email}/>
    <label for="password">{$i18n.t('auth.password')}</label>
    <input id="password" type="password" autocomplete="current-password" required bind:value={password}/>
    <button class="auth-submit" type="submit">{busy ? $i18n.t('auth.signingIn') : $i18n.t('auth.login')}</button>
  </fieldset>
</form>

<style>
  .auth-card { width: min(100%, 420px); padding: 34px; border: 0; border-radius: var(--radius); background: transparent; box-shadow: none; }
  .auth-card .welcome-mark { margin-bottom: 20px; }
  .auth-card h1 { margin: 0; font-size: 30px; letter-spacing: -.03em; }
  .auth-description { color: var(--muted); line-height: 1.55; }
  .auth-card label { display: block; margin: 19px 0 7px; font-size: 13px; font-weight: 650; }
  .auth-card input { width: 100%; min-height: 44px; padding: 10px 12px; border: 1px solid var(--border); border-radius: var(--radius); background: var(--surface); color: var(--ink); }
  .auth-card input:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
  .auth-submit { width: 100%; min-height: 46px; margin-top: 24px; border: 0; border-radius: var(--radius); background: var(--accent); color: white; font-weight: 650; }
  .auth-submit:disabled { opacity: .65; }
  .welcome-mark { margin: 0 auto 20px; }
  h1, .auth-description { text-align: center; }
  fieldset { margin: 0; padding: 0; border: 0; min-width: 0; }
  input { background: var(--surface); border-radius: var(--radius); }
</style>
