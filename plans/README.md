# Plans

Use `plans/roadmap/` for active work.

## Active Queue

- `plans/roadmap/PRD.md` defines the product target.
- `plans/roadmap/domain-model.md` defines users, sessions, messages, prompts and model-call data.
- `plans/roadmap/architecture.md` defines the planned backend structure.
- `plans/roadmap/deployment.md` defines GitHub, Railway and environment setup.
- `plans/roadmap/security-checklist.md` defines privacy and abuse-control requirements.
- `plans/roadmap/tasks.md` is the source of current task order and status.
- `plans/roadmap/progress.md` records completed and blocked roadmap work.
- `plans/roadmap/decisions.md` records product, domain and architecture decisions.
- `plans/roadmap/handoff.md` contains the clean-context prompt for one atomic task.

New implementation agents should not infer requirements from chat history when the plan files already contain the needed decision. Update the plan files when the user changes direction.

## Archive

Completed historical plans can later move to `plans/archive/`.
