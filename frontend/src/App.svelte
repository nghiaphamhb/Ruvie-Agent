<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { i18n } from './lib/i18n/index.ts';
  import { message as uiMessage, type UiMessage } from './lib/i18n/messages.ts';
  import AuthPage from './lib/features/auth/AuthPage.svelte';
  import AuthToastLayer, { type AuthNotice } from './lib/features/auth/AuthToastLayer.svelte';
  import type { AuthFieldErrors } from './lib/features/auth/auth-form.ts';
  import {
    AuthApiError,
    getAuthSession,
    getAuthSetup,
    login,
    register,
    logout,
    type AuthSession,
    type AuthUser,
  } from './lib/features/auth/auth-api.ts';
  import WorkspacePage from './lib/pages/WorkspacePage.svelte';
  let authLoading = $state(true);
  let authBusy = $state(false);
  let authUser = $state<AuthUser | null>(null);
  let csrfToken = $state('');
  let authError = $state<UiMessage | null>(null);
  let authNotice = $state<AuthNotice | null>(null);
  let nextAuthNoticeId = 1;
  let requiresInitialAdmin = $state<boolean | null>(null);
  let authReadError = $state<UiMessage | null>(null);
  let checkingSetup = $state(false);
  // Every new auth operation invalidates responses from an earlier session/read.
  let authGeneration = 0;
  onDestroy(() => {
    authGeneration++;
  });

  /** Publish only trusted message keys; retain the toast across the auth-to-workspace transition. */
  function notifyAuth(type: 'success' | 'error', message: UiMessage) {
    authNotice = {
      id: nextAuthNoticeId++,
      type,
      message,
      retry:
        type === 'error' &&
        (message.key === 'common.errors.network' || message.key === 'auth.errors.session'),
    };
  }
  function dismissAuthNotice(id: number) {
    if (authNotice?.id === id) authNotice = null;
  }
  let authFieldErrors = $state<AuthFieldErrors>({});
  function clearAuthErrors() {
    authError = null;
    authFieldErrors = {};
  }

  /** Accept a server-validated session; setup status alone never establishes identity. */
  async function acceptSession(result: AuthSession, initialAdmin = false) {
    authUser = result.user;
    csrfToken = result.csrf_token;
    requiresInitialAdmin = false;
    authReadError = null;
    authLoading = false;
    const url = new URL(window.location.href);
    url.searchParams.delete('form');
    if (initialAdmin) url.searchParams.set('view', 'admin-users');
    history.replaceState({}, '', url);
  }

  async function readSetup(generation: number) {
    authLoading = true;
    checkingSetup = true;
    requiresInitialAdmin = null;
    authReadError = null;
    try {
      const setup = await getAuthSetup();
      if (generation === authGeneration) requiresInitialAdmin = setup.requires_initial_admin;
    } catch {
      if (generation === authGeneration) authReadError = uiMessage('auth.errors.setup');
    } finally {
      if (generation === authGeneration) authLoading = false;
    }
  }

  async function checkSession() {
    if (authBusy) return;
    const generation = ++authGeneration;
    authLoading = true;
    checkingSetup = false;
    authReadError = null;
    clearAuthErrors();
    try {
      const current = await getAuthSession();
      if (generation !== authGeneration) return;
      authUser = current?.user ?? null;
      csrfToken = current?.csrf_token ?? '';
      if (current) await acceptSession(current);
      else await readSetup(generation);
    } catch (error) {
      if (generation !== authGeneration) return;
      authError =
        error instanceof AuthApiError ? error.uiMessage : uiMessage('auth.errors.session');
      authReadError = authError;
      notifyAuth('error', authError);
    } finally {
      if (generation === authGeneration) authLoading = false;
    }
  }
  onMount(() => {
    void checkSession();
  });

  /** Authenticate supplied credentials; cookie/CSRF stay in the active API contract. */
  async function submitLogin(email: string, password: string): Promise<boolean> {
    if (authBusy || authLoading || authReadError) return false;
    const generation = ++authGeneration;
    authBusy = true;
    clearAuthErrors();
    try {
      const result = await login(email.trim(), password);
      if (generation !== authGeneration) return false;
      await acceptSession(result);
      notifyAuth('success', uiMessage('auth.signedIn'));
      return Boolean(authUser);
    } catch (error) {
      if (generation !== authGeneration) return false;
      authError = error instanceof AuthApiError ? error.uiMessage : uiMessage('auth.errors.login');
      notifyAuth('error', authError);
      return false;
    } finally {
      if (generation === authGeneration) authBusy = false;
    }
  }

  /** Register once; only the server assigns account identity and document access. */
  async function submitRegister(name: string, email: string, password: string): Promise<boolean> {
    if (authBusy || authLoading || requiresInitialAdmin !== true) return false;
    const generation = ++authGeneration;
    authBusy = true;
    clearAuthErrors();
    try {
      const result = await register(name, email, password);
      if (generation !== authGeneration) return false;
      await acceptSession(result, true);
      notifyAuth('success', uiMessage('auth.registered'));
      return Boolean(authUser);
    } catch (error) {
      if (generation !== authGeneration) return false;
      authError =
        error instanceof AuthApiError
          ? error.uiMessage
          : uiMessage('auth.errors.registrationFailed');
      authFieldErrors = error instanceof AuthApiError ? error.fieldErrors : {};
      if (error instanceof AuthApiError && error.code === 'setup_already_completed') {
        requiresInitialAdmin = false;
      } else if (
        !(error instanceof AuthApiError) ||
        (![403, 422].includes(error.status ?? 0) && error.code !== 'email_taken')
      ) {
        // A lost response may have committed. Read state once; never repeat the POST or infer identity.
        if (
          !(error instanceof AuthApiError) ||
          error.status === undefined ||
          error.status === 201
        ) {
          authError = uiMessage('auth.errors.setupUnknown');
        }
        notifyAuth('error', authError);
        await readSetup(generation);
        return false;
      }
      notifyAuth('error', Object.values(authFieldErrors)[0] ?? authError);
      return false;
    } finally {
      if (generation === authGeneration) authBusy = false;
    }
  }

  /** Unmount the keyed workspace so no account's requests, files or key drafts survive logout. */
  function clearSession() {
    const generation = ++authGeneration;
    authUser = null;
    csrfToken = '';
    authFieldErrors = {};
    authBusy = false;
    const url = new URL(window.location.href);
    url.searchParams.set('form', 'login');
    url.searchParams.delete('view');
    history.replaceState({}, '', url);
    void readSetup(generation);
  }

  /** Keep an expiry notice in the auth layer after Workspace unmounts. */
  function expireWorkspace(notice?: UiMessage) {
    if (notice) notifyAuth('error', notice);
    clearSession();
  }

  /** End the cookie session; a protected 401 also discards local account data. */
  async function signOut() {
    const generation = ++authGeneration;
    authBusy = true;
    authError = null;
    try {
      await logout(csrfToken);
      if (generation !== authGeneration) return;
      clearSession();
    } catch (error) {
      if (generation !== authGeneration) return;
      if (error instanceof AuthApiError && error.status === 401) {
        clearSession();
        return;
      }
      authError = error instanceof AuthApiError ? error.uiMessage : uiMessage('auth.errors.logout');
    } finally {
      if (generation === authGeneration) authBusy = false;
    }
  }
</script>

<svelte:head>
  <title>{$i18n.t('page.title')}</title>
  <meta name="description" content={$i18n.t('page.description')} />
</svelte:head>
<div class="app-shell">
  {#if authLoading || !authUser}
    <AuthPage
      busy={authBusy}
      checking={authLoading}
      {checkingSetup}
      {requiresInitialAdmin}
      readError={authReadError}
      onretry={() => {
        void checkSession();
      }}
      fieldErrors={authFieldErrors}
      onlogin={submitLogin}
      onregister={submitRegister}
      onerrorclear={clearAuthErrors}
    />
  {:else}
    {#key authUser.id + csrfToken}
      <WorkspacePage
        {authUser}
        {csrfToken}
        {authBusy}
        {authError}
        onlogout={signOut}
        onexpired={expireWorkspace}
      />
    {/key}
  {/if}
</div>
<AuthToastLayer
  notice={authNotice}
  ondismiss={dismissAuthNotice}
  onretry={() => {
    void checkSession();
  }}
/>
