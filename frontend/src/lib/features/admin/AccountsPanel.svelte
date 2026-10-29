<script lang="ts">
  import { onDestroy, onMount, tick } from 'svelte';
  import { toast } from 'svelte-sonner';
  import { i18n } from '../../i18n/index.ts';
  import CreateAccountForm from './CreateAccountForm.svelte';
  import EditUserModal from './EditUserModal.svelte';
  import SurfaceDialog from '../../shared/SurfaceDialog.svelte';
  import type { createAdminState } from './admin-state.svelte.ts';
  import type { AccountSummary } from './admin-api.ts';
  import type { AccountInput } from './admin-form.ts';
  let {
    state: adminState,
    active = true,
    actorUserId,
  }: {
    state: ReturnType<typeof createAdminState>;
    active?: boolean;
    actorUserId: string;
  } = $props();
  let opener: HTMLButtonElement;
  let search = $state('');
  let page = $state(1);
  const pageSize = 20;
  let searchTimer: ReturnType<typeof setTimeout>;
  let editing = $state<AccountSummary | null>(null);
  let activityTarget = $state<AccountSummary | null>(null);
  let activityDesired = $state(false);
  let actionTooltip = $state<{ triggerId: string; text: string; left: number; top: number } | null>(
    null,
  );
  /** Position outside the scrolling table so the tooltip is not clipped. */
  function showActionTooltip(event: MouseEvent | FocusEvent, text: string) {
    const bounds = (event.currentTarget as HTMLElement).getBoundingClientRect();
    actionTooltip = {
      triggerId: (event.currentTarget as HTMLElement).id,
      text,
      left: Math.min(window.innerWidth - 140, Math.max(140, bounds.left + bounds.width / 2)),
      top: bounds.top - 8,
    };
  }
  let editOpener: HTMLButtonElement | null = null;
  const displayed = $derived(adminState.created ?? adminState.found);
  const notices = {
    authentication_required: 'admin.errors.authentication_required',
    admin_required: 'admin.errors.admin_required',
    csrf_invalid: 'admin.errors.csrf_invalid',
    origin_not_allowed: 'admin.errors.origin_not_allowed',
    email_taken: 'admin.errors.email_taken',
    validation_error: 'admin.errors.validation_error',
    account_creation_failed: 'admin.errors.account_creation_failed',
    account_lookup_unavailable: 'admin.errors.account_lookup_unavailable',
    account_update_unavailable: 'admin.errors.account_update_unavailable',
    account_not_found: 'admin.errors.account_not_found',
    last_active_admin: 'admin.errors.last_active_admin',
    self_deactivation_forbidden: 'admin.errors.self_deactivation_forbidden',
    account_activity_unavailable: 'admin.errors.account_activity_unavailable',
    unknown: 'admin.errors.unknown',
  } as const;
  onMount(() => void adminState.loadUsers({ q: '', page: 1, page_size: pageSize }));
  onDestroy(() => clearTimeout(searchTimer));
  $effect(() => {
    if (!active) {
      actionTooltip = null;
      activityTarget = null;
      adminState.invalidateActivity();
      toast.dismiss('admin-activity');
    }
  });
  onDestroy(() => {
    adminState.invalidateActivity();
    toast.dismiss('admin-activity');
  });
  async function confirmActivity() {
    const target = activityTarget;
    if (!target || adminState.activityBusy) return;
    const latest = adminState.users.find((user) => user.id === target.id);
    if (!latest || latest.is_active !== target.is_active) {
      activityTarget = null;
      toast.error($i18n.t('admin.activityChanged'), { id: 'admin-activity' });
      return;
    }
    const result = await adminState.changeActivity(target, activityDesired);
    if (!active || activityTarget !== target || result.status === 'ignored') return;
    activityTarget = null;
    if (result.status === 'updated')
      toast.success($i18n.t(activityDesired ? 'admin.activityOpened' : 'admin.activityLocked'), {
        id: 'admin-activity',
      });
    else if (result.status === 'observed')
      toast.info($i18n.t('admin.activityObserved'), { id: 'admin-activity' });
    else if (result.status === 'uncertain')
      toast.error($i18n.t('admin.activityUncertain'), { id: 'admin-activity' });
    else
      toast.error(
        $i18n.t(
          adminState.activityError === 'last_active_admin'
            ? 'admin.activityLastAdmin'
            : notices[adminState.activityError ?? 'unknown'],
        ),
        {
          id: 'admin-activity',
        },
      );
  }
  $effect(() => {
    if (!active) return;
    const query = { q: search, page, page_size: pageSize };
    let timer: ReturnType<typeof setTimeout>;
    let stopped = false;
    let refreshing = false;
    const schedule = () => {
      if (!stopped && !document.hidden) timer = setTimeout(() => void refresh(), 15000);
    };
    async function refresh() {
      clearTimeout(timer);
      if (stopped || document.hidden || refreshing) return;
      refreshing = true;
      try {
        await adminState.loadUsers(query, true);
      } finally {
        refreshing = false;
      }
      schedule();
    }
    const visibilityChanged = () => {
      clearTimeout(timer);
      if (!document.hidden) void refresh();
    };
    document.addEventListener('visibilitychange', visibilityChanged);
    schedule();
    return () => {
      stopped = true;
      clearTimeout(timer);
      document.removeEventListener('visibilitychange', visibilityChanged);
    };
  });
  function lastActiveLabel(userId: string): string {
    const record = adminState.presence[userId];
    if (!record || adminState.presenceStale) return $i18n.t('admin.presenceUnavailable');
    if (record.is_online) return $i18n.t('admin.online');
    if (!record.last_active_at) return $i18n.t('admin.neverActive');
    const seconds = Math.max(
      0,
      (adminState.presenceUpdatedAt - Date.parse(record.last_active_at)) / 1000,
    );
    if (seconds < 60) return $i18n.t('admin.justNow');
    const units = [
      [31536000, 'year'],
      [2592000, 'month'],
      [86400, 'day'],
      [3600, 'hour'],
      [60, 'minute'],
    ] as const;
    const [divisor, unit] = units.find(([divisor]) => seconds >= divisor)!;
    return new Intl.RelativeTimeFormat($i18n.locale, { numeric: 'auto' }).format(
      -Math.floor(seconds / divisor),
      unit,
    );
  }
  function searchChanged(value: string) {
    search = value;
    page = 1;
    clearTimeout(searchTimer);
    searchTimer = setTimeout(
      () => void adminState.loadUsers({ q: search, page, page_size: pageSize }),
      300,
    );
  }
  function goToPage(next: number) {
    page = next;
    void adminState.loadUsers({ q: search, page, page_size: pageSize });
  }
  async function closeEdit() {
    editing = null;
    await tick();
    editOpener?.focus();
  }
  async function restoreFocus() {
    await tick();
    opener?.focus();
  }
  async function create(input: AccountInput) {
    const result = await adminState.create(input);
    if (result) await restoreFocus();
    return result;
  }
  function close() {
    if (adminState.busy) return;
    adminState.close();
    void restoreFocus();
  }
