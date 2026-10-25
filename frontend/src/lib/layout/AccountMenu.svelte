<script lang="ts">
  import { i18n } from '../i18n/index.ts';
  import WorkspaceIcon from '../shared/WorkspaceIcon.svelte';
  let {
    name,
    busy,
    collapsed,
    onsettings,
    onlogout,
    canAdmin = false,
    onadmin = () => {},
  }: {
    name: string;
    busy: boolean;
    collapsed: boolean;
    onsettings: () => void;
    onlogout: () => void;
    canAdmin?: boolean;
    onadmin?: () => void;
  } = $props();
  let menu: HTMLDivElement;
  let trigger: HTMLButtonElement;
  let open = $state(false);
  let position = $state({ left: 16, bottom: 64, width: 248 });
  let initials = $derived(
    name
      .trim()
      .split(/\s+/)
      .slice(0, 2)
      .map((part) => Array.from(part)[0] ?? '')
      .join('')
      .toUpperCase() || 'R',
  );
  /** Native popover handles outside clicks; position above the account trigger. */
  function toggle() {
    if (open) {
      menu.hidePopover();
      return;
    }
    const box = trigger.getBoundingClientRect();
    const width = Math.min(248, innerWidth - 32);
    position = {
      left: Math.max(16, Math.min(box.left, innerWidth - width - 16)),
      bottom: innerHeight - box.top + 8,
      width,
    };
    menu.showPopover();
    menu.querySelector<HTMLButtonElement>('button')?.focus();
  }
  function close() {
    menu.hidePopover();
    trigger.focus();
  }
  /** Light dismiss returns focus unless the click already focused another control. */
  function toggled(event: ToggleEvent) {
    open = event.newState === 'open';
    const focused = document.activeElement;
    if (
      !open &&
      trigger.isConnected &&
      (focused === document.body || focused?.id === 'workspace-main' || menu.contains(focused))
    )
      trigger.focus();
  }
  function keydown(event: KeyboardEvent) {
    if (event.key === 'Escape') {
      event.preventDefault();
      close();
    }
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault();
      const buttons = [...menu.querySelectorAll<HTMLButtonElement>('button')];
      const index = buttons.indexOf(document.activeElement as HTMLButtonElement);
      buttons[
        (index + (event.key === 'ArrowDown' ? 1 : -1) + buttons.length) % buttons.length
      ]?.focus();
    }
  }
</script>

<button
  class="account-trigger"
  class:account-collapsed={collapsed}
  bind:this={trigger}
  type="button"
  aria-label={$i18n.t('workspace.account', { name })}
  aria-haspopup="menu"
  aria-expanded={open}
  aria-controls="account-menu"
  onclick={toggle}
>
  <span class="account-avatar" aria-hidden="true">{initials}</span><span class="account-name"
    >{name}</span
  >
</button>
<div
  id="account-menu"
  class="account-menu"
  role="menu"
  tabindex="-1"
  popover="auto"
  bind:this={menu}
  ontoggle={toggled}
  style:left={`${position.left}px`}
  style:bottom={`${position.bottom}px`}
  style:width={`${position.width}px`}
  onkeydown={keydown}
>
  {#if canAdmin}
    <button
      class="account-admin"
      type="button"
      role="menuitem"
      disabled={busy}
      onclick={() => {
        close();
        onadmin();
      }}><WorkspaceIcon name="workspace" />{$i18n.t('admin.navigation')}</button
    >
  {/if}
  <button
    class="account-settings"
    type="button"
    role="menuitem"
    onclick={() => {
      close();
      onsettings();
    }}><WorkspaceIcon name="settings" />{$i18n.t('workspace.settings')}</button
  >
  <button
    type="button"
    role="menuitem"
    disabled={busy}
    onclick={() => {
      close();
      onlogout();
    }}><WorkspaceIcon name="logout" />{$i18n.t('auth.logout')}</button
  >
</div>

<style>
  .account-trigger {
    display: flex;
    align-items: center;
    gap: 12px;
    width: 100%;
    min-height: 56px;
    padding: 8px;
    border: 0;
    background: transparent;
    color: var(--ink);
    border-radius: 8px;
    text-align: left;
  }
  .account-avatar {
    display: grid;
    place-items: center;
    flex: none;
    width: 38px;
    height: 38px;
    border-radius: 50%;
    background: #ffb327;
    color: #071a30;
    font-size: 14px;
    font-weight: 600;
  }
  .account-name {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    padding: 0;
    font-weight: 500;
  }
  .account-menu {
    position: fixed;
    inset: auto;
    margin: 0;
    padding: 8px;
    border: 1px solid var(--border);
    border-radius: 8px;
    background: var(--surface);
    color: var(--ink);
    box-shadow: 0 12px 32px #0005;
  }
  .account-menu button {
    display: flex;
    align-items: center;
    gap: 12px;
    min-height: 44px;
    width: 100%;
    padding: 10px 12px;
    border: 0;
    border-radius: 10px;
    background: transparent;
    color: inherit;
    text-align: left;
  }
  button:hover {
    background: var(--soft);
  }
  .account-trigger {
    overflow: hidden;
  }
  .account-name {
    transition:
      opacity 140ms ease,
      transform 200ms ease;
  }
  .account-collapsed .account-name {
    opacity: 0;
    transform: translateX(-6px);
  }
  @media (prefers-reduced-motion: reduce) {
    .account-name {
      transition: none;
    }
  }
</style>
