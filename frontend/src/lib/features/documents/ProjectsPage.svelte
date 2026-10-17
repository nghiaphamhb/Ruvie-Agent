<script lang="ts">
  import {i18n} from '../../i18n/index.ts';
  import type {UiMessage} from '../../i18n/messages.ts';
  import type {ProjectSummary} from './documents-api.ts';
  let {projects, loading, error, onreload, onselect}: {
    projects: ProjectSummary[]; loading: boolean; error: UiMessage|null;
    onreload:()=>void; onselect:(id:string)=>void;
  }=$props();
</script>
<section class="projects-page" aria-labelledby="projects-heading">
  <header><h1 id="projects-heading" data-view-heading tabindex="-1">{$i18n.t('workspace.projects')}</h1>
    <button type="button" disabled={loading} onclick={onreload}>{$i18n.t('common.reload')}</button></header>
  {#if loading}<p role="status">{$i18n.t('upload.loadingProjects')}</p>
  {:else if error}<p role="alert">{$i18n.message(error)} <button type="button" onclick={onreload}>{$i18n.t('common.retry')}</button></p>
  {:else if !projects.length}<p>{$i18n.t('upload.empty')}</p>
  {:else}
    <ul>{#each projects as project (project.id)}
      <li><button class="project-card" type="button" onclick={()=>onselect(project.id)}><strong>{project.name}</strong><span>{project.code}</span></button></li>
    {/each}</ul>
    <p class="project-help">{$i18n.t('workspace.selectProject')}</p>
  {/if}
</section>
<style>
  section{max-width:900px;margin:0 auto;padding:24px;}
  header{display:flex;align-items:center;justify-content:space-between;gap:16px;}
  h1{margin:0;font-size:24px;}p{line-height:1.6;color:var(--muted);}
  [role="alert"]{color:var(--error);}
  button{min-height:44px;padding:10px 16px;border:1px solid var(--border);border-radius:12px;background:var(--surface);color:var(--ink);}
  ul{list-style:none;display:grid;grid-template-columns:repeat(auto-fit,minmax(min(240px,100%),1fr));gap:16px;padding:0;margin:24px 0;}
  li{min-width:0;}.project-card{display:flex;flex-direction:column;align-items:flex-start;gap:12px;min-height:110px;width:100%;text-align:left;overflow-wrap:anywhere;}
  .project-card:hover{background:var(--soft);}.project-card span{color:var(--muted);}
</style>
