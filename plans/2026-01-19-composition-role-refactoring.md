# Composition Role Refactoring Plan
**GitHub Issue:** #134
**Date:** 2026-01-19
**Status:** ✅ **COMPLETED** (2026-01-25)
**Objective:** Convert composition roles from dynamic inclusion to standard Ansible role pattern

## Completion Summary

All phases of the refactoring have been successfully completed:

- ✅ **Phase 1:** Created `composition-common` role with shared infrastructure setup
- ✅ **Phase 2:** Refactored all 38 composition roles to use dependency pattern (4 manual, 34 automated)
- ✅ **Phase 3:** Updated 25 playbooks to use direct role inclusion
- ✅ **Phase 4:** Cleaned up compositions lists from 7 host_vars files
- ✅ **Phase 5:** Removed deprecated `compositions` role

**Results:**
- 112 role files modified (defaults, tasks, meta)
- 25 playbooks updated
- 7 host_vars cleaned up
- 4 deprecated role files removed
- 2 automation scripts created
- 910+ lines of code added
- 97 lines of deprecated code removed

**Commits:**
- `ae7484c5` - refactor: migrate all composition roles to use composition-common dependency
- `646b3ec1` - refactor: update playbooks to use direct composition role inclusion
- `98f972a7` - refactor: remove compositions lists from host_vars
- `f6c0f060` - refactor: remove deprecated compositions role

## Problem Statement

The current composition system uses a non-standard pattern where:
- The `compositions` role is included once in playbooks
- Host vars define a `compositions:` list of composition names
- The `compositions` role dynamically includes each `composition-*` role via `include_role`

This creates three main problems:
1. **Context switching:** Users must jump between playbooks and host vars to manage compositions
2. **Dependency management:** Cannot leverage Ansible's built-in role dependencies
3. **Non-standard:** Difficult for others to understand and use

## Current Architecture

### Compositions Role (`ansible/roles/compositions/`)
Currently handles ALL common functionality:
- Creates shared Docker bridge network
- Provisions ZFS datasets for each composition (`/{{ compositions_dataset }}/{{ item }}`)
- Creates config directories (`/{{ compositions_dataset }}/{{ item }}/config`)
- Dynamically includes each `composition-*` role with variables:
  - `composition_name: "{{ item }}"`
  - `composition_root: "/{{ compositions_dataset }}/{{ item }}"`
  - `composition_config: "/{{ compositions_dataset }}/{{ item }}/config"`
- Starts all Docker Compose projects
- Prunes unused images

**Dependencies:** `system-docker`

### Individual Composition Roles (e.g., `composition-gitea`, `composition-homeassistant`)
Each role typically:
- Templates `docker-compose.yaml.j2` to `{{ composition_root }}/docker-compose.yaml`
- Templates `environment_vars.j2` to `{{ composition_root }}/.environment_vars`
- Performs composition-specific setup:
  - Creates additional directories
  - Installs required packages
  - Configures DNS via `network-register-subdomain`
  - Templates additional configuration files

**Dependencies:** None (currently)

### Usage in Playbooks
```yaml
# ansible/playbooks/baremetal/host-albion/core.yaml
- role: compositions
```

### Usage in Host Vars
```yaml
# ansible/inventory/host_vars/host-albion/core.yaml
compositions:
  - reverseproxy
  - container-management
  - zfs-api
```

## Proposed Architecture

### New Common Role: `composition-common`
Extract reusable infrastructure setup into a new role that each composition depends on:

**Responsibilities:**
- Create Docker bridge network (if not exists, idempotent)
- Ensure `{{ composition_name }}` ZFS dataset exists
- Ensure ZFS dataset ownership is correct
- Create `{{ composition_config }}` directory
- Define common variables based on `composition_name`

**Required Variables (passed from parent):**
- `composition_name`: Name of the composition (e.g., "gitea")

**Variables it will set:**
- `composition_root: "/{{ compositions_dataset }}/{{ composition_name }}"`
- `composition_config: "/{{ compositions_dataset }}/{{ composition_name }}/config"`

**Dependencies:** `system-docker`

**Task Structure:**
```yaml
- Create Docker network (idempotent, safe to run multiple times)
- Create ZFS dataset for composition
- Set ZFS dataset ownership
- Create config directory
```

### Refactored Composition Roles
Each `composition-*` role will:
- Declare `composition-common` as a dependency in `meta/main.yaml`
- Set `composition_name` as a default variable
- Contain composition-specific logic:
  - Template `docker-compose.yaml.j2`
  - Template `environment_vars.j2`
  - Perform specific setup tasks
  - **Start its own Docker Compose project** (at the end)