</script>

<svelte:window
  onkeydown={(event) => {
    if (event.key === 'Escape') actionTooltip = null;
  }}
  onresize={() => {
    actionTooltip = null;
  }}
  onscroll={() => {
    actionTooltip = null;
  }}
/>

<section class="accounts-panel" aria-labelledby="admin-users-heading">
  <header>
    <h1 id="admin-users-heading" class="sr-only" data-view-heading tabindex="-1">
      {$i18n.t('admin.users')}
    </h1>
    <label class="user-search">
      <span class="sr-only">{$i18n.t('admin.searchUsers')}</span>
      <input
        type="search"
        placeholder={$i18n.t('admin.searchUsers')}
        value={search}
        oninput={(event) => searchChanged(event.currentTarget.value)}
      />
    </label>
    <button
      bind:this={opener}
      type="button"
      disabled={adminState.formOpen ||
        adminState.busy ||
        Boolean(activityTarget) ||
        Boolean(editing)}
      onclick={adminState.open}>{$i18n.t('admin.create')}</button
    >
  </header>
  {#snippet creationFeedback()}
    {#if adminState.error}<p role="alert">{$i18n.t(notices[adminState.error])}</p>{/if}
    {#if adminState.uncertain}
      <p role="status">
        {$i18n.t('admin.unknown', { email: adminState.sentEmail })}
      </p>
    {/if}
    {#if adminState.sentEmail && !adminState.created}
      <button type="button" disabled={adminState.busy} onclick={() => adminState.lookup()}
        >{$i18n.t(adminState.busy ? 'admin.busy' : 'admin.lookup')}</button
      >
    {/if}
    {#if adminState.lookupDone && !adminState.found}<p role="status">
        {$i18n.t('admin.notFound')}
      </p>{/if}
    {#if displayed}
      <div role="status" class="result">
        <h2>{$i18n.t(adminState.created ? 'admin.created' : 'admin.found')}</h2>
        {#if !adminState.created}<p>
            {$i18n.t('admin.foundHelp')}
          </p>{/if}
        <dl>
          <dt>{$i18n.t('auth.name')}</dt>
          <dd>{displayed.display_name}</dd>
          <dt>{$i18n.t('auth.email')}</dt>
          <dd>{displayed.email}</dd>
          <dt>{$i18n.t('admin.role')}</dt>
          <dd>
            {$i18n.t(displayed.system_role === 'admin' ? 'admin.roleAdmin' : 'admin.roleUser')}
          </dd>
          <dt>{$i18n.t('admin.status')}</dt>
          <dd>{$i18n.t(displayed.is_active ? 'admin.active' : 'admin.inactive')}</dd>
        </dl>
        {#if adminState.created}<p>
            {$i18n.t('admin.handover')}
          </p>{/if}
      </div>
    {/if}
  {/snippet}
  <SurfaceDialog
    open={adminState.formOpen && active}
    title={$i18n.t('admin.create')}
    onclose={close}
    closeDisabled={adminState.busy}
    dismissOnBackdrop
    className="create-account-dialog"
  >
    {#if adminState.formOpen}
      <CreateAccountForm
        embedded
        busy={adminState.busy}
        uncertain={adminState.uncertain || Boolean(adminState.found)}
        fieldErrors={adminState.fieldErrors}
        oncreate={create}
        oncancel={close}
      />
      {@render creationFeedback()}
    {/if}
  </SurfaceDialog>
  {#if !adminState.formOpen}{@render creationFeedback()}{/if}
  <section class="directory" aria-labelledby="directory-heading">
    <h2 id="directory-heading" class="sr-only">{$i18n.t('admin.directory')}</h2>
    {#if adminState.listError}
      <div role="alert">
        <p>{$i18n.t(notices[adminState.listError])}</p>
        <button
          type="button"
          onclick={() => adminState.loadUsers({ q: search, page, page_size: pageSize })}
          >{$i18n.t('admin.retry')}</button
        >
      </div>
    {:else if adminState.listLoading && adminState.users.length === 0}
      <p role="status">{$i18n.t('admin.loadingUsers')}</p>
    {:else if adminState.users.length === 0}
      <p role="status">{$i18n.t(search.trim() ? 'admin.noSearchResults' : 'admin.noUsers')}</p>
    {:else}
      <div class="table-scroll" aria-busy={adminState.listLoading}>
        <table>
          <thead
            ><tr>
              <th scope="col">{$i18n.t('auth.name')}</th>
              <th scope="col">{$i18n.t('admin.role')}</th>
              <th scope="col">{$i18n.t('auth.email')}</th>
              <th scope="col">{$i18n.t('admin.status')}</th>
              <th scope="col">{$i18n.t('admin.lastActive')}</th>
              <th scope="col">{$i18n.t('admin.createdAt')}</th>
              <th scope="col"><span class="sr-only">{$i18n.t('admin.actions')}</span></th>
            </tr></thead
          >
          <tbody>
            {#each adminState.users as user (user.id)}
              <tr>
                <td>{user.display_name}</td>
                <td
                  >{$i18n.t(
                    user.system_role === 'admin' ? 'admin.roleAdmin' : 'admin.roleUser',
                  )}</td
                >
                <td>{user.email}</td>
                <td>{$i18n.t(user.is_active ? 'admin.active' : 'admin.locked')}</td>
                <td
                  ><span
                    class="presence"
                    class:online={!adminState.presenceStale &&
                      adminState.presence[user.id]?.is_online}
                    title={adminState.presence[user.id]?.last_active_at
                      ? new Date(adminState.presence[user.id].last_active_at!).toLocaleString(
                          $i18n.locale,
                        )
                      : undefined}>{lastActiveLabel(user.id)}</span
                  ></td
                >
                <td
                  ><time datetime={user.created_at}
                    >{new Date(user.created_at).toLocaleDateString($i18n.locale)}</time
                  ></td
                >
                <td
                  ><button
                    class="row-action edit"
                    type="button"
                    aria-label={$i18n.t('admin.editUser', { name: user.display_name })}
                    disabled={Boolean(activityTarget) ||
                      adminState.activityBusy ||
                      adminState.formOpen}
                    onclick={(event) => {
                      editOpener = event.currentTarget;
                      editing = user;
                    }}>✎</button
                  >
                  <button
                    class="row-action account-action"
                    id={'account-action-' + user.id}
                    class:deactivate={user.is_active}
                    class:reactivate={!user.is_active}
                    type="button"
                    disabled={adminState.activityBusy ||
                      Boolean(editing) ||
                      adminState.editBusy ||
                      adminState.formOpen ||
                      adminState.activityUncertainIds.includes(user.id)}
                    aria-disabled={user.id === actorUserId && user.is_active}
                    aria-label={$i18n.t(user.is_active ? 'admin.lockUser' : 'admin.unlockUser', {
                      name: user.display_name,
                    })}
                    aria-describedby={actionTooltip?.triggerId === 'account-action-' + user.id
                      ? 'account-action-tooltip'
                      : undefined}
                    onmouseenter={(event) =>
                      showActionTooltip(
                        event,
                        $i18n.t(
                          user.id === actorUserId && user.is_active
                            ? 'admin.selfLock'
                            : user.is_active
                              ? 'admin.lock'
                              : 'admin.unlock',
                        ),
                      )}
                    onmouseleave={() => {
                      actionTooltip = null;
                    }}
                    onfocus={(event) =>
                      showActionTooltip(
                        event,
                        $i18n.t(
                          user.id === actorUserId && user.is_active
                            ? 'admin.selfLock'
                            : user.is_active
                              ? 'admin.lock'
                              : 'admin.unlock',
                        ),
                      )}
                    onblur={() => {
                      actionTooltip = null;
                    }}
                    onclick={() => {
                      if (user.id === actorUserId && user.is_active) return;
                      actionTooltip = null;
                      activityTarget = user;
                      activityDesired = !user.is_active;
                    }}
                  >
                    <svg
                      width="22"
                      height="22"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="1.8"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      aria-hidden="true"
                    >
                      <circle cx="9" cy="6" r="4" />
                      <path d="M12 20H3v-2a6 6 0 0 1 10-4.5" />
                      <circle cx="17.5" cy="17.5" r="5" />
                      {#if user.is_active}<path d="m16 16 3 3m0-3-3 3" />{:else}<path
                          d="m15.5 17.5 1.3 1.3 2.7-2.7"
                        />{/if}
                    </svg>
                  </button>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
      <footer class="pagination">
        <span>{$i18n.t('admin.userCount', { count: adminState.total })}</span>
        <div>
          <button
            type="button"
            disabled={page <= 1 || adminState.listLoading}
            onclick={() => goToPage(page - 1)}>{$i18n.t('admin.previous')}</button
          >
          <span
            >{$i18n.t('admin.pageOf', {
              page,
              pages: Math.max(1, Math.ceil(adminState.total / pageSize)),
            })}</span
          >
          <button
            type="button"
            disabled={page * pageSize >= adminState.total || adminState.listLoading}
            onclick={() => goToPage(page + 1)}>{$i18n.t('admin.next')}</button
          >
        </div>
      </footer>
    {/if}
  </section>
</section>
{#if actionTooltip}
  <div
    id="account-action-tooltip"
    role="tooltip"
    class="action-tooltip"
    style:left={`${actionTooltip.left}px`}
    style:top={`${actionTooltip.top}px`}
  >
    {actionTooltip.text}
  </div>
{/if}
<SurfaceDialog
  open={Boolean(activityTarget) && active}
  title={$i18n.t(activityDesired ? 'admin.unlockTitle' : 'admin.lockTitle')}
  onclose={() => {
    activityTarget = null;
  }}
>
  {#if activityTarget}
    <p>{activityTarget.display_name} · {activityTarget.email}</p>
    <p>{$i18n.t(activityDesired ? 'admin.unlockHelp' : 'admin.lockHelp')}</p>
    <button
      type="button"
      data-dialog-initial-focus
      onclick={() => {
        activityTarget = null;
      }}>{$i18n.t('admin.activityCancel')}</button
    >
    <button
      type="button"
      class:destructive={!activityDesired}
      class:positive={activityDesired}
      disabled={adminState.activityBusy}
      onclick={confirmActivity}
      >{$i18n.t(
        adminState.activityBusy ? 'admin.busy' : activityDesired ? 'admin.unlock' : 'admin.lock',
      )}</button
    >
  {/if}
</SurfaceDialog>
{#if editing}
  <EditUserModal
    user={editing}
    busy={adminState.editBusy}
    error={adminState.editError}
    onsave={(user, changes) => adminState.saveUser(user, changes)}
    onclose={closeEdit}
  />
{/if}

<style>
  .row-action {
    display: inline-grid;
    place-items: center;
    vertical-align: middle;
    width: 40px;
    height: 40px;
    min-height: 40px;
    padding: 0;
  }
  .account-action {
    margin-left: 4px;
  }
  .account-action.deactivate {
    color: #b91c1c;
  }
  .account-action.reactivate {
    color: #15803d;
  }
  :global([data-theme='dark']) .account-action.deactivate {
    color: #fda4af;
  }
  :global([data-theme='dark']) .account-action.reactivate {
    color: #86efac;
  }
  .account-action[aria-disabled='true'] {
    color: var(--muted);
    opacity: 0.6;
    cursor: not-allowed;
  }
  button.destructive {
    background: #b91c1c;
    border-color: #b91c1c;
    color: #fff;
  }
  button.destructive:hover:not(:disabled) {
    background: #991b1b;
    border-color: #991b1b;
  }
  button.positive {
    background: #15803d;
    border-color: #15803d;
    color: #fff;
  }
  button.positive:hover:not(:disabled) {
    background: #166534;
    border-color: #166534;
  }
  .action-tooltip {
    position: fixed;
    z-index: 1000;
    transform: translate(-50%, -100%);
    max-width: min(260px, calc(100vw - 24px));
    padding: 8px 12px;
    border-radius: 6px;
    background: #172b3a;
    color: #fff;
    font-size: 13px;
    line-height: 1.4;
    pointer-events: none;
  }
  .accounts-panel {
    width: 100%;
    padding: 1rem clamp(1rem, 3vw, 2rem);
    box-sizing: border-box;
    color: var(--ink);
    overflow-wrap: anywhere;
  }
  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    margin-bottom: 0;
  }
  h2 {
    font-size: 1.15rem;
  }
  button {
    font: inherit;
    color: var(--ink);
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 0.5rem;
    padding: 0.65rem 1rem;
    min-height: 44px;
    cursor: pointer;
  }
  button:disabled {
    opacity: 0.6;
    cursor: default;
  }
  button:focus-visible {
    outline: 2px solid var(--ink);
    outline-offset: 3px;
  }
  p {
    line-height: 1.5;
  }
  .result {
    max-width: 48rem;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1rem;
    margin-top: 1rem;
    background: var(--surface);
  }
  .directory {
    width: 100%;
    min-width: 0;
  }
  .pagination,
  .pagination > div {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    flex-wrap: wrap;
  }
  .accounts-panel :global(.create-account-dialog) {
    width: min(30rem, calc(100vw - 32px));
    max-height: min(90dvh, 48rem);
    border-radius: 16px;
    box-shadow: 0 24px 80px rgb(0 0 0 / 35%);
  }
  .user-search {
    flex: 0 1 28rem;
    min-width: 0;
  }
  header > button {
    flex: none;
    margin-left: auto;
  }
  input {
    width: 100%;
    min-height: 44px;
    min-width: 0;
    padding: 0.5rem 0.75rem;
    font: inherit;
    color: var(--ink);
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 0.5rem;
  }
  .table-scroll {
    width: 100%;
    overflow-x: auto;
    margin-block: 1rem 0.75rem;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    text-align: left;
  }
  th,
  td {
    padding: 0.75rem;
    border-bottom: 1px solid var(--border);
    white-space: nowrap;
  }
  th {
    color: var(--muted);
    font-weight: 600;
  }
  th:nth-child(1) {
    width: 22%;
  }
  th:nth-child(2) {
    width: 14%;
  }
  th:nth-child(3) {
    width: 30%;
  }
  th:nth-child(4) {
    width: 14%;
  }
  th:nth-child(5) {
    width: 14%;
  }
  :is(th, td):first-child {
    padding-left: 0;
  }
  :is(th, td):last-child {
    padding-right: 0;
    text-align: right;
  }
  .pagination {
    color: var(--muted);
  }
  .presence {
    display: inline-flex;
    align-items: center;
    gap: 8px;
  }
  .presence::before {
    content: '';
    width: 7px;
    height: 7px;
    flex: none;
    border-radius: 50%;
    background: var(--muted);
  }
  .presence.online::before {
    background: #29bd78;
  }
  .pagination button {
    min-height: 40px;
    padding: 0.45rem 0.75rem;
  }
  .edit {
    font-size: 1.15rem;
  }
  .sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
  }
  dl {
    display: grid;
    gap: 0.5rem;
  }
  dt {
    font-weight: 600;
  }
  dd {
    margin: 0;
  }
</style>
