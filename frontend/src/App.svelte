<script lang="ts">
  import {onMount} from 'svelte';
  import {i18n} from './lib/i18n/index.ts';
  import {message as uiMessage,type UiMessage} from './lib/i18n/messages.ts';
  import AuthPage from './lib/features/auth/AuthPage.svelte';
  import AuthToastLayer,{type AuthNotice} from './lib/features/auth/AuthToastLayer.svelte';
  import type {AuthFieldErrors} from './lib/features/auth/auth-form.ts';
  import {AuthApiError,getAuthSession,login,register,logout,type AuthSession,type AuthUser} from './lib/features/auth/auth-api.ts';
  import WorkspacePage from './lib/pages/WorkspacePage.svelte';
  let authLoading = $state(true);
  let authBusy = $state(false);
  let authUser = $state<AuthUser | null>(null);
  let csrfToken = $state('');
  let authError = $state<UiMessage | null>(null);
  let authNotice = $state<AuthNotice|null>(null);
  let nextAuthNoticeId = 1;

  /** Publish only trusted message keys; retain the toast across the auth-to-workspace transition. */
  function notifyAuth(type:'success'|'error',message:UiMessage) {
    authNotice={id:nextAuthNoticeId++,type,message,
      retry:type==='error' && (message.key==='common.errors.network' || message.key==='auth.errors.session')};
  }
  function dismissAuthNotice(id:number) {if(authNotice?.id===id)authNotice=null;}
  let authFieldErrors = $state<AuthFieldErrors>({});
  function clearAuthErrors() {
    authError = null;
    authFieldErrors = {};
  }

  /** Both auth flows accept the existing session shape; project failures stay in the workspace. */
  async function acceptSession(result: AuthSession) {
    authUser = result.user;
    csrfToken = result.csrf_token;
    const url = new URL(window.location.href);
    url.searchParams.delete('form');
    history.replaceState({}, '', url);
  }

  async function checkSession() {
    authLoading = true;
    clearAuthErrors();
    try {
      const current = await getAuthSession();
      authUser = current?.user ?? null;
      csrfToken = current?.csrf_token ?? '';
      if (current) await acceptSession(current);
    } catch (error) {
      authError = error instanceof AuthApiError ? error.uiMessage : uiMessage('auth.errors.session');
      notifyAuth('error',authError);
    } finally {
      authLoading = false;
    }
  }
  onMount(() => { void checkSession(); });

  /** Authenticate supplied credentials; cookie/CSRF stay in the active API contract. */
  async function submitLogin(email: string, password: string): Promise<boolean> {
    if (authBusy) return false;
    authBusy = true;
    clearAuthErrors();
    try {
      await acceptSession(await login(email.trim(), password));
      notifyAuth('success',uiMessage('auth.signedIn'));
      return Boolean(authUser);
    } catch (error) {
      authError = error instanceof AuthApiError ? error.uiMessage : uiMessage('auth.errors.login');
      notifyAuth('error',authError);
      return false;
    } finally {
      authBusy = false;
    }
  }

  /** Register once; only the server assigns account identity and document access. */
  async function submitRegister(name: string, email: string, password: string): Promise<boolean> {
    if (authBusy) return false;
    authBusy = true;
    clearAuthErrors();
    try {
      await acceptSession(await register(name, email, password));
      notifyAuth('success',uiMessage('auth.registered'));
      return Boolean(authUser);
    } catch (error) {
      authError = error instanceof AuthApiError ? error.uiMessage : uiMessage('auth.errors.registrationFailed');
      authFieldErrors = error instanceof AuthApiError ? error.fieldErrors : {};
      notifyAuth('error',Object.values(authFieldErrors)[0] ?? authError);
      return false;
    } finally {
      authBusy = false;
    }
  }

  /** Unmount the keyed workspace so no account's requests, files or key drafts survive logout. */
  function clearSession() {
    authUser=null;
    csrfToken='';
    authFieldErrors={};
    const url=new URL(window.location.href);
    url.searchParams.set('form','login');
    history.replaceState({},'',url);
  }

  /** End the cookie session; a protected 401 also discards local account data. */
  async function signOut() {
    authBusy = true;
    authError = null;
    try {
      await logout(csrfToken);
      clearSession();
    } catch (error) {
      if (error instanceof AuthApiError && error.status === 401) {clearSession(); return;}
      authError = error instanceof AuthApiError ? error.uiMessage : uiMessage('auth.errors.logout');
    } finally {
      authBusy = false;
    }
  }

</script>

<svelte:head>
  <title>{$i18n.t('page.title')}</title>
  <meta name="description" content={$i18n.t('page.description')} />
</svelte:head>
<div class="app-shell">
  {#if authLoading || !authUser}
    <AuthPage busy={authBusy} checking={authLoading} fieldErrors={authFieldErrors}
      onlogin={submitLogin} onregister={submitRegister} onerrorclear={clearAuthErrors}/>
  {:else}
    {#key authUser.id+csrfToken}
      <WorkspacePage {authUser} {csrfToken} {authBusy} {authError} onlogout={signOut} onexpired={clearSession}/>
    {/key}
  {/if}
</div>
<AuthToastLayer notice={authNotice} ondismiss={dismissAuthNotice} onretry={()=>{void checkSession();}}/>
