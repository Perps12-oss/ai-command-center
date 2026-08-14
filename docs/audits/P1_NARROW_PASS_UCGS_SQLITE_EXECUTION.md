# P1 Narrow Pass — UCGS CI Gate, Shared SQLite Transactions, Execution Boundary

**Status:** SUPERSEDED for remediation tracking — fixes landed on `cursor/p1-remediation-ucgs-efe6`; see `docs/audits/P1_REMEDIATION_LEDGER.md`  
**Date:** 2026-08-12  
**Baseline:** `origin/main` @ `ec34287` (verification); remediation follows on later tip  
**Scope:** Narrow pass only. Not a repo-wide re-audit. No product code changed **in the verification PR**.  
**Method:** Static proof + local reproduction (`write_local=False` for UCGS; throwaway DB under `/tmp` for SQLite). Test suite and `tools/ucgs_runner.py` default write path not used against the working tree.

**Verdict:** All three P1 surfaces **CONFIRMED**. UCGS CI architecture gate is inert. Shared-connection transaction ownership is broken for unlocked writers. The falsified `alias→TOOL_INVOKE` narrative must be dropped; the adjacent real problem is a live unreceipted ActionRegistry execution path (plus a related permission hole on `workspace_execute_command`).

---

## 1. UCGS CI gate is inert

### 1.1 Why (exact mechanism)

`tools/ucgs_runner.py` collects the change set exclusively via:

```text
git diff --cached --name-only
git diff --cached
```

(`_collect_git_diff`, lines 40–55.)

In GitHub Actions, `actions/checkout@v4` leaves a clean index equal to `HEAD`. The staged diff is therefore **always empty**. All four checks receive `changed_files=[]` and `diff_text=""`, emit zero violations, and the runner reports:

```text
verdict: PASS
risk_level: S1
report_complete: true
```

`tools/ucgs_ci_gate.py` only blocks on `verdict ∈ {FAIL}` or `risk_level ∈ {S4,S5}`. An empty-diff PASS never blocks.

**Local reproduction at this tip (empty index):**

| Observation | Result |
|-------------|--------|
| `git diff --cached --name-only` | empty |
| `run_ucgs(..., write_local=False)` | `PASS` / `S1` / 0 violations |
| Gate exit code | `0` |
| Same checks with a synthetic UI→`OllamaService` added line | `layer_imports` produces an S4 violation |

So the gate **can** FAIL when given a real diff; CI never supplies one.

### 1.2 The four checks

Registered in `tools/ucgs_runner.py` `CHECKS` / `context.checks_run`:

| Check | Module | Diff dependency |
|-------|--------|-----------------|
| `layer_imports` | `tools/ucgs_checks/layer_imports.py` | Scans **added** (`+`) lines in staged diff against profile layer rules |
| `forbidden_patterns` | `tools/ucgs_checks/forbidden_patterns.py` | Regex over **added** staged lines (secrets + profile scope creep) |
| `large_commit` | `tools/ucgs_checks/large_commit.py` | Counts staged files / added lines |
| `contract_drift` | `tools/ucgs_checks/contract_drift.py` | Fires only if a locked contract path appears in `changed_files` |

Profile data: `ucgs.profiles/ai-command-center.yaml` (UI→service S4, CommandRouter/ContextManager boundaries, S5 scope patterns, contract lock).

### 1.3 Every CI / hook invocation

| Surface | Invokes runner+gate? | Effective? |
|---------|----------------------|------------|
| `.github/workflows/ucgs.yml` — steps “Run UCGS v5 Gate” + “Evaluate Verdict” | Yes (`UCGS_ENFORCEMENT: block`) | **No** — empty staged diff |
| `tools/install_git_hooks.py` generated `.git/hooks/pre-commit` | Yes | **Yes locally** when files are staged before commit |
| `.cursor/hooks/ucgs-pre-commit.py` | Runs runner; **always `allow`** (`failClosed: false`) | Advisory only |
| `.github/workflows/tests.yml` | Does **not** run UCGS | N/A |
| `.github/workflows/tom-deep-audit.yml` | Runs `arch_lint` only | Advisory / different gate |

