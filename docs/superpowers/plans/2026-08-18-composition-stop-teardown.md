# Composition Stop and Teardown Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Support two teardown states in the `compositions:` list — `state: stopped` (stop containers, leave everything else) and `state: absent` (stop and remove containers, then park the ZFS dataset in a graveyard so data and snapshots survive).

**Architecture:** `system-compositions` splits its loop by state. Present-state compositions include their `composition-*` role exactly as today. Non-present states bypass the composition role entirely and route to a single shared `teardown.yaml`, which derives the paths it needs from the list item. The ~39 `composition-*` roles are unchanged.

**Tech Stack:** Ansible, `community.docker.docker_compose_v2`, `zfs rename`

---

## Context

`state:` values live in host_vars and re-execute on every playbook run, so teardown must never be able to destroy data on its own. `state: absent` therefore **parks** a dataset (atomic `zfs rename` into a graveyard path) rather than destroying it. A human destroys it later, deliberately.

## Critical safety constraint: never use `community.general.zfs` `state: absent`

The module source (`community/general/plugins/modules/zfs.py:174`) runs:

```python
cmd = [self.zfs_cmd, "destroy", "-R", self.name]
```

`-R` destroys the dataset, all child datasets, **its entire snapshot history**, and any dependent clones — including clones outside the hierarchy. In this repo specifically:

- `fastpool/compositions` is `policy: critical` with `snapshots_discover_children: true` (`inventory/host_vars/server-64gb-storage/core.yaml:49-52`), so every composition dataset carries deep snapshot history.
- `backups-zfs-client` replicates using `zfs send -R -w -I <snap> <snap>` — incremental sends anchored on those snapshots. Erasing them breaks the replication chain.

This module must not be used for dataset removal anywhere in this plan. `zfs rename` is used instead.

## The graveyard must stay undeclared in `zfs:`

Do **not** add the graveyard to the `zfs:` structure in host_vars. `zfs-prune.py` and `zfs-snapshot.py` build their target list from `{{ zfs | zfs_datasets_with_policy }}` — only datasets declared there, plus discovered children of datasets flagged `snapshots_discover_children`. An undeclared `fastpool/graveyard/*` is invisible to both: no new snapshots, and critically **no pruning**, so parked history freezes exactly as-is.

Declaring it with `policy: none` would be actively harmful — `none` is `autoprune: true` with all retention counts at `0` (`roles/system-zfs-policy/defaults/main.yaml:22-29`), which would prune away every snapshot just parked.

Creating the dataset via `community.general.zfs` `state: present` does **not** declare it in the `zfs:` policy structure — those are independent mechanisms.

Side effect: a parked dataset leaves syncoid's backup scope, since it is no longer a child of `fastpool/compositions`. Expected for a decommissioned service, but it means the graveyard is not itself backed up — empty it deliberately rather than letting it accumulate.

## Verified behaviours (tested, not assumed)

- `include_role` + `vars:` reaches a role's `meta/` dependency and overrides that dependency's role default.
- A dependency's `defaults/` propagate to the dependent role — so one `state: present` default in `composition-common` covers roles invoked directly from a `roles:` list (`composition-zfs-api` in the `zfs_backup_*` group playbooks).
- No composition role calls `include_role`/`import_role`, so a task-scoped `state` var cannot leak into an unrelated role.
- All composition roles depend on `composition-common` except `composition-mcp-kagi`, which is orphaned (absent from inventory and playbooks).

---

## Task 1: Split the deploy loop by state

- [ ] **Step 1: Edit `roles/system-compositions/tasks/main.yaml`**

Keep the existing comment block at the top. Replace the single task with two, preserving the `target_composition` filter in both:

```yaml
- name: Deploy compositions
  ansible.builtin.include_role:
    name: "composition-{{ item.composition | default(item) }}"
  loop: "{{ compositions }}"
  loop_control:
    label: "{{ item.composition | default(item) }}"
  when: >-
    (not (target_composition | default(''))
     or (item.composition | default(item)) in (target_composition | default('') | split(',')))
    and (item.state | default('present')) == 'present'

- name: Tear down compositions
  ansible.builtin.include_tasks: teardown.yaml
  loop: "{{ compositions }}"
  loop_control:
    label: "{{ item.composition | default(item) }}"
  when: >-
    (not (target_composition | default(''))
     or (item.composition | default(item)) in (target_composition | default('') | split(',')))
    and (item.state | default('present')) in ['stopped', 'absent']
```

Note the `vars: state: ...` block from the current version is removed — composition roles no longer receive `state`, because non-present states never reach them.

## Task 2: Add the shared teardown tasks

- [ ] **Step 1: Create `roles/system-compositions/tasks/teardown.yaml`**

```yaml
# code: language=ansible

# Included per-composition from main.yaml for state: stopped and state: absent.
# Non-present compositions never enter their composition-* role, so everything
# needed is derived from the list item here.

- name: Set teardown facts
  ansible.builtin.set_fact:
    _td_name: "{{ item.composition | default(item) }}"
    _td_state: "{{ item.state | default('present') }}"
    _td_dataset: "{{ compositions_dataset | default('fastpool/compositions') }}"

- name: Stop composition containers
  community.docker.docker_compose_v2:
    project_src: "/{{ _td_dataset }}/{{ _td_name }}"
    state: "{{ 'absent' if _td_state == 'absent' else 'stopped' }}"
    remove_orphans: "{{ _td_state == 'absent' }}"
  failed_when: false

# ----------------------------
# state: absent only - park the dataset, never destroy it
# ----------------------------

- name: Check whether composition dataset still exists
  ansible.builtin.command: "zfs list -H -o name {{ _td_dataset }}/{{ _td_name }}"
  register: _td_ds
  changed_when: false
  failed_when: false
  when: _td_state == 'absent'

- name: Ensure graveyard dataset exists
  become: true
  community.general.zfs:
    name: "{{ _td_dataset | split('/') | first }}/graveyard"
    state: present
  when: _td_state == 'absent' and _td_ds.rc == 0

- name: Park composition dataset in graveyard
  become: true
  ansible.builtin.command: >-
    zfs rename {{ _td_dataset }}/{{ _td_name }}
    {{ _td_dataset | split('/') | first }}/graveyard/{{ _td_name }}
  when: _td_state == 'absent' and _td_ds.rc == 0
```

