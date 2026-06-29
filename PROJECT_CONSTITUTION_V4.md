# PROJECT_CONSTITUTION_V4.md

## Version: 4.0

## Status: Supreme Authority

## Classification: Constitutional Governance Document

---

# PREAMBLE

This Constitution governs the architecture, contracts, capabilities, verification systems, and enforcement mechanisms of the project.

The purpose of this Constitution is not to define implementation.

The purpose of this Constitution is to preserve verified decisions, architectural integrity, ownership boundaries, and historical guarantees while allowing controlled evolution of the system.

All project work shall comply with this Constitution.

---

# ARTICLE 0

# CONSTITUTIONAL SUPREMACY

This Constitution is the highest authority within the repository.

All lower authorities derive legitimacy from this Constitution.

When conflicts occur:

Constitution > Authorities > Verification > Implementation

Implementation shall never redefine authority.

Verification shall never redefine requirements.

---

# ARTICLE I

# DEFINITIONS

For the purposes of this Constitution:

### Architecture

The structural organization of ownership, responsibilities, and dependencies.

### Contract

A versioned agreement defining behavior, interfaces, payloads, or guarantees.

### Gate

A verified requirement that must pass before work may be accepted.

### Protected Asset

A system designated as constitutionally protected.

### Source of Truth

The sole authoritative owner of a specific category of information.

### Regression

Any weakening, removal, bypass, contradiction, duplication, or invalidation of a previously verified guarantee.

### Refactor

A structural modification that produces no externally observable behavioral change.

### Feature Change

Any modification that alters behavior, capability, contract, workflow, or observable outcomes.

### Constitutional Violation

Any change that conflicts with constitutional authority regardless of functionality.

---

# ARTICLE II

# AUTHORITY HIERARCHY

Level 1

PROJECT_CONSTITUTION_V4.md

Level 2

AGENTS.md

ARCHITECTURE_ENFORCEMENT.md

Level 3

ARCHITECTURE.md

ai_command_center/core/contracts.py

ai_command_center/core/events/topics.py

Level 4

Phase Documents (gate history in ARCHITECTURE.md)

Level 5

Verification Framework

Level 6

Implementation

No lower authority may contradict a higher authority.

Silence does not imply permission.

---

# ARTICLE III

# CONSTITUTIONAL INVARIANTS

The following invariants are permanent unless amended.

### Invariant 1

Ownership Flow

UI

v

AppState

v

EventBus

v

Services

v

Repositories

v

Storage

No shortcut path is permitted.

### Invariant 2

UI Isolation

UI renders state.

UI publishes intent.

UI owns no business logic.

### Invariant 3

EventBus Governance

Runtime communication occurs through canonical EventBus contracts.

### Invariant 4

AppState Governance

AppState owns presentation state.

Services own operational state.

### Invariant 5

Repository Ownership

Repositories exclusively own persistence.

### Invariant 6

Context Pipeline

All AI requests pass through ContextManager.

### Invariant 7

Contract Governance

Versioned contracts are protected assets.

### Invariant 8

Topic Governance

Canonical topics are authoritative.

### Invariant 9

Telemetry Firewall

Telemetry observes.

Telemetry never influences runtime behavior.

### Invariant 10

Verification Integrity

Verification validates requirements.

Verification does not create requirements.

### Invariant 11

Source-of-Truth Integrity

Each information domain shall have exactly one authoritative owner.

### Invariant 12

Constitutional Non-Circumvention

No mechanism may bypass constitutional requirements through indirection, temporary exceptions, wrappers, aliases, compatibility layers, or migration paths.

---

# ARTICLE IV

# PROTECTED ASSETS

## Tier A - Constitutional Assets

Modification requires constitutional amendment.

- EventBus Architecture
- AppState Projection System
- ContextManager Pipeline
- Repository Ownership Model
- Contract Registry
- Topic Registry
- Verification Framework
- UCGS Framework
- Architecture Enforcement System

