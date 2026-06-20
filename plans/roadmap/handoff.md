# Clean-Context Handoff

Use this file to start a fresh agent window for one atomic task. Replace placeholders and keep scope narrow.

## Standard Handoff Prompt

```text
Прочитай:
- AGENTS.md
- harness/README.md
- plans/roadmap/PRD.md
- plans/roadmap/domain-model.md
- plans/roadmap/architecture.md
- plans/roadmap/deployment.md
- plans/roadmap/security-checklist.md
- plans/roadmap/tasks.md
- plans/roadmap/progress.md
- plans/roadmap/decisions.md
- plans/roadmap/task-template.md
- plans/roadmap/invariant-checklist.md

Возьми только task <TASK_ID> из plans/roadmap/tasks.md.

Цель:
<one-sentence objective from tasks.md>

Ограничения:
- не трогай соседние задачи;
- MVP остается single-prompt ботом;
- отправляй всю активную историю в DeepSeek, если задача явно не меняет эту политику;
- не логируй полный prompt и полные сообщения пользователя;
- не коммить секреты;
- Telegram и DeepSeek в тестах должны быть моками по умолчанию;
- если принимаешь спорное архитектурное/privacy/deployment решение, добавь запись в decisions.md;
- в конце обнови progress.md;
- перед финальным ответом запусти focused checks и python scripts/validate.py, если он уже есть.

Начни с drift check:
git status --short -- <likely files from task>

Если это еще не git-репозиторий, отметь это в progress.md и продолжай аккуратно.
Если есть unrelated dirty changes, работай вокруг них и не откатывай их.
Если задача требует новых секретов или live API, остановись и попроси конкретные env vars.
```

## Minimal Executor Checklist

1. Read required files.
2. Identify one task ID.
3. Confirm scope and likely files.
4. Run drift check.
5. Implement only that task.
6. Add or update tests.
7. Run focused checks.
8. Run unified validation if available.
9. Update `progress.md`.
10. Update `decisions.md` if a decision was made.
11. Final response: changed files, checks, remaining risks.

## Blocked Task Handoff

Use this when a task cannot proceed:

```md
### YYYY-MM-DD - Task <TASK_ID> BLOCKED

- Blocking issue:
  - `<specific missing decision/data/tooling>`
- Evidence:
  - `<file/test/command/result>`
- Files changed:
  - `<path or none>`
- Checks:
  - `<command>`: passed | failed | not run, reason
- Needed from user:
  - `<one concrete decision or input>`
```

Blocked tasks must not be marked `DONE` in `tasks.md`.

## Resume Prompt After Block

```text
Resume task <TASK_ID>.

Read:
- plans/roadmap/progress.md
- plans/roadmap/decisions.md
- plans/roadmap/tasks.md
- plans/roadmap/task-template.md
- files changed in the blocked attempt

The previous block was:
<copy blocking issue>

New user decision/input:
<copy user answer>

Continue with the same scope. Do not restart unrelated phases.
```