`ucgs.yml` also runs `scripts/verify_constitution.py` before UCGS — that is a separate full-tree gate (see §1.5).

### 1.4 Correct baseline / diff semantics

| Context | Correct input | Current behavior |
|---------|---------------|------------------|
| Local pre-commit | Staged index (`git diff --cached`) | Correct |
| Pull request CI | Three-dot diff vs base: `git diff --name-only origin/<base>...HEAD` + matching patch | Empty staged → inert |
| Push to `main` | Diff of pushed range (e.g. `HEAD~1...HEAD` or before/after SHAs) | Empty staged → inert |
| Optional CI mode | Full-tree scan (ignore diff scoping) | Not implemented |

Minimum remediation for CI: stop using `--cached` in non-interactive runs; prefer merge-base…HEAD for PRs (and document the mode in the report `context`). Do not weaken `UCGS_ENFORCEMENT: block`.

### 1.5 Secondary protections (what still works)

These are **not** substitutes for UCGS profile rules (scope-creep regexes, contract_drift, large_commit, profile layer paths), but they are live architecture-adjacent gates:

| Gate | Where | Scope |
|------|-------|-------|
| `scripts/arch_lint.py --baseline` | `tests.yml` (blocking) | Full-tree AST: R1–R5 (UI isolation, service wiring, AppState, service→service, ADR-018 sole `TOOL_INVOKE` publisher) |
| `scripts/verify_constitution.py` | `ucgs.yml` (blocking) | Authority files + UI AST imports + `shell=True` allowlist + legacy `db.*` imports |
| Local UCGS hook (if installed) | pre-commit | Staged diff — real UCGS coverage for human commits |

**Conclusion:** Claiming “no working CI architecture gate” overstates the secondary AST gates, but is correct for **UCGS itself**: the advertised CI architecture governance kit cannot FAIL on PRs/pushes today.

---

## 2. SQLite shared-connection transaction corruption

### 2.1 Composition root

One connection is created and passed to every repository in `build_services` (`ai_command_center/core/service_factory.py`):

```text
connect() → check_same_thread=False → connection_lock(conn) registered
         → Note / Memory / Conversation / Plugin / RuntimeProvider
         → Entity / Relationship / WorldModel / Goal / OperationIndex
         → Telemetry / ExecutionRun / ExecutionEvent / WorkflowRun / Artifact
         → Timeline / SnapshotService (workspace OS)
```

`ai_command_center/db/conn_sync.py` documents the intended rule: multi-statement work must hold `connection_lock(conn)` for execute→commit. The lock is **opt-in per caller**.

### 2.2 Map: locked vs unlocked on the shared connection

**Hold `connection_lock` (safe pattern when used for the whole critical section):**

- `ConversationRepository`, `MemoryRepository` (db impl via wrapper), `TelemetryRepository`
- `GoalRepository`, `ExecutionRunRepository`, `ExecutionEventRepository`, `ArtifactRepository`
- `TimelineRepository`

**Commit on the shared connection without `connection_lock` (HEAD):**

| # | Writer | Path | EventBus-hot? |
|---|--------|------|---------------|
| 1 | `NoteRepository` | `db/note_repository.py` (via `repositories/note_repository.py`) | Yes (Obsidian indexing) |
| 2 | `EntityRepository` | `core/entity/entity_repository.py` | Yes (entity bus handlers) |
| 3 | `RelationshipRepository` | `core/relationship/relationship_repository.py` | Yes |
| 4 | `SQLiteWorldModelRepository` | `repositories/world_model_repository.py` | Yes (`begin_transaction` / mutations) |
| 5 | `OperationIndexRepository` | `repositories/operation_index_repository.py` | Yes (indexer service) |
| 6 | `WorkflowRunRepository` | `repositories/workflow_run_repository.py` | Yes (persistence service) |
| — | `PluginManifestRepository` | `repositories/plugin_manifest_repository.py` | Mostly registry/startup |
| — | `RuntimeProviderManifestRepository` | `repositories/runtime_provider_manifest_repository.py` | Mostly registry/startup |
| — | `SnapshotService` | `core/snapshot/snapshot_service.py` | Workspace OS snapshots |