## Tier B - Architectural Assets

Modification requires architectural review.

- Settings System
- Plugin Runtime
- Tool Runtime
- Telemetry System
- Service Lifecycle Framework
- Capability Registry
- Phase Ledger

---

# ARTICLE V

# SOURCE OF TRUTH GOVERNANCE

Every information domain shall have one owner.

No duplicate authority may be introduced.

No shadow registry may be introduced.

No derived representation may become authoritative.

When ambiguity exists:

The documented source of truth wins.

---

# ARTICLE VI

# GATE PRESERVATION

Passed gates become protected project contracts.

A gate may only be:

- Extended
- Replaced
- Superseded

A gate may never silently disappear.

Superseded gates must record:

- Replacement gate
- Reason
- Date
- Approval record

---

# ARTICLE VII

# REGRESSION POLICY

Regression Budget:

ZERO

Allowed Regressions:

NONE

A task is incomplete if it:

- breaks a gate
- weakens an invariant
- duplicates ownership
- bypasses architecture
- invalidates a protected asset

even when functionality succeeds.

---

# ARTICLE VIII

# REFACTOR GOVERNANCE

A refactor shall:

- preserve behavior
- preserve contracts
- preserve ownership
- preserve gate validity

If behavior changes:

The work is a feature change.

Feature changes require full validation.

---

# ARTICLE IX

# SHORTCUT PROHIBITION

Temporary architecture is architecture.

Temporary ownership is ownership.

Temporary sources of truth are sources of truth.

A violation remains a violation regardless of intent.

---

# ARTICLE X

# CONSTITUTIONAL PRE-FLIGHT

Required before implementation.

Must include:

Task Description

Authorities Reviewed

Files Reviewed

Protected Assets Impacted

Sources of Truth Impacted

Architectural Invariants Impacted

Contracts Impacted

Gate Impact Assessment

Historical Gate Impact

Regression Risk

Constitutional Status

APPROVED

or

REVIEW REQUIRED

Implementation may not begin before pre-flight completion.

---

# ARTICLE XI

# CONSTITUTIONAL REVIEW TRIGGERS

Mandatory review is required when work affects:

- Ownership Flow
- EventBus contracts
- AppState design
- Repository boundaries
- ContextManager
- Contract versions
- Topic registry
- Verification framework
- Protected assets
- Sources of truth

Review is mandatory even if tests pass.

---

# ARTICLE XII

# ARCHITECTURAL EXCEPTION RECORD (AER)

Temporary exceptions are permitted only through a documented AER.

An AER must include:

- Exception description
- Justification
- Risk assessment
- Mitigation plan
- Expiration date
- Owner
- Removal strategy

Expired AERs become violations.

AERs may not alter constitutional invariants.

---

# ARTICLE XIII

# COMPLETION REQUIREMENTS

Required report:

Historical Gates:

PASS / FAIL

Current Task:

PASS / FAIL

Protected Assets:

PASS / FAIL

Sources of Truth:

PASS / FAIL

Constitutional Compliance:

PASS / FAIL

Regression Check:

PASS / FAIL

Final Status:

COMPLETE / INCOMPLETE

---

# ARTICLE XIV

# AMENDMENT PROCEDURE

Constitutional amendments require:

1. Written proposal.
2. Architectural review.
3. Updated authorities.
4. Updated verification.
5. Updated phase ledger.
6. Amendment record.
7. Explicit approval.

Implicit amendment is prohibited.

Verification-only amendment is prohibited.

Retroactive amendment is prohibited.

---

# ARTICLE XV

# BURDEN OF PROOF

The default position is:

DO NOT MODIFY VERIFIED SYSTEMS.

The burden of proof belongs to the proposed change.

The proposed change must demonstrate:

- necessity
- safety
- constitutional compliance
- architectural compliance
- contract compliance
- gate compliance
- source-of-truth compliance

