---
name: impeccable-clarify
description: Improve interface labels, instructions, errors, empty states, and other UX copy when the user requests clearer wording. Proposes contextual before-and-after text while preserving product meaning, terminology, localization variables, and the existing design system.
license: Apache-2.0
---

# Impeccable Clarify — standalone adaptation

Modified from Paul Bakaus's Impeccable clarify playbook. See [NOTICE.md](NOTICE.md) for source and changes, and [LICENSE](LICENSE).

## Scope and coexistence

Improve interface language in its interaction context. Default to a proposal in chat with current wording, replacement, and a brief reason. When implementation is requested, inspect the actual catalogs/components, report affected paths and validation, and obtain any approval required by the repository before editing. Existing approval remains valid within its reported scope.

Keep the current design system, product terminology, factual meaning, and brand voice. Use ui-ux-pro-max for a distinct layout/accessibility concern when useful; do not change colors, typography, spacing, component structure, or business behavior as part of a copy rewrite. Flag needs outside this scope rather than silently implementing them.

No Impeccable engine, hooks, scripts, other playbooks, or automatic hand-off is required. Do not create a glossary or other project files unless their paths are included in an authorized change scope.

## Read the interaction

Inspect the complete path around the text, including the trigger, relevant controls, system state, and available next actions. Infer audience knowledge and emotional context from existing product information. Distinguish ambiguous wording, internal jargon, inconsistent terminology, missing consequences, redundant text, and text likely to overflow.

Read the actual supported behavior before describing it. Ask when an unresolved domain term or factual claim would change meaning; do not invent file limits, processing times, permission explanations, guarantees, or recovery actions. Never reveal private document details in permission-denied messages.

## Rewrite by purpose

For each message, identify the fact needed now, the next action, and only the supporting context that affects the decision. Avoid repeating a heading in its description.

- Actions: name the outcome with a specific verb and object when useful. Use consistent nouns and verbs for the same concept. In destructive confirmations, identify the object and consequence and give the action button a concrete label. Do not add undo if the product does not implement it.
- Forms: keep visible labels; placeholders provide examples. Explain known format requirements before submission. Validation identifies the field problem and how to correct it without blame.
- Errors: state what failed, why only when known and useful, and an actually available recovery step. Internal codes should not be the primary explanation. Avoid jokes about deletion, privacy, lost access, or blocked work.
- Loading: name the real operation; give honest expectations. Do not imply completion, invent progress percentages, or promise timing the system cannot establish.
- Empty states: distinguish first use, no results, active filters, missing permission, and failure. Offer an action only when it exists and is authorized.
- Success: confirm the completed outcome briefly. Describe subsequent processing separately if it is still pending.
- Help: answer the likely question instead of restating the control. Link labels make sense out of context, and icon-only controls have meaningful accessible names.

Use plain language without replacing domain terms the audience needs. Voice remains consistent; tone adapts to the consequences of the moment. Concision must preserve meaning and recovery instructions.

## Localization and accessibility

- Use the existing i18n mechanism and catalogs; do not hardcode a translation into a component when the application uses message keys.
- Preserve placeholders, interpolation syntax, plural/select branches, formatting tokens, and dynamic values. Check their callers before renaming anything.
- Prefer complete translatable messages over concatenated fragments. Let translators reorder variables and account for pluralization.
- Preserve meaningful terminology across the target flow and applicable locales. Do not silently replace other languages with the user's chat language or fabricate unverified translations.
- Keep accessible names consistent with visible action labels. Do not rely on color, punctuation, or icons alone to explain a state.
- Check long names, translation expansion, narrow widths, and 200% zoom when the rendered interface is available. Do not claim these checks passed from source inspection alone.

## Deliver and validate

Present a compact before/after table with the state or source key and the reason for each substantive change. Mark unknown current wording rather than fabricating it. Distinguish proposed copy from changes actually applied.

When implementing within approved scope, check that message keys and placeholders still match callers, related states remain truthful, and relevant locales remain consistent. Run appropriate documented checks; do not add behavior or new layers to support wording alone. Obtain approval for any generated files required by validation when repository rules require it.

Report the changed scope, checks actually performed, and remaining uncertainty. Leave unrelated UI work to the existing design workflow; do not auto-run polish or other uninstalled commands.
