# How the AI agent talks to GitHub

An explanation of the git and GitHub authentication system that the opencode
agent uses, written for a reader who meets it for the first time. The
authoritative reference is [the role README](../../roles/system-opencode/README.md).

## The problem this system solves

The user runs an AI agent, opencode, that writes code and pushes it to GitHub.
GitHub must know who sends each push. Humans normally prove their identity with
a credential that stays valid for years. The agent must not have such a
credential, because a hostile party could steal it.

## Two ways to connect

Git can connect to GitHub in two ways: with SSH or with HTTPS.

- **SSH** uses a private key file. The key sits in `~/.ssh` and stays valid for
  years.
- **HTTPS** uses a user name and a password. For a program, the password is a
  *token*. A token is a text string that GitHub creates for one caller, and
  each token has a limited life.

## The agent has no permanent secrets

The agent runs inside a sandbox. A sandbox is a locked space on the computer:
the agent can read and write the code, but it cannot read private files. The
sandbox blocks `~/.ssh`, so the agent has no SSH key. It also blocks the normal
`gh` login data, which holds a token that stays valid for years. The agent
cannot leak what the agent does not have.

## A bot identity with a one-hour token

The system gives the agent a bot identity: a GitHub App. A GitHub App has its
own private key. This key sits in `~/.config/opencode-secrets/github-app.pem`,
outside the sandbox, so the agent cannot read it or copy it.

A program outside the sandbox uses this key and asks GitHub for a token.
GitHub sends back a token that is valid for one hour. The agent can use this
token, but it can never see the key behind it.

## What happens at session start

The agent never starts by itself. A wrapper script starts the agent.

1. Before the sandbox starts, the wrapper asks GitHub for a token. It writes
   the token to `~/.config/opencode/gh-token`.
2. While the session runs, a background loop in the wrapper asks for a new
   token every 45 minutes. The loop stops when the session stops.

Why does the token live in a file? A session keeps its environment variables
until the end. A file can change at any time, and every reader sees the new
value at once.

## Who uses SSH and who uses HTTPS

Every repo points to GitHub with an SSH address, for example
`git@github.com:awfulwoman/infra.git`. For manual work, the user's git connects
over SSH with the key in `~/.ssh`. The repos keep their SSH addresses, so
manual work stays the same.

Inside an agent session, the wrapper adds one extra git rule: replace every SSH
address with an HTTPS address. So the agent always connects over HTTPS, because
it has no SSH key.

| Who | Channel | Credential |
|-----|---------|------------|
| The user, manual git | SSH | the key in `~/.ssh` |
| The agent, git push and fetch | HTTPS (rewritten from SSH) | the one-hour App token |
| The agent, `gh` | HTTPS (GitHub API) | the same token |

During each push, git asks a helper script for the password. The helper is
`git-credential-github.sh`. It reads the token file and answers with the name
`x-access-token` plus the current token. The part before `@` in the rewritten
address is the user name.

## The `gh` helper

The `gh` tool reads its token from an environment variable, so the file trick
alone does not work for it. The wrapper puts a small helper program in front of
`gh`. This helper reads the token file each time it runs. Outside a session,
the helper passes through, and `gh` uses the normal login of the user.

## How the system grew

The commit history of this repo shows the lessons:

- **Nov 12:** First version. Git inside the sandbox could not read the App key,
  so pushes went out with an empty token. The fix: the wrapper creates the
  token outside the sandbox.
- **Nov 14:** `gh` receives its own config directory inside the sandbox. It no
  longer reads the long-lived login of the user.
- **Nov 15:** The token file and the 45-minute refresh loop arrive. Before this
  change, a session older than one hour pushed with an invalid token.

## The security payoff

If a hostile party takes control of the agent, it holds no permanent key. It
holds one token that becomes invalid within the hour, and the App reaches only
the repos where the user installed it. The App has only two permissions: read
and write for git content, and read and write for issues.
