# Open WebUI Legacy Reference Audit

Audit date: 2026-07-29

## Scope

A case-insensitive scan for `Open WebUI`, `open-webui`, `open_webui`, and
`openwebui` found 1,279 tracked-file matches after excluding `package-lock.json`
and `CHANGELOG.md`. Most matches are inherited locale entries or compatibility
identifiers, not visible branding.

## Priority 1 — User-visible links and copy

These should be reviewed first because users can see them or follow them out of
Ruvie:

- Community, model, prompt, tool, and function links still point to
  `openwebui.com` in:
  - `src/lib/components/admin/Evaluations/Feedbacks.svelte`
  - `src/lib/components/admin/Functions.svelte`
  - `src/lib/components/chat/ChatPlaceholder.svelte`
  - `src/lib/components/chat/Placeholder.svelte`
  - `src/lib/components/chat/Messages/RateComment.svelte`
  - `src/lib/components/chat/ModelSelector/ModelItemMenu.svelte`
  - `src/lib/components/chat/ShareChatModal.svelte`
  - `src/lib/components/workspace/Models.svelte`
  - `src/lib/components/workspace/Prompts.svelte`
  - `src/lib/components/workspace/Tools.svelte`
- Help, release, enterprise, social, and license links still point to Open WebUI
  documentation or accounts in:
  - `src/lib/components/AddToolServerModal.svelte`
  - `src/lib/components/admin/Settings/Authentication.svelte`
  - `src/lib/components/admin/Settings/Connections.svelte`
  - `src/lib/components/admin/Settings/General.svelte`
  - `src/lib/components/admin/Users/UserList.svelte`
  - `src/lib/components/chat/Settings/About.svelte`
  - `src/lib/components/chat/Settings/General.svelte`
  - `src/lib/components/layout/Sidebar/UserMenu.svelte`
  - `src/lib/components/layout/UpdateInfoToast.svelte`
- The enabled Vietnamese and Russian translations still display “OpenWebUI
  Community” for three Ruvie community strings:
  - `src/lib/i18n/locales/vi-VN/translation.json`
  - `src/lib/i18n/locales/ru-RU/translation.json`
- Function-editor defaults still identify `open-webui` as the author and link to
  its GitHub account:
  - `src/lib/components/admin/Functions/FunctionEditor.svelte`

## Priority 2 — Runtime calls and outbound identification

These references affect runtime behavior or disclose the upstream product to
external services:

- `backend/ruvie/config.py` fetches custom branding assets from
  `api.openwebui.com`.
- `backend/ruvie/main.py` checks the Open WebUI GitHub repository for releases
  and prints its repository URL during startup.
- `backend/ruvie/utils/auth.py` allows Open WebUI API and license domains.
- `backend/ruvie/routers/openai.py` sends `https://openwebui.com/` as an
  `HTTP-Referer`.
- Retrieval loaders and web-search providers send Open WebUI-branded
  `User-Agent` or integration headers.
- Several admin settings still send users to Open WebUI documentation because
  Ruvie does not yet have equivalent local documentation.

## Priority 3 — Compatibility identifiers

Do not rename these as a branding-only cleanup. They can affect persisted data,
third-party integrations, upgrades, or protocol compatibility:

- Database/vector prefixes such as `open_webui`, `open-webui-index`, and
  `open_webui_collections`.
- Forwarded request headers such as `X-OpenWebUI-User-*`.
- Structured-output types such as `open_webui:code_interpreter`.
- Drag-and-drop MIME data `application/x-open-webui-drag`.
- Manifest key `required_open_webui_version`.
- Environment variables, package name, CLI command, Docker service/image names,
  telemetry service name, and Kubernetes service address.

Rename these only with a migration and backward-compatibility plan.

## Legal and historical references

Keep the attribution and upstream-license text in `LICENSE`. `README.md` also
correctly states that Ruvie is derived from Open WebUI. Historical comments and
upstream issue links may remain when they explain a dependency or workaround.

## Recommended cleanup order

1. Replace or hide user-visible community, social, release, and marketplace
   links that Ruvie does not support.
2. Correct the enabled Vietnamese and Russian translations.
3. Replace outbound branding headers and update checks where Ruvie has an
   owned endpoint.
4. Migrate compatibility identifiers separately; do not combine this with UI
   branding work.
