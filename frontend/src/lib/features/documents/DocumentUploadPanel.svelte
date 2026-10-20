<script lang="ts">
  import { i18n, formatFileSize } from '../../i18n/index.ts';
  import type { UiMessage } from '../../i18n/messages.ts';
  import type { ProjectSummary, RevisionStatus } from './documents-api.ts';
  let {
    projects,
    projectsLoading,
    projectsError,
    selectedProjectId = $bindable(),
    uploadTitle = $bindable(),
    uploadSoftware = $bindable(),
    uploadSoftwareVersion = $bindable(),
    selectedFile = $bindable(),
    uploadBusy,
    uploadError,
    uploadStatus,
    uploadTimedOut,
    statusRefreshing,
    onsubmit,
    onrefresh,
    onprojectsreload,
  }: {
    projects: ProjectSummary[];
    projectsLoading: boolean;
    projectsError: UiMessage | null;
    selectedProjectId: string;
    uploadTitle: string;
    uploadSoftware: string;
    uploadSoftwareVersion: string;
    selectedFile: File | null;
    uploadBusy: boolean;
    uploadError: UiMessage | null;
    uploadStatus: RevisionStatus | null;
    uploadTimedOut: boolean;
    statusRefreshing: boolean;
    onsubmit: (event: SubmitEvent) => void;
    onrefresh: () => void;
    onprojectsreload: () => void;
  } = $props();
  function uploadStatusLabel(status: RevisionStatus['status']) {
    return {
      pending: $i18n.t('upload.status.pending'),
      running: $i18n.t('upload.status.running'),
      ready: $i18n.t('upload.status.ready'),
      failed: $i18n.t('upload.status.failed'),
    }[status];
  }
</script>