**Example `meta/main.yaml`:**
```yaml
dependencies:
  - role: composition-common
    vars:
      composition_name: gitea
```

**Example `defaults/main.yaml`:**
```yaml
composition_name: gitea
```

**Example `tasks/main.yaml` pattern:**
```yaml
# Template compose file
- name: "Create compose file"
  ansible.builtin.template:
    src: docker-compose.yaml.j2
    dest: "{{ composition_root }}/docker-compose.yaml"

# Template environment vars
- name: "Create .env file"
  ansible.builtin.template:
    src: environment_vars.j2
    dest: "{{ composition_root }}/.environment_vars"

# Composition-specific tasks...

# Start this composition's containers
- name: Start Docker Compose project
  community.docker.docker_compose_v2:
    project_src: "{{ composition_root }}"
    state: present
    remove_orphans: true
```

### Usage in Playbooks (Standard Pattern)
```yaml
# ansible/playbooks/baremetal/host-albion/core.yaml
- role: composition-reverseproxy
- role: composition-container-management
- role: composition-zfs-api
```

### Migration from Host Vars
Host vars will no longer use the `compositions:` list. Instead, playbooks will directly include the required composition roles.

## Implementation Steps

### Phase 1: Create Common Infrastructure
1. **Create `composition-common` role**
   - `ansible/roles/composition-common/tasks/main.yaml`
   - `ansible/roles/composition-common/meta/main.yaml` (depends on `system-docker`)
   - `ansible/roles/composition-common/defaults/main.yaml`

2. **Move common tasks from `compositions` to `composition-common`:**
   - Docker network creation (idempotent, safe to run multiple times)
   - Single composition ZFS dataset creation (not looping)
   - Single composition config directory creation

3. **Design variable handling:**
   - `composition_name` must be provided by parent role
   - `composition_common` calculates `composition_root` and `composition_config`
   - Variables are available to dependent composition roles

### Phase 2: Refactor Composition Roles
For each of the ~39 composition roles:

1. **Create `meta/main.yaml`:**
   ```yaml
   dependencies:
     - role: composition-common
       vars:
         composition_name: <role-name-without-composition-prefix>
   ```

2. **Create or update `defaults/main.yaml`:**
   ```yaml
   composition_name: <role-name-without-composition-prefix>
   ```

3. **Update `tasks/main.yaml`:**
   - Keep composition-specific tasks (templating, setup)
   - Add Docker Compose startup task at the end
   - Use `composition_root` and `composition_config` variables (set by `composition-common`)

4. **Verify each role:**
   - Test that infrastructure is created
   - Test that containers start properly
   - Verify no behavior changes

### Phase 3: Update Playbooks
For each playbook currently using `compositions` role:

1. **Remove:** `- role: compositions`

2. **Add:** Individual composition role inclusions
   - Convert host_vars `compositions:` list to direct role inclusions
   - Example:
     ```yaml
     # Old
     - role: compositions

     # New (based on host_vars compositions list)
     - role: composition-reverseproxy
     - role: composition-container-management
     - role: composition-zfs-api
     ```

### Phase 4: Handle Special Cases

#### Reverse Proxy Role
The issue specifically asks about `composition-reverseproxy`. Analysis shows:
- It has more setup tasks than typical compositions
- It templates Traefik configuration files
- It manages provider configurations
- It creates nginx containers for catch-all and status pages
- **No special dependencies on the current structure**

The role will work fine with the new structure. It just needs proper meta/main.yaml and defaults/main.yaml files like other compositions.

#### Image Pruning
Currently handled by `compositions` role after starting all containers. Options:
1. Remove entirely (run manually with `docker image prune` when needed)
2. Add to each composition role's tasks (runs after each composition)
3. Create separate `composition-cleanup` role to run at the end of playbooks

**Recommendation:** Option 1 - Remove from automation. Image pruning is a maintenance operation that doesn't need to run on every playbook execution. Users can run `docker image prune` manually when needed.

### Phase 5: Deprecate Old System
1. **Keep `compositions` role temporarily** as a shim that shows a deprecation warning
2. **Document migration path** in role README
3. **Remove after 1-2 iterations** of using new pattern

## Variable Flow

