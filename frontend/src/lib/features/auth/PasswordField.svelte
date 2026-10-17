<script lang="ts">
  import { onDestroy } from 'svelte';
  import { i18n } from '../../i18n/index.ts';
  import eyeHide from '../../assets/auth/eye-hide.svg';
  let { id = 'password', value = $bindable(''), disabled = false, invalid = false, describedby,
        autocomplete = 'current-password' }: {
    id?: string; value?: string; disabled?: boolean; invalid?: boolean; describedby?: string;
    autocomplete?: 'current-password' | 'new-password';
  } = $props();
  // Ported interaction from references/src/lib/components/common/SensitiveInput.svelte.
  let show = $state(false);
  onDestroy(() => { value = ''; show = false; });
</script>

<div class="password-field">
  <input {id} name={id} class="auth-input" type={show ? 'text' : 'password'}
    {autocomplete} required {disabled} bind:value aria-invalid={invalid} aria-describedby={describedby} />
  <button class="password-toggle" type="button" {disabled} aria-pressed={show}
    aria-label={$i18n.t(id === 'password_confirmation' ? (show ? 'auth.hideConfirmPassword' : 'auth.showConfirmPassword') : (show ? 'auth.hidePassword' : 'auth.showPassword'))} onclick={() => { show = !show; }}>
    <img src={eyeHide} alt="" />
  </button>
</div>

<style>
  .password-field { position:relative; }
  input { padding-right:52px !important; }
  .password-toggle { position:absolute; top:0; right:0; width:44px; height:44px; border:0;
    border-radius:5px; background:transparent; display:grid; place-items:center; cursor:pointer; }
  .password-toggle[aria-pressed="true"] { background:rgba(7,59,101,.08); }
  img { max-width:none; filter:brightness(0); opacity:.6; }
  button:disabled { cursor:wait; }
</style>
