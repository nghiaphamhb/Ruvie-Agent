import {
  AdminApiError,
  createAccount,
  getAccount,
  listAccounts,
  lookupAccount,
  updateAccount,
  setAccountActivity,
  type AccountListQuery,
  type AccountSummary,
  type AccountPresence,
} from './admin-api.ts';
import type { AccountInput, AccountFieldErrors } from './admin-form.ts';
import { getAuthSession } from '../auth/auth-api.ts';

/** One mounted admin view owns metadata and request generations, never a password draft. */
export function createAdminState({
  csrfToken,
  onexpired,
  onforbidden,
}: {
  csrfToken: string;
  onexpired: () => void;
  onforbidden: () => void;
}) {
  let formOpen = $state(false),
    busy = $state(false),
    uncertain = $state(false),
    lookupDone = $state(false);
  let sentEmail = $state('');
  let created = $state<AccountSummary | null>(null),
    found = $state<AccountSummary | null>(null);
  let error = $state<AdminApiError['code'] | null>(null);
  let fieldErrors = $state<AccountFieldErrors>({});
  let users = $state<AccountSummary[]>([]);
  let presence = $state<Record<string, AccountPresence>>({});
  let presenceStale = $state(false);
  let presenceUpdatedAt = $state(Date.now());
  let total = $state(0),
    listLoading = $state(false),
    listError = $state<AdminApiError['code'] | null>(null);
  let editBusy = $state(false),
    editError = $state<AdminApiError['code'] | null>(null);
  let activityBusy = $state(false);
  let activityError = $state<AdminApiError['code'] | null>(null);
  let activityUncertainIds = $state<string[]>([]);
  let activityGeneration = 0;
  let listGeneration = 0;
  let generation = 0,
    disposed = false;
  function reset() {
    generation++;
    formOpen = false;
    busy = false;
    uncertain = false;
    lookupDone = false;
    sentEmail = '';
    created = null;
    found = null;
    error = null;
    fieldErrors = {};
  }
  function denied(failure: unknown) {
    if (!(failure instanceof AdminApiError)) return false;
    if (failure.status === 401) {
      reset();
      onexpired();
      return true;
    }
    if (failure.status === 403 && failure.code === 'admin_required') {
      reset();
      onforbidden();
      return true;
    }
    return false;
  }
  function open() {
    if (disposed || busy) return;
    reset();
    formOpen = true;
  }
  function close() {
    if (busy) return;
    reset();
  }
  async function create(input: AccountInput): Promise<boolean> {
    if (disposed || busy || !formOpen || uncertain || found) return false;
    const current = ++generation;
    busy = true;
    error = null;
    fieldErrors = {};
    lookupDone = false;
    found = null;
    sentEmail = input.email.trim().toLowerCase();
    try {
      const result = await createAccount(input, csrfToken);
      if (disposed || current !== generation) return false;
      created = result;
      formOpen = false;
      void loadUsers(lastListQuery);
      return true;
    } catch (failure) {
      if (disposed || current !== generation || denied(failure)) return false;
      error = failure instanceof AdminApiError ? failure.code : 'unknown';
      fieldErrors = failure instanceof AdminApiError ? failure.fieldErrors : {};
      // Only recognized rejections prove this POST did not create an account.
      uncertain = !(
        failure instanceof AdminApiError &&
        ((failure.status === 403 &&
          ['origin_not_allowed', 'csrf_invalid'].includes(failure.code)) ||
          (failure.status === 409 && failure.code === 'email_taken') ||
          (failure.status === 422 && failure.code === 'validation_error') ||
          (failure.status === 500 && failure.code === 'account_creation_failed'))
      );
      return false;
    } finally {
      if (!disposed && current === generation) busy = false;
    }
  }
  let lastListQuery: AccountListQuery = { q: '', page: 1, page_size: 20 };
  async function loadUsers(query: AccountListQuery = lastListQuery, background = false) {
    if (disposed || (background && listLoading)) return;
    lastListQuery = { ...query };
    const current = ++listGeneration;
    if (!background) {
      listLoading = true;
      listError = null;
    }
    try {
      const result = await listAccounts(query);
      if (disposed || current !== listGeneration) return;
      users = result.users;
      activityUncertainIds = activityUncertainIds.filter(
        (id) => !result.users.some((user) => user.id === id),
      );
      listError = null;
      presence = result.presence ?? {};
      presenceStale = false;
      presenceUpdatedAt = Date.now();
      total = result.total;
    } catch (failure) {
      if (disposed || current !== listGeneration || denied(failure)) return;
      if (background) presenceStale = true;
      else listError = failure instanceof AdminApiError ? failure.code : 'unknown';
    } finally {
      if (!disposed && current === listGeneration) listLoading = false;
    }
  }
  async function saveUser(
    current: AccountSummary,
    changes: {
      display_name?: string;
      email?: string;
      system_role?: 'user' | 'admin';
      password?: string;
    },
  ): Promise<AccountSummary | null> {
    if (disposed || editBusy || activityBusy || !Object.keys(changes).length) return null;
    editBusy = true;
    editError = null;
    const expectedName = changes.display_name?.trim() ?? current.display_name;
    const expectedEmail = changes.email?.trim().toLowerCase() ?? current.email.toLowerCase();
    const matchesRequest = (user: AccountSummary) =>
      user.id === current.id &&
      (changes.display_name === undefined || user.display_name.trim() === expectedName) &&
      (changes.email === undefined || user.email.toLowerCase() === expectedEmail) &&
      (changes.system_role === undefined || user.system_role === changes.system_role);
    function apply(user: AccountSummary) {
      users = users.map((item) => (item.id === user.id ? user : item));
      void loadUsers(lastListQuery);
      return user;
    }
    try {
      const updated = await updateAccount(current.id, changes, csrfToken);
      if (disposed) return null;
      if (!matchesRequest(updated)) throw new AdminApiError('unknown');
      return apply(updated);
    } catch (failure) {
      if (disposed || denied(failure)) return null;
      const knownRejection =
        failure instanceof AdminApiError &&
        (failure.status === 404 ||
          failure.status === 409 ||
          failure.status === 422 ||
          failure.status === 403 ||
          failure.status === 401);
      // Validation and permission errors prove no write; other failures may follow a commit.
      if (!knownRejection) {
        if (changes.password !== undefined) {
          try {
            const session = await getAuthSession();
            if (disposed) return null;
            if (!session) {
              reset();
              onexpired();
              return null;
            }
          } catch {
            if (disposed) return null;
          }
          editError = 'account_update_unavailable';
          return null;
        }
        try {
          const currentServerValue = await getAccount(current.id);
          if (!disposed && matchesRequest(currentServerValue)) return apply(currentServerValue);
        } catch (readFailure) {
          if (disposed || denied(readFailure)) return null;
        }
        editError = 'account_update_unavailable';
      } else {
        editError = failure instanceof AdminApiError ? failure.code : 'unknown';
      }
      return null;
    } finally {
      editBusy = false;
    }
  }
  function invalidateActivity() {
    activityGeneration++;
    activityBusy = false;
  }
  async function changeActivity(
    user: AccountSummary,
    desired: boolean,
  ): Promise<{
    status: 'updated' | 'observed' | 'rejected' | 'uncertain' | 'ignored';
    user?: AccountSummary;
  }> {
    if (disposed || editBusy || activityBusy || activityUncertainIds.includes(user.id))
      return { status: 'ignored' };
    const current = ++activityGeneration;
    activityBusy = true;
    activityError = null;
    listGeneration++;
    listLoading = false;
    const alive = () => !disposed && current === activityGeneration;
    const apply = (value: AccountSummary) => {
      // Discard polls started while the write or reconciliation was pending.
      listGeneration++;
      listLoading = false;
      users = users.map((item) => (item.id === value.id ? value : item));
      if (!value.is_active && presence[value.id])
        presence = { ...presence, [value.id]: { ...presence[value.id], is_online: false } };
      void loadUsers(lastListQuery);
    };
    try {
      const updated = await setAccountActivity(user.id, desired, csrfToken);
      if (!alive()) return { status: 'ignored' };
      if (updated.id !== user.id || updated.is_active !== desired)
        throw new AdminApiError('unknown');
      apply(updated);
      return { status: 'updated', user: updated };
    } catch (failure) {
      if (!alive() || denied(failure)) return { status: 'ignored' };
      if (failure instanceof AdminApiError && [403, 404, 409, 422].includes(failure.status ?? 0)) {
        activityError = failure.code;
        if (failure.status === 404) void loadUsers(lastListQuery);
        return { status: 'rejected' };
      }
      try {
        const observed = await getAccount(user.id);
        if (!alive()) return { status: 'ignored' };
        if (observed.id !== user.id) throw new AdminApiError('unknown');
        apply(observed);
        return { status: 'observed', user: observed };
      } catch (readFailure) {
        if (!alive() || denied(readFailure)) return { status: 'ignored' };
        listGeneration++;
        listLoading = false;
        activityUncertainIds = [...activityUncertainIds, user.id];
        activityError = 'account_activity_unavailable';
        return { status: 'uncertain' };
      }
    } finally {
      if (alive()) activityBusy = false;
    }
  }
  async function lookup() {
    if (disposed || busy || !sentEmail) return;
    const current = ++generation;
    busy = true;
    error = null;
    lookupDone = false;
    found = null;
    try {
      const result = await lookupAccount(sentEmail);
      if (disposed || current !== generation) return;
      found = result;
      lookupDone = true;
      // A found account is an observation, not confirmation of creation by this actor.
      if (result === null) uncertain = false;
    } catch (failure) {
      if (disposed || current !== generation || denied(failure)) return;
      error = failure instanceof AdminApiError ? failure.code : 'unknown';
    } finally {
      if (!disposed && current === generation) busy = false;
    }
  }
  return {
    get formOpen() {
      return formOpen;
    },
    get busy() {
      return busy;
    },
    get uncertain() {
      return uncertain;
    },
    get sentEmail() {
      return sentEmail;
    },
    get created() {
      return created;
    },
    get found() {
      return found;
    },
    get lookupDone() {
      return lookupDone;
    },
    get error() {
      return error;
    },
    get fieldErrors() {
      return fieldErrors;
    },
    get users() {
      return users;
    },
    get presence() {
      return presence;
    },
    get presenceStale() {
      return presenceStale;
    },
    get presenceUpdatedAt() {
      return presenceUpdatedAt;
    },
    get total() {
      return total;
    },
    get listLoading() {
      return listLoading;
    },
    get listError() {
      return listError;
    },
    get editBusy() {
      return editBusy;
    },
    get editError() {
      return editError;
    },
    get activityBusy() {
      return activityBusy;
    },
    get activityError() {
      return activityError;
    },
    get activityUncertainIds() {
      return activityUncertainIds;
    },
    open,
    close,
    create,
    lookup,
    loadUsers,
    saveUser,
    changeActivity,
    invalidateActivity,
    dispose() {
      disposed = true;
      listGeneration++;
      invalidateActivity();
      reset();
    },
  };
}
