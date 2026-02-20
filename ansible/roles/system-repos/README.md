# system-repos

Clones and manages git repositories on target hosts via SSH.

**Prerequisites:** SSH keys must be configured on the target host for
repository access.

## Usage

```yaml
repos:
  - repo: awfulwoman/infra
    name: infra
  - repo: awfulwoman/obsidian
    name: obsidian
```

## Parameters

### Global

- `repos_base_dir`: Base directory for clones (default: `/opt/repos`)
- `repos_git_host`: Git host (default: `github.com`)
- `repos_update`: Update existing repos (default: `false`)

### Per-repo

- `repo`: Repository in `owner/name` format (required)
- `name`: Directory name (optional, defaults to repo name)
- `version`: Branch/tag/commit (optional, defaults to `HEAD`)

## Examples

**Basic usage:**

```yaml
repos:
  - repo: awfulwoman/infra
```

**Specific version:**

```yaml
repos:
  - repo: awfulwoman/infra
    version: v1.2.3
```

**Custom directory name:**

```yaml
repos:
  - repo: awfulwoman/infra
    name: infrastructure
```