Independent Verification Audit’s “**six** live repositories” matches the EventBus-hot unlocked set (rows 1–6). HEAD also has three additional unlocked committers (Plugin, RuntimeProvider, Snapshot).

### 2.3 Every caller of the shared connection

Callers are whatever `build_services(db, …)` constructs with that `db` handle (list in §2.1). There is no second connection for those repositories. Services reach them via the wired instances; EventBus workers (`async_dispatch=True`) invoke handlers that write through those repositories concurrently.

### 2.4 Transaction ownership (actual vs intended)

| Intended | Actual |
|----------|--------|
| Per-repository critical sections own execute→commit under `connection_lock` | SQLite transaction state is **per connection**, not per repository or per thread |
| Lock serializes all writers | Only repositories that acquire the lock participate; unlocked writers interleave freely |
| `commit()` ends “my” unit of work | `conn.commit()` commits **whatever is open on that connection**, including another thread’s partial multi-statement work |

Highest-risk unlocked API: `SQLiteWorldModelRepository.begin_transaction()` (`BEGIN IMMEDIATE` … multi-statement … `commit`) with no lock.

### 2.5 How one thread commits another’s transaction (reproduced)

On a shared `check_same_thread=False` connection:

1. Thread A executes `INSERT … 'A_PARTIAL'` and does **not** commit (open transaction).
2. Thread B executes `INSERT … 'B_ONLY'` then `conn.commit()`.
3. Observer connection (separate) sees **both** `A_PARTIAL` and `B_ONLY` durable after step 2 — before A intends to commit.

Reproduced locally 2026-08-12 against this tip. Same pattern with `connection_lock` held for each thread’s full critical section serializes cleanly.

This is distinct from the falsified `id(conn)` instability claim: lock lookup by `id(conn)` is fine for a long-lived composition-root connection. The P1 is **incomplete lock adoption**, not key instability.

### 2.6 Minimum architectural boundary

One of:

1. **Connection-owned serialization (preferred minimum):** wrap the shared connection so `execute` / `executemany` / `executescript` / `commit` / `rollback` always take `connection_lock` — repositories cannot opt out; or  
2. **Exclusive connection ownership:** one writer connection + queue, or per-thread connections with WAL and no shared handle; or  
3. **Exhaustive lock adoption:** every write (and concurrent read) path on the shared conn acquires the lock for the full critical section — including `begin_transaction` — with an arch test forbidding unlocked `.commit(` on composition-root consumers.