`zfs rename` is atomic, preserves every snapshot, and moves the mountpoint (composition datasets inherit theirs, so it follows automatically). It fails loudly if the dataset is still busy — a safe failure, not data loss.

The `zfs list` check makes `absent` idempotent: once parked, it returns non-zero and both dataset tasks skip. This matters because the `state: absent` entry stays in host_vars and re-runs on every playbook execution.

## Task 3: Give composition roles a state default

- [ ] **Step 1: Edit `roles/composition-common/defaults/main.yaml`**

Add at the top, so composition roles invoked directly from a `roles:` list always have `state` defined:

```yaml
state: present
```

Leave `roles/composition-common/tasks/main.yaml` **unchanged** — non-present compositions never enter the role, so its dataset-creation tasks are never reached during a teardown.

## Task 4: Revert composition-loki to its pre-state form

- [ ] **Step 1: Edit `roles/composition-loki/tasks/main.yaml`**

Remove the two `state: absent` tasks (`Stop and remove Docker Compose project`, `Remove Loki config directory`) and strip the `when: state == 'present'` guard from every remaining task. Teardown is centralised now, and the `system-compositions` split is what stops loki reaching this role at all.

- [ ] **Step 2: Confirm `roles/composition-loki/defaults/main.yaml` keeps `state: present`**

Harmless and consistent with the `composition-common` default; leave it.

## Task 5: Verify

- [ ] **Step 1: No-op regression on present-state compositions**

```bash
ansible-playbook playbooks/hosts/server-64gb-storage/core.yaml --check --tags composition
```

Present-state compositions must show no changes — confirms the loop split did not alter deploy behaviour.

- [ ] **Step 2: Capture loki's snapshot count before running**

```bash
ssh server-64gb-storage 'zfs list -t snapshot -r fastpool/compositions/loki | wc -l'
```

- [ ] **Step 3: Run the absent path for loki**

loki is already marked `state: absent` in `inventory/host_vars/server-64gb-storage/core.yaml`.

```bash
ansible-playbook playbooks/hosts/server-64gb-storage/core.yaml \
  --tags composition -e target_composition=loki
```

- [ ] **Step 4: Verify the dataset was parked, not destroyed**

```bash
ssh server-64gb-storage 'zfs list fastpool/compositions/loki'          # must NOT exist
ssh server-64gb-storage 'zfs list fastpool/graveyard/loki'             # must exist
ssh server-64gb-storage 'zfs list -t snapshot -r fastpool/graveyard/loki | wc -l'
```

The snapshot count must match Step 2. Any drop means snapshots were lost — stop and investigate.

- [ ] **Step 5: Verify idempotency**

Re-run the Step 3 command. Must report no changes and no errors.

- [ ] **Step 6: Verify the graveyard is invisible to pruning**

Confirm no `fastpool/graveyard/*` dataset appears in the prune target list:

```bash
ssh server-64gb-storage 'sudo /opt/zfs-policy/zfs-prune.py --dry-run 2>&1 | grep -i graveyard'
```

Expect no output.

- [ ] **Step 7: Test `state: stopped` on a low-risk composition**

Set one to `state: stopped`, run, then confirm `docker ps` no longer lists it while `zfs list` still shows its dataset under `fastpool/compositions` with snapshots intact. Revert to `present` and confirm it redeploys cleanly.

## Task 6: Commit

- [ ] **Step 1: Stage and review**

```bash
git add roles/system-compositions/ roles/composition-common/defaults/main.yaml roles/composition-loki/tasks/main.yaml
git status
```

- [ ] **Step 2: Commit (pre-commit runs automatically)**

```bash
git commit -m "compositions: add state: stopped and state: absent teardown"
```

---

## Files

| File | Change |
|---|---|
| `roles/system-compositions/tasks/main.yaml` | Split loop into deploy vs teardown by state |
| `roles/system-compositions/tasks/teardown.yaml` | **New** — stop, and park dataset on `absent` |
| `roles/composition-common/defaults/main.yaml` | Add `state: present` |
| `roles/composition-loki/tasks/main.yaml` | Revert to pre-`state` form |
| ~39 `roles/composition-*/tasks/main.yaml` | **Unchanged** |

## Edge cases

| Case | Handling |
|---|---|
| Compose dir missing / never deployed | `failed_when: false` on the stop task |
| Dataset already parked | `zfs list` check → rename skipped; idempotent |
| Dataset busy (container still running) | `zfs rename` fails loudly; nothing destroyed |
| Host without ZFS | `zfs list` returns non-zero → all dataset tasks skip |
| Name collision in graveyard | `zfs rename` fails rather than overwriting |
| Host with `compositions_dataset: slowpool/compositions` | Pool derived via `split('/') \| first` → `slowpool/graveyard` |
| Docker network `guineanet` | Never touched; shared across compositions |