```
Playbook
  └─> composition-gitea (role)
        ├─> defaults/main.yaml: composition_name = "gitea"
        └─> meta/main.yaml dependencies
              └─> composition-common
                    ├─> Uses: composition_name = "gitea" (from parent)
                    ├─> Sets: composition_root = "/{{ compositions_dataset }}/gitea"
                    ├─> Sets: composition_config = "/{{ compositions_dataset }}/gitea/config"
                    └─> Creates infrastructure (network, ZFS dataset, config dir)
        └─> tasks/main.yaml
              ├─> Uses: composition_root, composition_config (from composition-common)
              ├─> Templates docker-compose.yaml to {{ composition_root }}
              ├─> Templates .environment_vars to {{ composition_root }}
              ├─> Composition-specific tasks (DNS registration, configs, etc.)
              └─> Starts Docker Compose project from {{ composition_root }}
```

**Key Insight:** Each composition is now fully self-contained. The dependency runs first to create infrastructure, then the role does all its work including starting its own containers. This is simpler and more atomic than the old batch-processing approach.

## Testing Strategy

1. **Unit Testing:**
   - Test `composition-common` role in isolation
   - Verify ZFS dataset creation
   - Verify Docker network creation
   - Verify directory structure

2. **Integration Testing:**
   - Test with 2-3 simple compositions first
   - Verify `composition-reverseproxy` works (mentioned in issue as potential problem)
   - Test on a non-production host

3. **Migration Testing:**
   - Run old playbook, capture state
   - Run new playbook, compare state
   - Ensure no containers are recreated unnecessarily

4. **Rollback Plan:**
   - Keep `compositions` role intact until verification
   - Document process to revert playbooks if needed

## Benefits After Refactoring

1. **Standard Pattern:** Compositions work like normal Ansible roles
2. **Better Dependency Management:** Automatic resolution of `composition-common` → `system-docker`
3. **Easier to Understand:** Clear what each playbook deploys
4. **More Flexible:** Can override composition variables in playbooks
5. **Better IDE Support:** Jump to definition, autocomplete for role names
6. **Easier Testing:** Can test individual compositions in isolation

## Handling Composition Removal

### Problem Statement
When a composition role is removed from a playbook (or a composition name removed from the `compositions:` list in the old system), the Docker containers continue running. There is no automatic cleanup mechanism.

### Current Behavior
- Remove `- role: composition-gitea` from playbook → Gitea containers keep running
- The composition's ZFS dataset, config files, and data persist
- No indication that the composition is "orphaned" or unwanted

### Options

#### Option 1: Manual Cleanup (Recommended)
**Approach:** Document the manual process for removing compositions.

**Process:**
1. Remove the composition role from the playbook
2. SSH to the host
3. Stop and remove containers: `cd /{{ compositions_dataset }}/{{ composition_name }} && docker compose down`
4. Optionally remove data: `zfs destroy -r {{ pool }}/{{ compositions_dataset }}/{{ composition_name }}`

**Pros:**
- Simple, explicit, no surprises
- Users have full control over when data is deleted
- No risk of accidentally destroying data
- Aligns with Ansible's declarative model (playbook declares desired state, doesn't enforce absence)

**Cons:**
- Requires manual intervention
- Containers keep running until manually stopped
- Could accumulate orphaned compositions if forgotten

#### Option 2: Automated Cleanup via State Tracking
**Approach:** Track which compositions should exist and remove others automatically.

**Implementation:**
1. Create a `composition-cleanup` role that runs after all composition roles
2. Generate a list of expected compositions from the playbook
3. Query Docker for running compose projects
4. Stop any projects not in the expected list
5. Optionally mark datasets for manual review/deletion

**Example Implementation:**
```yaml
# composition-cleanup/tasks/main.yaml
- name: Get list of running compose projects
  ansible.builtin.command:
    cmd: docker compose ls --format json
  register: running_projects
  changed_when: false

- name: Parse running projects
  ansible.builtin.set_fact:
    running_composition_names: "{{ running_projects.stdout | from_json | map(attribute='Name') | list }}"

- name: Identify orphaned compositions
  ansible.builtin.set_fact:
    orphaned_compositions: "{{ running_composition_names | difference(expected_compositions) }}"

- name: Stop orphaned compositions
  ansible.builtin.command:
    cmd: "docker compose -f /{{ compositions_dataset }}/{{ item }}/docker-compose.yaml down"
  loop: "{{ orphaned_compositions }}"
  when: composition_cleanup_stop_orphans | default(false)

- name: Report orphaned compositions
  ansible.builtin.debug:
    msg: "Orphaned compositions detected (not stopped): {{ orphaned_compositions }}"
  when:
    - orphaned_compositions | length > 0
    - not (composition_cleanup_stop_orphans | default(false))
```