(1) or (2) is the real boundary; (3) is a ratchet that has already failed twice (PR #88 partial coverage; later timeline/execution locks still left six hot writers unlocked).

### 2.7 Tests that should have caught it

| Test | Why it missed |
|------|----------------|
| `tests/test_sqlite_connection_threadsafe.py::test_concurrent_commits_on_shared_connection` | Only exercises the **locked** happy path; never mixes locked vs unlocked or unlocked vs unlocked multi-statement txns |
| `tests/test_brain_world_model.py` transaction tests | Single-threaded `begin_transaction` semantics only |
| No composition-root audit test | Nothing asserts every `build_services` writer imports/uses `connection_lock` |

A catching test would: share one `connect()` handle; have unlocked multi-statement writer A race unlocked (or locked) writer B’s `commit()`; assert A’s partial rows are **not** durable until A commits (or assert lock wrapper makes the race impossible).

---

## 3. Real P1 adjacent to falsified `alias→TOOL_INVOKE`

### 3.1 Drop the false narrative

**Do not retain:** any claim that `ACTION_INVOKE_*` / ActionRegistry is an “alias” that becomes `TOOL_INVOKE`, or that a symbolic alias chain routes ActionRegistry traffic into ADR-018’s sole publisher.

**Facts:**

- `TOOL_INVOKE = "tool.invoke"` and `ACTION_INVOKE_REQUEST = "action.invoke.request"` are **distinct** topics (`core/events/topics.py`).
- Sole publisher of `TOOL_INVOKE` remains `ExecutionOrchestratorService` (arch_lint R5).
- G2 re-routed `WorkspaceOsService._on_launch_resource` to `WORKFLOW_EXECUTION_REQUEST` → EA → tool step → `TOOL_INVOKE` (receipted path). That is a **replacement route**, not an alias.

### 3.2 Actual execution problem (P1)

**Live unreceipted OS side-effect path still installed:**

```text
bus.publish("action.invoke.request" | ACTION_INVOKE_REQUEST)
  → entity_bus_handlers.on_action_invoke_request
  → ActionRegistry.invoke(...)
  → frozen workspace_os_actions handlers
       webbrowser.open / os.startfile / subprocess.run(shell=False)
```

Evidence:

- Subscriber still registered: `entity_bus_handlers.py` (~L552–600).
- Handler still calls `action_registry.invoke` with launch actions registered from `workspace_os_actions.py`.
- `tests/test_receipt_coverage_gate.py::test_no_action_registry_launch_bypass` **exempts** `entity_bus_handlers.py` and admits a raw-string publisher of `"action.invoke.request"` would slip past.
- No remaining in-tree **symbol** publisher of `ACTION_INVOKE_REQUEST` (WorkspaceOsService was migrated) — but the **execution capability remains reachable** to any publisher of the topic string, plugins, or future regressions.

This is the opposite of “aliases into TOOL_INVOKE”: it is a **parallel execution authority** that never enters the receipt / TruthBoundary boundary ADR-018 and G2 require.

### 3.3 Adjacent security hole on the receipted TOOL_INVOKE path

While on the same surface (not an alias claim):

- `ToolExecutorService` registers builtin `workspace_execute_command` → frozen `_execute_command` → `subprocess.run`.
- Permission gate `_shell_allowed` / `Permission.LAUNCH_TOOL` runs **only** when `tool_name == "shell"` (`tool_executor_service.py` ~L323).
- Non-user actors can therefore obtain allowlisted command execution via `workspace_execute_command` without the permission check applied to `shell`.
- Sandbox allowlist still applies (`CommandSandbox`) — hardening gap, not arbitrary RCE — but it is a real permission-model bypass next to the TOOL_INVOKE work.

### 3.4 Minimum remediation direction (documentation only)

1. Remove or fail-closed the `ACTION_INVOKE_REQUEST` subscriber (or make it refuse launch actions and require TOOL_INVOKE).
2. Strengthen the tripwire: ban the topic **string**, do not exempt the handler, assert no `ActionRegistry.invoke` of launch handlers outside TOOL_INVOKE wrappers.
3. Apply the same permission gate to `workspace_execute_command` (and any future command-spawning builtins) as to `shell`.

---

## 4. False positives explicitly not reopened

| Claim | Disposition |
|-------|-------------|
| `id(conn)` lock-key instability as live P1 | **False positive** for the composition-root long-lived connection. Hygiene issue only if many short-lived conns close without `drop_connection_lock`. |
| `alias→TOOL_INVOKE` chain | **False positive** — see §3.1. |
| Reachable `drop_connection_lock` recursion | **False positive** — `drop_connection_lock` has **no callers**; it is dead hygiene code, not a recursion hazard. |

---

## 5. Safety call

**Do not continue feature implementation until:**

1. UCGS CI uses non-empty, correct PR/push diffs (or full-tree mode) so the four checks can FAIL under `UCGS_ENFORCEMENT: block`.  
2. Shared SQLite writers cannot commit another thread’s transaction (connection-level lock or non-shared writer model), covering at least the six EventBus-hot unlocked repositories.  
3. The ActionRegistry launch bypass is closed (and the `workspace_execute_command` permission hole is gated).

Secondary AST gates (`arch_lint`, `verify_constitution`) remain useful but do not cover UCGS profile rules or SQLite transaction ownership.

---

## 6. Out of scope

- Full test-suite health  
- Writing `.ucgs_last.yaml` into the repo via default runner  
- Remediation patches (this document is evidence only)