<section class="upload-panel" aria-labelledby="upload-heading">
  <div class="upload-heading">
    <div>
      <p class="eyebrow">{$i18n.t('upload.eyebrow')}</p>
      <h2 id="upload-heading">{$i18n.t('upload.heading')}</h2>
    </div>
    <p>{$i18n.t('upload.support')}</p>
  </div>
  {#if projectsError}<p class="upload-error" role="alert">
      {$i18n.message(projectsError)}
      <button type="button" onclick={onprojectsreload}>{$i18n.t('common.retry')}</button>
    </p>{/if}
  {#if !projectsLoading && projects.length === 0 && !projectsError}
    <p class="upload-note">{$i18n.t('upload.empty')}</p>
  {:else}
    <form class="upload-form" {onsubmit}>
      <label
        >{$i18n.t('upload.project')}
        <select
          aria-label={$i18n.t('upload.project')}
          required
          bind:value={selectedProjectId}
          disabled={projectsLoading || uploadBusy}
        >
          <option value="" disabled
            >{projectsLoading
              ? $i18n.t('upload.loadingProjects')
              : $i18n.t('upload.chooseProject')}</option
          >
          {#each projects as project (project.id)}<option value={project.id}
              >{project.name} · {project.code}</option
            >{/each}
        </select>
      </label>
      <label
        >{$i18n.t('upload.title')}<input
          required
          maxlength="500"
          bind:value={uploadTitle}
          disabled={uploadBusy}
        /></label
      >
      <label
        >{$i18n.t('upload.software')}<input
          required
          maxlength="255"
          bind:value={uploadSoftware}
          disabled={uploadBusy}
        /></label
      >
      <label
        >{$i18n.t('upload.version')}<input
          required
          maxlength="255"
          bind:value={uploadSoftwareVersion}
          disabled={uploadBusy}
        /></label
      >
      <label class="upload-file"
        >{$i18n.t('upload.file')}<input
          required
          type="file"
          accept=".pdf,.txt,application/pdf,text/plain"
          onchange={(event) =>
            (selectedFile = (event.currentTarget as HTMLInputElement).files?.[0] ?? null)}
          disabled={uploadBusy}
        /></label
      >
      {#if selectedFile}
        <!-- File card structure/glyph from references/.../common/FileItem.svelte.
           Selected browser file only: no content URL, preview, or download. -->
        <div class="file-card">
          <span class="file-icon" aria-hidden="true">
            {#if uploadBusy}<span class="status-dot"></span>{:else}
              <svg viewBox="0 0 24 24" fill="currentColor"
                ><path
                  fill-rule="evenodd"
                  d="M5.625 1.5c-1.036 0-1.875.84-1.875 1.875v17.25c0 1.035.84 1.875 1.875 1.875h12.75c1.035 0 1.875-.84 1.875-1.875V12.75A3.75 3.75 0 0 0 16.5 9h-1.875a1.875 1.875 0 0 1-1.875-1.875V5.25A3.75 3.75 0 0 0 9 1.5H5.625ZM7.5 15a.75.75 0 0 1 .75-.75h7.5a.75.75 0 0 1 0 1.5h-7.5A.75.75 0 0 1 7.5 15Zm.75 2.25a.75.75 0 0 0 0 1.5H12a.75.75 0 0 0 0-1.5H8.25Z"
                  clip-rule="evenodd"
                /><path
                  d="M12.971 1.816A5.23 5.23 0 0 1 14.25 5.25v1.875c0 .207.168.375.375.375H16.5a5.23 5.23 0 0 1 3.434 1.279 9.768 9.768 0 0 0-6.963-6.963Z"
                /></svg
              >
            {/if}
          </span>
          <div>
            <strong>{selectedFile.name}</strong><small
              >{selectedFile.type || $i18n.t('upload.file')} · {formatFileSize(
                selectedFile.size,
                $i18n.locale,
              )}</small
            >
          </div>
        </div>
      {/if}
      <button
        class="upload-submit"
        type="submit"
        disabled={uploadBusy ||
          statusRefreshing ||
          projectsLoading ||
          !projects.length ||
          !selectedFile ||
          !selectedProjectId}
        >{uploadBusy ? $i18n.t('upload.uploading') : $i18n.t('upload.submit')}</button
      >
    </form>
  {/if}
  {#if uploadStatus}
    <div class="upload-status" role="status">
      <span>{uploadStatusLabel(uploadStatus.status)}</span>
      {#if uploadStatus.status === 'failed' && uploadStatus.error_code}<span
          >{$i18n.t('upload.errorCode', { code: uploadStatus.error_code })}</span
        >{/if}
      {#if (uploadTimedOut || uploadError) && uploadStatus.status !== 'ready' && uploadStatus.status !== 'failed'}{#if uploadTimedOut}<span
            >{$i18n.t('upload.continuing')}</span
          >{/if}<button type="button" onclick={onrefresh} disabled={statusRefreshing}
          >{statusRefreshing ? $i18n.t('upload.refreshing') : $i18n.t('upload.refresh')}</button
        >{/if}
    </div>
  {/if}
  {#if uploadError}<p class="upload-error" role="alert">{$i18n.message(uploadError)}</p>{/if}
</section>

<style>
  .upload-panel {
    flex: none;
    width: min(calc(100% - 48px), var(--form-width));
    margin: 24px auto;
    padding: calc(3 * var(--space));
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--surface);
  }
  .upload-heading {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 8px;
    flex-direction: column;
  }
  .upload-heading h2 {
    margin: 0;
    font-size: 19px;
    letter-spacing: -0.02em;
  }
  .upload-heading .eyebrow {
    margin-bottom: 5px;
  }
  .upload-heading > p,
  .upload-note {
    margin: 0;
    color: var(--muted);
    font-size: 12px;
  }
  .upload-form {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 11px;
    margin-top: 14px;
    align-items: end;
  }
  .upload-form label {
    display: grid;
    gap: 6px;
    color: var(--muted);
    font-size: 12px;
    font-weight: 600;
  }
  .upload-form input,
  .upload-form select {
    min-width: 0;
    min-height: 44px;
    padding: 8px 10px;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--surface);
    color: var(--ink);
    font: inherit;
    font-weight: 400;
  }
  .upload-form .upload-file input {
    padding: 5px;
  }
  .upload-submit {
    min-height: 44px;
    border: 0;
    border-radius: var(--radius);
    background: var(--accent);
    color: var(--surface);
    font-weight: 650;
    justify-self: start;
    padding: 10px 24px;
  }
  .upload-submit:disabled {
    opacity: 0.55;
  }
  .upload-status {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 12px;
    margin-top: 12px;
    color: var(--accent);
    font-size: 13px;
  }
  .upload-status button,
  .upload-error button {
    min-height: 44px;
    min-width: 44px;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 6px 9px;
    background: var(--surface);
    color: var(--accent);
  }
  .upload-error {
    margin: 12px 0 0;
    color: var(--error);
    font-size: 13px;
  }
  .upload-note {
    margin-top: 12px;
  }
  .upload-file,
  .file-card {
    grid-column: 1 / -1;
  }
  .file-card {
    display: flex;
    gap: 12px;
    align-items: center;
    padding: 12px;
    background: var(--soft);
    border-radius: var(--radius);
    overflow-wrap: anywhere;
  }
  .file-icon {
    flex: none;
    display: grid;
    place-items: center;
    width: 40px;
    height: 40px;
    border-radius: var(--radius);
    background: var(--surface);
  }
  .file-icon svg {
    width: 20px;
    height: 20px;
  }
  .file-card div {
    min-width: 0;
  }
  strong {
    display: block;
    font-size: 14px;
    font-weight: 600;
  }
  small {
    display: block;
    color: var(--muted);
    margin-top: 4px;
    font-size: 12px;
  }
</style>