**Pros:**
- Automated cleanup
- Prevents orphaned containers
- Clear visibility into what's running vs configured

**Cons:**
- More complex implementation
- Risk of accidentally stopping wanted containers if playbook is incomplete
- Doesn't handle data cleanup (datasets would still exist)
- Requires passing list of expected compositions to cleanup role
- Could stop containers during troubleshooting if role temporarily removed

#### Option 3: Explicit Absence Declaration
**Approach:** Use a `state: absent` parameter in composition roles.

**Usage:**
```yaml
# To remove a composition
- role: composition-gitea
  vars:
    composition_state: absent
```

**Pros:**
- Explicit intent to remove
- Less risk of accidents
- Aligns with Ansible patterns (state: present/absent)

**Cons:**
- Verbose (must keep role in playbook to remove it)
- Doesn't help with orphaned compositions from old system
- Still requires deciding what to do with data

### Recommendation: Option 1 (Manual Cleanup)

**Rationale:**
1. **Safety First:** Compositions often contain important data. Requiring manual cleanup prevents accidental data loss.
2. **Simplicity:** No complex tracking or state management needed.
3. **Ansible Philosophy:** Ansible declares desired state. Removing a role means "don't manage this anymore," not "destroy this."
4. **Clear Process:** Easy to document and understand.

**Documentation to Provide:**
Create a runbook documenting:
- How to list running compositions: `docker compose ls`
- How to stop a composition: `cd /path/to/composition && docker compose down`
- How to remove composition data: `zfs destroy -r pool/compositions/name`
- How to identify orphaned compositions (compare `docker compose ls` output to playbook)

**Future Enhancement:**
Could add a utility script or playbook that helps identify orphaned compositions for manual review:
```bash
# scripts/list-orphaned-compositions.sh
# Compares running Docker Compose projects against configured compositions
```

### Implementation in Refactoring

**During Migration:**
1. Document the manual cleanup process in role README files
2. Add a section to CLAUDE.md about composition lifecycle
3. Create a helper script to list running vs configured compositions
4. Add to success criteria: "Orphaned composition detection documented"

**After Migration:**
- Consider adding Ansible check mode warnings if orphaned compositions detected
- Could implement Option 2 as an opt-in feature with `composition_cleanup_enabled: false` default

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking existing playbooks | High | Phased migration, keep old role temporarily |
| Variable scoping problems | Medium | Explicit variable passing, document clearly |
| Forgotten migrations | Low | Script to identify all uses of `compositions:` |
| Reverseproxy specific issues | Medium | Test this role first, it's the most complex |
| Docker network race conditions | Low | Network creation is idempotent, safe for parallel runs |
| Orphaned compositions after role removal | Medium | Document manual cleanup process, create helper script |
| Accidental data loss from automated cleanup | High | Use manual cleanup (Option 1), require explicit deletion |

## Resolved Questions

1. **Should image pruning remain automated?**
   - **Decision:** No, remove from automation. Run manually when needed.
   - **Rationale:** It's a maintenance operation that doesn't need to run on every playbook execution

2. **How to handle compositions that need to run in specific order?**
   - **Decision:** Order them explicitly in playbooks (now possible!)
   - **Example:** `composition-reverseproxy` should run before other web services

3. **Should `compositions_dataset` variable remain global?**
   - **Decision:** Yes, keep in group_vars
   - **Rationale:** All compositions use the same parent dataset

4. **What about Docker Compose project naming?**
   - **Decision:** Keep current behavior - `composition_name` is used as project name
   - **Rationale:** Maintains compatibility, no breaking changes needed

5. **How to handle composition removal (when role removed from playbook)?**
   - **Decision:** Manual cleanup process (Option 1)
   - **Rationale:** Safety first - prevents accidental data loss, aligns with Ansible philosophy
   - **Implementation:** Document process, create helper script to identify orphans
   - See "Handling Composition Removal" section above for full details

## Success Criteria

- [ ] All ~39 composition roles refactored with proper `meta/main.yaml`
- [ ] `composition-common` role created and tested
- [ ] All playbooks updated to use direct role inclusion
- [ ] All host_vars `compositions:` lists removed
- [ ] `composition-reverseproxy` specifically verified working
- [ ] No Docker containers recreated during migration (no downtime)
- [ ] Documentation updated (README files, CLAUDE.md)
- [ ] Old `compositions` role deprecated with clear migration guide
- [ ] Composition removal process documented (how to stop/remove unwanted compositions)
- [ ] Helper script created to identify orphaned compositions
