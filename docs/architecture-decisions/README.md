# Architecture decision records

## What lives here

**Architecture decision records** are short, versioned write-ups of **meaningful technical choices**: tradeoffs, boundaries, and “why we did X instead of Y.” They are for decisions that would be hard to infer from code alone or that future readers will question.

Not every change needs a decision record—routine features and bugfixes usually do not.

*(Some teams call these “ADRs”; the folder name spells it out on purpose.)*

## The starter file

**[new-architecture-decision.md](new-architecture-decision.md)** is not a real decision record itself. It is the **copy-paste skeleton** for a new one: open it (or duplicate it in your editor), save as `docs/architecture-decisions/NNNN-kebab-case-title.md` using the **next monotonic number** prefix, then replace the placeholder title and follow the sections. The file opens with a short callout so anyone who lands on it in GitHub sees immediately what it is for.

## Naming new files

Use `NNNN-kebab-case-title.md` (e.g. `0003-session-auth-strategy.md`). Numbers keep a stable order; pick the next free integer.
