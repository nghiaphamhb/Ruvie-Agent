<script lang="ts">
  import { onMount, tick } from 'svelte';
  import { i18n } from '../../i18n/index.ts';
  import type { AuthFieldErrors } from './auth-form.ts';
  import LanguageSelector from '../../shared/LanguageSelector.svelte';
  import LoginForm from './LoginForm.svelte';
  import RegisterForm from './RegisterForm.svelte';
  import logo from '../../assets/brand/ruvie-logo.png';
  import outerRing from '../../assets/auth/outer-ring.png';
  import outerLeft from '../../assets/auth/outer-left.png';
  import outerRight from '../../assets/auth/outer-right.png';
  import innerRing from '../../assets/auth/inner-ring.png';
  import innerCurl from '../../assets/auth/inner-curl.png';
  import innerLeft from '../../assets/auth/inner-left.png';
  import innerRight from '../../assets/auth/inner-right.png';

  let {
    busy,
    checking,
    fieldErrors,
    onlogin,
    onregister,
    onerrorclear,
  }: {
    busy: boolean;
    checking: boolean;
    fieldErrors: AuthFieldErrors;
    onlogin: (email: string, password: string) => Promise<boolean>;
    onregister: (name: string, email: string, password: string) => Promise<boolean>;
    onerrorclear: () => void;
  } = $props();
  type Mode = 'login' | 'register';
  function readMode(): Mode {
    return new URLSearchParams(window.location.search).get('form') === 'register'
      ? 'register'
      : 'login';
  }
  let mode = $state<Mode>(typeof window === 'undefined' ? 'login' : readMode());
  let email = $state('');
  let stageWidth = $state(1093);
  let stageHeight = $state(614);
  const artScale = $derived(Math.max(stageWidth / 1366, stageHeight / 768));

  /** Adapt chooseAuthMode from the legacy auth page; reset passwords by remounting the form. */
  async function changeMode(next: Mode, push = true) {
    if (busy || checking) return;
    mode = next;
    onerrorclear();
    const url = new URL(window.location.href);
    url.searchParams.set('form', next);
    if (push) history.pushState({}, '', url);
    await tick();
    document.getElementById(next === 'register' ? 'display_name' : 'email')?.focus();
  }
  function followMode(event: MouseEvent, next: Mode) {
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    void changeMode(next);
  }
  onMount(() => {
    function popped() {
      if (busy || checking) {
        const url = new URL(window.location.href);
        url.searchParams.set('form', mode);
        history.replaceState({}, '', url);
        return;
      }
      void changeMode(readMode(), false);
    }
    window.addEventListener('popstate', popped);
    return () => window.removeEventListener('popstate', popped);
  });
</script>

