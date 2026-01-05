# Commit Changes

Create a well-crafted git commit for the current changes.

## Instructions

1. Run `git status` and `git diff` to understand all changes
2. Analyze the changes and draft a concise commit message that:
   - Summarizes the nature of the changes (feature, fix, refactor, etc.)
   - Focuses on the "why" rather than the "what"
   - Uses imperative mood (e.g., "Add feature" not "Added feature")
   - Keeps the first line under 72 characters
3. Stage all relevant changes with `git add`
4. Commit with the message, ending with the standard Claude Code footer

## Commit Message Format

```
<type>: <short description>

<optional body explaining why, not what>

Co-Authored-By: Claude <noreply@anthropic.com>
```

## Types

- `feat`: New feature
- `fix`: Bug fix
- `refactor`: Code refactoring
- `docs`: Documentation changes
- `chore`: Maintenance tasks
- `style`: Formatting, whitespace changes

## Important

- Do NOT commit files that contain secrets (.env, credentials, etc.)
- Do NOT push to remote unless explicitly asked
- Use a HEREDOC for the commit message to preserve formatting
- ONLY add Claude as as a co-author if Claude has written the code. Do not add if it was written solely by others.
