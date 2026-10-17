<script lang="ts">
  import { onDestroy, tick } from 'svelte';
  import { i18n } from '../../i18n/index.ts';
  import { validateLogin, type AuthFieldErrors } from './auth-form.ts';
  import PasswordField from './PasswordField.svelte';
  let { busy, email = $bindable(''), onlogin, onerrorclear }: {
    busy:boolean; email?:string;
    onlogin:(email:string,password:string)=>Promise<boolean>; onerrorclear:()=>void;
  } = $props();
  let password=$state('');
  let fields=$state<AuthFieldErrors>({});
  onDestroy(()=>{password='';});
  function clearErrors() { fields={}; onerrorclear(); }
  async function submit(event:SubmitEvent) {
    event.preventDefault();
    if (busy) return;
    onerrorclear();
    fields=validateLogin(email,password);
    const first=Object.keys(fields)[0];
    if (first) { await tick(); document.getElementById(first)?.focus(); return; }
    if (await onlogin(email.trim(),password)) password='';
  }
</script>

<form class="auth-form" aria-busy={busy} novalidate onsubmit={submit} oninput={clearErrors}>
  <h1>{$i18n.t('auth.login')}</h1>
  <fieldset disabled={busy}>
    <div class="auth-field">
      <label for="email">{$i18n.t('auth.email')}</label>
      <input id="email" name="email" class="auth-input" type="email" autocomplete="username"
        required maxlength="320" bind:value={email} aria-invalid={Boolean(fields.email)}
        aria-describedby={fields.email ? 'email-error' : undefined} />
      {#if fields.email}<p id="email-error" class="field-error" role="alert">{$i18n.message(fields.email)}</p>{/if}
    </div>
    <div class="auth-field">
      <label for="password">{$i18n.t('auth.password')}</label>
      <PasswordField bind:value={password} disabled={busy} invalid={Boolean(fields.password)}
        describedby={fields.password ? 'password-error' : undefined} />
      {#if fields.password}<p id="password-error" class="field-error" role="alert">{$i18n.message(fields.password)}</p>{/if}
    </div>
    <button class="auth-submit" type="submit">{busy ? $i18n.t('auth.signingIn') : $i18n.t('auth.login')}</button>
  </fieldset>
</form>
