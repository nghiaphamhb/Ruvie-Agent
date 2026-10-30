---
name: impeccable-critique
description: Review an existing interface for usability, information hierarchy, consistency, and task clarity when the user requests critique or UI evaluation. Produces evidence-backed recommendations without editing the application; complements ui-ux-pro-max rather than choosing a new design system.
license: Apache-2.0
---

# Impeccable Critique — standalone adaptation

Modified from Paul Bakaus's Impeccable critique playbook. This is a lightweight adaptation, not the full upstream critique workflow. See [NOTICE.md](NOTICE.md) for source and changes, and [LICENSE](LICENSE).

## Scope and coexistence

Review an existing screen, component, or interaction. Deliver the review in chat; do not edit application files or persist reports unless separately requested and authorized. Follow applicable repository approval rules for every file-generating operation, including builds and screenshots.

Preserve the established visual identity, tokens, product facts, and API behavior. Use the project's ui-ux-pro-max guidance for focused design or implementation questions when useful; do not regenerate a design system during critique. Do not recommend a font or palette replacement merely because a pattern is common. Do not automatically invoke other skills or begin implementing findings.

This adaptation has no Impeccable engine, CLI detector, hooks, telemetry, storage, or required subagents. Do not install or invoke those dependencies. It makes no claim of equivalence to upstream dual-assessment critique.

## Establish the evidence

- Resolve a concrete target from the request and available project context. Ask only when the target cannot be inferred.
- Identify the primary user, their task, and the outcome that counts as success. For an operational application, prioritize completing tasks, scanability, predictable behavior, and clear system state.
- Inspect the target's actual components, styles, and related state handling. Read existing product/design context when present; do not create context files as a prerequisite. Respect excluded directories and private data.
- Inspect the rendered target at relevant desktop/mobile widths and theme states when tools and an authorized running app are available. A screenshot supports visual findings, not claims that keyboard or error flows were tested.
- If rendering is unavailable, continue as a source-only review. State that limitation prominently and mark visual or runtime concerns as hypotheses requiring verification. Do not invent measurements, contrast results, user tests, or detector findings.

## Review the task, not decoration alone

Walk the primary path from entry through action, feedback, and recovery. Consider:

- System status: loading, progress, completion, failure, and stale state.
- Familiar language: terms and controls match what the audience understands.
- User control: cancel, back, undo, and recovery where appropriate.
- Consistency: repeated concepts and actions behave alike.
- Error prevention: constraints and consequences are visible before commitment.
- Recognition: choices are visible rather than dependent on memory.
- Efficiency: frequent tasks avoid unnecessary steps without hiding essential guidance.
- Information hierarchy: the main content and next action are easy to find; density serves the task.
- Error recovery: messages explain the problem and an available next step.
- Help: contextual guidance appears where it changes a decision.

Also inspect focus/keyboard behavior, accessible names, responsive overflow, localization expansion, and theme readability where evidence permits. Distinguish functional barriers from personal aesthetic preference.

Use two relevant perspectives, such as a first-time employee and a frequent IT support user. Identify specific friction in their task paths; do not invent research or present imagined reactions as observed behavior.

## Deliver a useful review

Respond in the user's language. Start with the most consequential finding and name the target and evidence method (rendered, screenshot, source-only, or mixed).

Briefly identify what already works. Rank the material findings:

- P0: a verified blocker to the primary task for the affected users.
- P1: major friction, misleading behavior, or a substantial accessibility barrier.
- P2: a recurring clarity, hierarchy, or consistency issue.
- P3: a minor refinement with limited task impact.

For each finding, give the exact element/state or source location, observed evidence, user impact, and a concrete bounded recommendation. Separate confirmed issues from unverified concerns. Do not inflate severity or force a minimum number of findings.

Numerical heuristic scoring is optional. If requested, define a 0–4 scale, mark unassessed or inapplicable heuristics as N/A, exclude them from the denominator, and describe scores as reviewer judgments rather than measured usability.

Finish with a small prioritized next-step proposal and the material validation limits. Recommend impeccable-clarify only for findings about interface wording. Do not require commands from the uninstalled Impeccable suite. Ask a focused question only when priorities or intent materially affect the proposed next step; do not gate the review on a questionnaire.
