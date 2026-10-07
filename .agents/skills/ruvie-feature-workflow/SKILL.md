---
name: ruvie-feature-workflow
description: Create feature specs, analyze Fxxx-yyy tasks, or implement agreed task plans in the Ruvie Agent repository. Use for its spec-to-code workflow, not unrelated repositories or general questions.
---

# Ruvie Feature Workflow

Use only in the Ruvie Agent repository. Resolve paths from the repository root.
Read applicable `AGENTS.md`; use `README.md` for run/test commands and
`specs/feat/F000-pattern.md` for spec structure. Follow current files rather
than copying their rules or commands into this skill.

## Mode and permission

Choose `spec`, `analyze`, or `implement` from the user's request. Natural
language is sufficient; a mode word is optional. If intent is unclear, inspect
read-only and ask which output they want. Do not infer implementation from a
task ID, approval of a feature spec, or invocation of this skill alone.

- **spec:** inspect, propose a short development plan, and ask for confirmation
  before creating the full spec. Approval permits writing the spec, not coding.
- **analyze:** inspect and explain the selected task; do not modify files.
- **implement:** code only the requested task against the agreed plan and
  explicit implementation request. If no plan is agreed, analyze first and ask
  for confirmation before coding.

Reuse approvals already given for the same scope. Requested edits to an
existing spec need no new approval unless they change agreed scope or design.

## Shared approach

- Use **Ruvie Agent** as the project name in generated descriptions. Preserve
  exact identifiers and paths when citing existing code.
- Write user-facing explanations and specs in Vietnamese unless requested
  otherwise. Keep template headings. Use aviation-manual style for freshers:
  short, active sentences; one idea per sentence; one meaning per term. Use the
  same term for the same concept. Name the actor, condition, action and result
  when relevant. Define unfamiliar terms once; avoid ambiguous words, metaphors
  and unnecessary jargon. This is a writing preference, not a certification claim.
- Clearly distinguish **Spec requires**, **Code currently does**, and
  **Proposed implementation**. Cite verified file/function names; mark planned
  files/functions as proposals. Never describe planned behavior as implemented.
- Read the relevant spec and trace the actual input-to-output flow before
  planning. Prefer existing active code, then compatible legacy code, then new
  code for the remaining gap. Search only relevant files; exclude every
  directory named `archive`, case-insensitively.
- Inspect relevant `references/` files/functions before recreating legacy
  behavior. Record what can be reused and how contracts, dependencies, data,
  authorization, and failure handling must change. Check provenance/license
  before copying source; do not import or run legacy runtime code.
- Prefer the smallest solution that satisfies the task. Keep required
  validation, authorization, and error handling. Avoid unrelated refactors.
- Use a small diagram, input/output example, or pseudocode only where it makes
  the flow easier to understand. Do not repeat the same detail across sections.

## spec

1. Read `F000-pattern.md`, nearby feature specs, relevant active code, and
   relevant legacy examples. Identify existing behavior and the remaining gap.
2. Present a short plan: intended behavior, scope, proposed files/components,
   reuse candidates, checks, and material decisions. Ask the user to confirm;
   wait for an answer before creating the full spec. Silence is not approval.
3. After approval, choose the next unused feature number and save under
   `specs/feat/`, following the current pattern's headings and order. Preserve
   the user's numbering or destination when specified.
4. Give each task a stable `Fxxx-yyy` ID and concise details:
   - **Work:** concrete steps, in implementation order.
   - **Where:** files/functions to create, change, or reuse.
   - **Done:** observable expected result and how to check it.
5. Write acceptance criteria as testable behavior, not vague claims such as
   "works correctly." Include relevant failures and permission boundaries.
   Leave implementation tasks unchecked; writing a spec does not complete them.

## analyze

Read the selected task, related acceptance criteria, and current callers.
Explain in this order, using concise Vietnamese headings:

1. **Hiện trạng:** what exists and what is missing, with files/functions.
2. **Kết quả cần đạt:** the behavior required when the task is complete.
3. **Luồng thực hiện:** input → processing → output; who receives/returns what.
   For difficult flows, add a small Mermaid flowchart or sequence diagram when
   it improves understanding. Label components, exchanged data and important
   decisions/errors. Explain it briefly; skip diagrams for simple flows.
4. **Kế hoạch code:** proposed files, responsibilities, key functions/classes,
   their inputs/outputs, main logic, and reusable code. Add pseudocode if useful.
5. **Edge cases:** relevant empty/invalid input, provider/permission errors,
   partial failure, and intended handling; mark inapplicable cases briefly.
6. **Cách kiểm tra:** meaningful test cases and observable completion signals.
7. **Điểm cần quyết định:** open assumptions/options, recommendation and reason;
   say when none remain. Ask only about choices that affect implementation.

Keep spec requirements, current behavior, and proposals distinct throughout.
End with any confirmation needed for the plan; do not move to coding on your own.

## implement

### Readable code

- Write simple, direct code that a fresher can follow. Prefer clear names,
  small functions and existing code; avoid extra layers, dependencies or clever
  shortcuts. Keep code short without compressing it into hard-to-read lines.
- Add a short docstring at important function/class entry points: purpose,
  relevant inputs and returned result. For API/provider boundaries, document
  the method/path and request/response shape with a small example when useful.
- Comment important variables and decisions: units, trusted identity, access
  predicates, key handling, network checks, transactions and retry state.
  Explain why the code is needed; do not narrate obvious assignments or loops.
- Keep comments accurate, concise and near the code. Never include real secrets.
  When improving existing readability, preserve behavior, contracts and security
  rules; use formatting/comments first and refactor only where it helps.

### Execution

1. Re-read the selected task and agreed plan; inspect affected code and the
   worktree. Preserve existing user changes and stay within the requested task.
2. If reality differs, report the difference briefly. Adjust routine details
   within the approved design. For changes to scope, authorization, data
   behavior, or API contracts, propose an updated plan and obtain confirmation
   before those changes. Continue independent work already authorized.
3. Make the minimal implementation, using active/legacy reuse as agreed.
   Follow applicable repository and testing instructions.
4. Run unit tests for the implemented behavior. For backend changes, also run
   the full backend suite documented in `README.md` and `AGENTS.md`; for frontend
   changes, run relevant frontend tests/build checks. For schema changes, add a
   new migration and verify its SQL and relevant isolation coverage. Respect
   the repository's rules for development databases and real providers.
5. Tick only the implemented task in its feature spec after required tests
   pass and its completion criteria are verified. Leave unfinished tasks
   unchecked and explain why. Do not tick unrelated tasks or hide failing tests.

Final report, in concise Vietnamese:

- For **each changed production/configuration file**: purpose; significant
  new/changed classes or functions, role and input/output; reason for the
  approach, especially security, data handling, and control flow.
- For tests: behavior covered, exact commands, pass/fail/skip counts, and any
  blocked or unrun checks. Derive counts from output; do not invent them.
- Task/spec status, reusable code used, and remaining issues or limitations.

Do not explain test code line by line or describe trivial changes at length.