<main class="auth-page">
  <div class="outer-art" aria-hidden="true">
    <img data-slot="outer-ring" src={outerRing} alt="" style="left:641.252px;top:52.778px" />
    <img data-slot="outer-left" src={outerLeft} alt="" style="left:94.14px;top:638.023px" />
    <img data-slot="outer-right" src={outerRight} alt="" style="left:1437.374px;top:792.334px" />
  </div>
  <aside class="auth-language"><LanguageSelector id="login-language" /></aside>
  <section
    class="auth-stage"
    aria-label="Ruvie"
    bind:clientWidth={stageWidth}
    bind:clientHeight={stageHeight}
    style:--art-scale={artScale}
  >
    <div class="inner-art" aria-hidden="true">
      <img data-slot="inner-ring" src={innerRing} alt="" style="left:364.267px;top:0" />
      <img data-slot="inner-curl" src={innerCurl} alt="" style="left:681.577px;top:78.933px" />
      <img data-slot="inner-left" src={innerLeft} alt="" style="left:0;top:482.133px" />
      <img data-slot="inner-right" src={innerRight} alt="" style="left:1160.389px;top:636.444px" />
    </div>
    <div class="auth-card">
      <img class="auth-logo" src={logo} alt="Ruvie" width="140" height="48" />
      {#if checking}
        <p class="auth-checking" aria-live="polite">{$i18n.t('auth.checking')}</p>
      {:else}
        {#key mode}
          {#if mode === 'login'}
            <LoginForm {busy} bind:email {onlogin} {onerrorclear} />
          {:else}
            <RegisterForm {busy} {fieldErrors} bind:email {onregister} {onerrorclear} />
          {/if}
        {/key}
        <p class="auth-switch">
          <span>{$i18n.t(mode === 'login' ? 'auth.noAccount' : 'auth.hasAccount')}</span>
          <a
            href={mode === 'login' ? '/?form=register' : '/?form=login'}
            aria-disabled={busy}
            onclick={(event) => followMode(event, mode === 'login' ? 'register' : 'login')}
          >
            {$i18n.t(mode === 'login' ? 'auth.register' : 'auth.login')}
          </a>
        </p>
      {/if}
    </div>
  </section>
</main>

<style>
  .auth-page {
    --surface: #fff;
    --ink: #073b65;
    --muted: #e5f2ff;
    --border: #c1d1e2;
    --radius: 7px;
    position: relative;
    isolation: isolate;
    flex-shrink: 0;
    width: 100%;
    min-height: 100dvh;
    display: grid;
    place-items: center;
    padding: 64px 24px 12px;
    overflow: hidden;
    color: white;
    background: #003565;
  }
  .outer-art,
  .inner-art {
    position: absolute;
    pointer-events: none;
    width: 1920px;
    height: 1080px;
    left: 50%;
    top: 50%;
    transform: translate(-50%, -50%);
    z-index: -1;
    background: radial-gradient(ellipse 58.43% 103.88% at 56.74% 50%, #0085ff, #003565);
  }
  .outer-art img,
  .inner-art img {
    position: absolute;
    max-width: none;
    transform-origin: 0 0;
  }
  .auth-stage {
    position: relative;
    isolation: isolate;
    width: min(100%, 1093px);
    min-height: min(614px, calc(100dvh - 76px));
    display: grid;
    place-items: center;
    padding: 12px 24px;
    overflow: hidden;
    border-radius: 24px;
    background: #003565;
    box-shadow:
      22px 35px 91px #0000001a,
      89px 139px 165px #00000017;
  }
  /* Scale the artwork with its gradient so the opaque Figma crops retain their colors. */
  .outer-art {
    transform: translate(-50%, -50%) scale(max(calc(100vw / 1920px), calc(100dvh / 1080px)));
  }
  .inner-art {
    width: 1366px;
    height: 768px;
    transform: translate(-50%, -50%) scale(var(--art-scale));
  }
  .auth-card {
    position: relative;
    z-index: 1;
    width: min(100%, 424px);
    padding: 48px 64px;
    border: 1px solid rgba(195, 221, 255, 0.18);
    border-radius: 22px;
    background: rgba(16, 70, 128, 0.4);
    backdrop-filter: blur(9px);
  }
  .auth-logo {
    display: block;
    width: 112px;
    height: auto;
    margin: 0 auto 20px;
    filter: brightness(0) invert(1);
  }
  .auth-language {
    position: absolute;
    z-index: 2;
    top: 16px;
    right: 24px;
    width: 144px;
    max-width: calc(100% - 48px);
  }
  .auth-language :global(label) {
    color: white;
    font-size: 14px;
  }
  .auth-switch {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 4px;
    margin: 18px 0 0;
    font-size: 14px;
    line-height: 1.6;
    text-align: center;
  }
  a {
    color: white;
    font-weight: 650;
    text-underline-offset: 3px;
  }
  a[aria-disabled='true'] {
    cursor: wait;
    opacity: 0.7;
  }
  .auth-checking {
    text-align: center;
    line-height: 1.5;
  }
  .auth-page :global(.auth-form h1) {
    margin: 0 0 16px;
    font-size: 22px;
    line-height: 1.3;
    letter-spacing: -0.02em;
  }
  .auth-page :global(.auth-description) {
    margin: -6px 0 16px;
    line-height: 1.5;
    font-size: 14px;
  }
  .auth-page :global(fieldset) {
    min-width: 0;
    border: 0;
    padding: 0;
    margin: 0;
  }
  .auth-page :global(.auth-field) {
    margin-bottom: 12px;
  }
  .auth-page :global(.auth-field label) {
    display: block;
    margin-bottom: 6px;
    font-size: 14px;
    line-height: 1.5;
  }
  .auth-page :global(.auth-input) {
    width: 100%;
    height: 44px;
    min-width: 0;
    padding: 10px 12px;
    background: white;
    color: #073b65;
    border: 1px solid #bcbec0;
    border-radius: 5px;
    font-size: 16px;
  }
  .auth-page :global(.auth-input[aria-invalid='true']) {
    border: 2px solid #fdb5a9;
  }
  .auth-page :global(.auth-submit) {
    width: 100%;
    min-height: 44px;
    margin-top: 16px;
    padding: 10px 12px;
    border: 0;
    border-radius: 7px;
    background: #003465;
    color: white;
    font-weight: 650;
    font-size: 16px;
    cursor: pointer;
  }
  .auth-page :global(.auth-submit:hover:not(:disabled)) {
    background: #00294f;
  }
  .auth-page :global(.auth-submit:disabled) {
    cursor: wait;
    opacity: 0.75;
  }
  .auth-page :global(.field-error) {
    font-size: 14px;
    color: #fff1ed;
    margin: 7px 0 0;
    line-height: 1.5;
  }
  .auth-page :global(:is(input, button, a, select):focus-visible) {
    outline: 2px solid white;
    outline-offset: 3px;
  }
  .auth-page :global(input:focus-visible) {
    outline: 2px solid #d2ecff;
    outline-offset: 3px;
  }
  @supports not (backdrop-filter: blur(1px)) {
    .auth-card {
      background: #124f91;
    }
  }
  @media (max-width: 800px) {
    .auth-page {
      padding: 72px 16px 16px;
    }
    .auth-stage {
      min-height: 0;
      padding: 16px;
    }
    .auth-card {
      padding: 40px;
    }
    .auth-language {
      right: 16px;
      top: 16px;
    }
  }
  @media (max-height: 740px) and (min-width: 801px) {
    .auth-page {
      padding: 48px 24px 8px;
    }
    .auth-stage {
      min-height: min(614px, calc(100dvh - 56px));
      padding: 8px 16px;
    }
    .auth-card {
      width: min(100%, 416px);
      padding: 24px 56px;
    }
    .auth-logo {
      width: 96px;
      margin-bottom: 12px;
    }
    .auth-switch {
      margin-top: 14px;
      line-height: 1.3;
    }
    .auth-page :global(.auth-form h1) {
      font-size: 20px;
      margin-bottom: 12px;
    }
    .auth-page :global(.auth-field) {
      margin-bottom: 8px;
    }
    .auth-page :global(.auth-field label) {
      margin-bottom: 4px;
      line-height: 1.3;
    }
  }
</style>