before implementation.

---

# ARTICLE XVI

# CONSTITUTIONAL VIOLATION OVERRIDE

A change shall be rejected immediately if it:

- passes tests but violates architecture
- passes gates but weakens protected assets
- passes validation but duplicates ownership
- passes verification but bypasses contracts
- passes functionality but creates constitutional debt

because:

Architecture > Features

Contracts > Convenience

Governance > Implementation

Constitution > Everything

---

# ARTICLE XVII

# AUDIT RECORD — 2026-06-29

## Source

External architectural audit (AUDIT.md) conducted by a Principal Software Engineer against the full codebase snapshot.

## Findings Verified

### Finding 1 — Dead Code Shim [HIGH — RESOLVED]

`ai_command_center/db/repository.py` contained a `ConversationRepository` class whose sole purpose was to emit a deprecation warning and lazily re-export the real class from `ai_command_center.db.conversation_repository`.

**Resolution:** Class deleted. `db/__init__.py` updated. No consumers used the shim path.

### Finding 2 — Bloated Composition Root [HIGH — RESOLVED]

`application.py` manually imported and instantiated every service (~20+), making it a merge conflict bottleneck that violated the Open/Closed Principle.

`ui/app.py` `_ensure_view()` contained a 40-line `if/elif` chain manually instantiating every view.

**Resolution:**

- All repository and service wiring extracted to `ai_command_center/core/service_factory.py` (`build_services()`). Adding a new service now requires editing only `service_factory.py`.
- `_ensure_view` replaced with a `_view_registry` dict of factory callables populated in `_register_views()`. Adding a new view requires adding one entry there.
- `application.py` reduced from 182 lines to 67 lines.

### Finding 3 — Asyncio Threading Leak [MEDIUM — RESOLVED]

`OllamaHttpService._on_unload` dispatched `_shutdown_loop()` as a fire-and-forget coroutine with no `.result()` wait. If the process exited before the coroutine completed, the background asyncio thread became a zombie.

**Resolution:** `_on_unload` now calls `.result(timeout=5.0)` on the shutdown future before joining the thread, ensuring the loop is fully stopped before references are nullified.

### Finding 4 — Aggressive UI Polling [MEDIUM — RESOLVED]

`UIQueue` used a hardcoded 50ms unconditional recursive `.after()` loop that fired every 50ms regardless of queue activity, wasting CPU cycles on ARM64 when idle.

**Resolution:** `UIQueue` refactored to use Tkinter virtual event `<<UIQueueItem>>`. `enqueue()` posts the event via `event_generate(..., when="tail")`; the main thread wakes only when work arrives. A 200ms fallback poll handles startup edge cases.

## Architectural Decisions

The following are now constitutional:

1. **Service wiring belongs in `core/service_factory.py`**, not `application.py`. `application.py` is a thin orchestrator only.
2. **View instantiation belongs in `_register_views()`** via the `_view_registry` dict. `_ensure_view` must not contain instantiation logic.
3. **`UIQueue` must remain event-driven.** Reintroducing unconditional polling at intervals ≤ 100ms is prohibited without AER.
4. **Deprecated import shims are prohibited.** Classes that only re-export another class are dead code and must be deleted at point of discovery.
5. **`asyncio.run_coroutine_threadsafe` calls that manage lifecycle shutdown must await `.result()` with a timeout** before joining the associated thread.

## Verification

All 29 existing tests passed after refactoring with no behavioral change. This work is classified as a Refactor per Article I.

---

# FINAL PRINCIPLE

The project is not code.

The project is the collection of verified architectural decisions, contracts, guarantees, ownership boundaries, capabilities, enforcement systems, and historical evidence accumulated through validation.

Code may change.

Implementation may change.

UI may change.

Architecture may evolve.

Constitutional guarantees shall not be weakened without deliberate, documented, reviewed, and verifiable amendment.
