# Project Memory

A shared, committed project memory file exists at `.claude/memory.md`.

## Reading

At the start of every session, read `.claude/memory.md` to load project
context accumulated from previous sessions.

## Writing

Update `.claude/memory.md` when you:

- Discover a non-obvious architectural pattern or constraint
- Solve a recurring or tricky debugging problem
- Confirm a convention that isn't documented elsewhere
- Learn something host-specific that would save time next session

When updating, edit the relevant section in-place. Do not append
chronological logs — maintain the file as a living reference, not a diary.

## Rules

- Never store secrets, credentials, or Ansible Vault values here
- Remove entries that are no longer accurate
- Keep entries concise — prefer bullets over prose
