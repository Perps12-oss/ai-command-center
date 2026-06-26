> # ⬜ TO-DO LIST
>
> **Status: TO-DO LIST — not yet implemented.**
>
> This document is the approved Workspace OS Reference Architecture v3.5. It is
> tracked here as a **to-do list**: the architectural principles, domain models,
> and subsystems below are the target design to build out. Everything in the
> checklist is currently unchecked (planned / outstanding).

---

# TO-DO Checklist (derived from the reference architecture)

## Architectural Principles (Part I)
- [ ] A1 — Context Before Conversation: consume available context (clipboard, workspace, selections, memory, indexes, telemetry) before requesting conversational input
- [ ] A2 — Execution Before Explanation: prioritize safe execution over explanation (`Intent → Execute → Optional Explanation`)
- [ ] A3 — Workspace Before Window: treat apps/windows as telemetry; manage workspaces as entities
- [ ] A4 — Suggestion Before Prompting: reduce typing via suggestions + single-keystroke execution
- [ ] A5 — Determinism Before AI: resolution hierarchy `Direct Action → Indexed Lookup → Rule Engine → Retrieval → AI Reasoning`
- [ ] A6 — Context Persistence: workspace continuity survives transient context loss
- [ ] A7 — Instant Visibility: UI rendering never waits for telemetry acquisition
- [ ] A8 — Local-First Capability: core workflows function offline / air-gapped
- [ ] A9 — Progressive Disclosure: reveal complexity gradually

## Core Domain Model (Part II) — ✅ Phase 1 (delivered)
- [x] `TelemetrySnapshot` sensor object (timestamp, target_hwnd, app_name, window_title, clipboard_text) — `ai_command_center/workspace/domain.py`
- [x] `WorkspaceContext` primary domain object — `ai_command_center/workspace/domain.py`
- [x] Workspace Resolver (telemetry → stable work sessions, deterministic) — `ai_command_center/workspace/resolver.py`
- [x] `WorkspaceLease` persistence model (prevent accidental workspace collapse) — `ai_command_center/workspace/domain.py`

> Phase 1 also realizes **A5 (Determinism Before AI)** and **A6 (Context Persistence)** at the domain layer: identical evidence always resolves to the same `workspace_id`, and a lease retains the active workspace across transient low-evidence excursions. Gate: `scripts/verify_workspace_phase1.py`.

## Context Acquisition Architecture (Part III) — ✅ Phase 3 (delivered)
- [x] Reliability-first acquisition hierarchy: Clipboard → Explicit Input → Workspace Indexes → Known Integrations → UI Automation — `ContextSource` in `ai_command_center/workspace/context_acquisition.py`
- [x] Higher-ranked sources supersede lower; UI Automation optional — `ContextAcquirer.acquire()` (supersede merge; UI Automation excluded unless `include_ui_automation=True`)

> Phase 3 is **pull-based** (no background polling / auto-ingestion): context is gathered only when `acquire()` is called. Providers are injected so the core stays pure and platform-agnostic; OS-specific readers (clipboard, UI automation) are thin adapters supplied later. A failing provider is isolated so core functionality works without UI Automation. Gate: `scripts/verify_workspace_phase3.py`.

## Intent Resolution Architecture (Part IV) — ✅ Phase 2 (delivered)
- [x] `ResolutionCandidate` (score, target, source) — `ai_command_center/workspace/intent.py`
- [x] Confidence policy: ≥0.90 auto-execute, 0.50–0.90 suggest, <0.50 clarify — `classify()` / `ResolutionMode`
- [x] No subsystem silently executes ambiguous actions; all expose confidence — `IntentResolver` is classify-only; empty/low-confidence sets resolve to CLARIFY

> Phase 2 is pure and deterministic (A5): `IntentResolver` ranks candidates (strongest score first, ties by `source`) and applies the confidence policy without executing or invoking AI. Gate: `scripts/verify_workspace_phase2.py`.

## Runtime Lifecycle (Part V) — ✅ Phase 6 (delivered)
- [x] Phase 0A — Invocation (no blocking ops modeled in the pipeline) — `LifecyclePhase.INVOCATION`
- [x] Phase 0B — Context Acquisition (clipboard/index/integration; UI Automation optional) — `RuntimePipeline.run()` → `ContextAcquirer`
- [x] Phase 1 — Hydration (suggestions generated before AI) — `SuggestionEngine.suggest()`
- [x] Phase 2 — Intent Resolution (deterministic; exposes confidence) — `IntentResolver.resolve()`
- [x] Phase 3 — Execution (structured action results) — only for `AUTO_EXECUTE` action-bearing intents
- [x] Phase 4 — Delivery (dispatch results to targets) — `ActionDispatcher.dispatch()`

> Phase 6 is a pure, deterministic state machine in `ai_command_center/workspace/lifecycle.py` that wires the prior layers (Parts III/IV/VI/VII). Collaborators are injected; ambiguous (suggest/clarify) intents never silently execute. Gate: `scripts/verify_workspace_phase6.py`.

## Action Architecture (Part VI) — ✅ Phase 4 (delivered)
- [x] `ActionResult` base type — `ai_command_center/workspace/actions.py`
- [x] Standard action types: `TextInsertion`, `OpenFile`, `LaunchApplication`, `RunCommand`, `CreateNote` (frozen)
- [x] `OutputTarget.dispatch()` interface + `ActionDispatcher` (routes to first accepting target, isolates failures)
- [x] Output targets: pluggable via injected `CallableTarget` adapters (SendInput, Clipboard, Obsidian, Shell, Browser, VSCode supplied by higher layers)

> Phase 4 is pure — no OS side effects in this layer; real delivery (SendInput/shell/Obsidian/...) is injected. Gate: `scripts/verify_workspace_phase4.py`.

## Suggestion Engine (Part VII) — ✅ Phase 5 (delivered)
- [x] Generate suggestions before AI reasoning whenever possible — `SuggestionEngine` (deterministic, rule-based; e.g. Python-traceback → Explain Error / Create Issue / Search Notes / Save Snippet)
- [x] Minimize typing / routing friction / unnecessary AI invocation — pre-AI rules over `AcquiredContext`; no AI calls

> Phase 5 is pure and deterministic in `ai_command_center/workspace/suggestions.py`; ranking is stable (score, then label, then rule). Gate: `scripts/verify_workspace_phase5.py`.

## Plugin Architecture (Part VIII) — ✅ Phase 7 (delivered)
- [x] `CommandPlugin` contract (name, priority, match, enrich_context, execute) — `ai_command_center/workspace/plugins.py`
- [x] Plugin location `%APPDATA%\AICommandCenter\plugins\` (documented; discovery/loading is a runtime concern, not this pure layer)
- [x] Tier 1 exclusive matching (highest priority match wins) — `PluginRegistry.select()` (ties by name; faulty plugins isolated)

> Phase 7 is pure/deterministic; pipeline enrichment is supported for context only (`PluginRegistry.enrich()`), never fan-out execution. Gate: `scripts/verify_workspace_phase7.py`.

## Memory Architecture (Part IX) — ✅ Phase 8 (delivered)
- [x] Workspace-centric memory (workspace/task/execution history, file & note relationships, preferences) — `WorkspaceMemory` in `ai_command_center/workspace/memory.py`
- [x] Conversation history secondary — `WorkspaceMemory.conversation` (separate from primary entities)

> Phase 8 is an immutable in-memory model (`with_*` returns new instances; `MemoryStore` keyed by `workspace_id` for cross-session continuity). Persistence (SQLite) is a repository concern. Gate: `scripts/verify_workspace_phase8.py`.

## AI Reasoning Subsystem (Part X) — ✅ Phase 9 (delivered)
- [x] AI as supporting subsystem only (does not own state/routing/execution/persistence) — `ReasoningEngine` boundary in `ai_command_center/workspace/reasoning.py`
- [x] Responsibilities: summarization, classification, transformation, planning, context expansion — `ReasoningTask`; in: `ReasoningRequest` (context/intent/knowledge), out: `ReasoningResponse` (ActionResults/structured/suggestions)

> Phase 9 defines the boundary as types + an injectable engine (concrete model call supplied later); it never executes or persists. Gate: `scripts/verify_workspace_phase9.py`.

## Product North Star (Part XII)
- [ ] Flow: `User → Command Palette → Workspace Context → Tools/Memory/Automation → AI (when needed) → Execution`

---

# WORKSPACE OS REFERENCE ARCHITECTURE v3.5

**System Name:** AI Command Center

**Classification:** Local-First AI-Powered Workspace Operating Layer

**Authority Source:** PROJECT_CONSTITUTION_V3

**Document Type:** Architecture Authority Document

**Status:** Approved Architectural Baseline

**Scope:** Domain Models, Runtime Architecture, State Management, Context Systems, Execution Systems, User Interaction Patterns, and Architectural Constraints

**Target Platform:** Windows ARM64

**Governance Model:** UCGS v5

---

# Authority Statement

This document derives authority from PROJECT_CONSTITUTION_V3.

This document is not a constitutional document.

This document defines the approved reference architecture for AI Command Center and serves as the authoritative source for:

* System architecture
* Runtime behavior
* Core domain models
* State management patterns
* Architectural constraints
* Subsystem responsibilities

This architecture may evolve through evidence-driven governance without requiring constitutional amendment, provided constitutional requirements remain satisfied.

---

# Authority Hierarchy

```text
PROJECT_CONSTITUTION_V3
    Supreme Authority

        ↓

WORKSPACE_OS_REFERENCE_ARCHITECTURE_V3.5
    Architecture Authority

        ↓

PHASE_LEDGER
    Delivery Authority

        ↓

FROZEN_CONTRACTS
    Interface Authority

        ↓

IMPLEMENTATION
    Execution Authority
```

In the event of conflict:

Higher-authority documents supersede lower-authority documents.

---

# Executive Definition

AI Command Center is not a chatbot.

AI Command Center is a workspace operating layer.

Its purpose is to reduce the distance between:

```text
Intent
↓
Execution
```

The command palette is the primary interface.

Workspace Context is the primary architectural object.

Tools perform actions.

Memory preserves continuity.

AI performs reasoning when deterministic systems are insufficient.

Success is measured by reduction of friction rather than conversational quality.

---

# Part I — Architectural Principles

These principles define the approved reference architecture.

They derive authority from PROJECT_CONSTITUTION_V3 and may evolve through architectural governance processes.

---

## A1 — Context Before Conversation

The system must consume available context before requesting conversational input.

Context sources include:

* Clipboard state
* Workspace state
* User selections
* Historical workspace memory
* Indexed local content
* Application telemetry

Conversation is a fallback mechanism.

---

## A2 — Execution Before Explanation

When a task can be safely executed, execution should be prioritized over explanation.

Preferred flow:

```text
Intent
↓
Execute
↓
Optional Explanation
```

---

## A3 — Workspace Before Window

Applications and windows are telemetry sources.

Workspaces are managed entities.

The system reasons about ongoing work rather than isolated software.

---

## A4 — Suggestion Before Prompting

The system should reduce typing whenever sufficient confidence exists.

Preferred interaction:

```text
Alt+Space
↓
Suggestions
↓
Single Keystroke
↓
Execution
```

---

## A5 — Determinism Before AI

Tasks should be solved using the most deterministic mechanism available.

Resolution hierarchy:

```text
Direct Action
↓
Indexed Lookup
↓
Rule Engine
↓
Retrieval
↓
AI Reasoning
```

AI is a reasoning layer.

AI is not the default execution layer.

---

## A6 — Context Persistence

Workspace continuity must survive temporary context loss.

Workspace identity should not collapse because the user briefly changes applications.

Human work is persistent.

Window focus is transient.

---

## A7 — Instant Visibility

User interface rendering must never wait for telemetry acquisition.

Required behavior:

```text
Alt+Space
↓
Palette Appears
↓
Context Arrives
↓
UI Updates
```

---

## A8 — Local-First Capability

Core workflows must function without internet connectivity.

The system should remain fully operational:

* Offline
* Air-gapped
* During network outages

Cloud services may enhance functionality.

They must not be required for primary workflows.

---

## A9 — Progressive Disclosure

Complexity should be revealed gradually.

New users should experience:

```text
Command
↓
Result
```

Power users may access:

```text
Plugins
Automation
Memory
Advanced Routing
Workspace Controls
```

without increasing baseline complexity.

---

# Part II — Core Domain Model

---

## TelemetrySnapshot

TelemetrySnapshot represents a point-in-time observation of the operating environment.

It is a sensor object.

It is not the primary architectural entity.

```python
@dataclass(frozen=True)
class TelemetrySnapshot:
    timestamp: float

    target_hwnd: int

    app_name: str

    window_title: str

    clipboard_text: str
```

---

## WorkspaceContext

WorkspaceContext is the current primary domain object of the reference architecture.

Future architectural revisions may refine or replace this model if supported by operational evidence.

```python
@dataclass
class WorkspaceContext:
    workspace_id: str

    title: str

    inferred_task: str

    active_snapshot: TelemetrySnapshot

    active_files: list[str]

    recent_snapshots: list[str]

    memory_refs: list[str]

    metadata: dict
```

---

## Workspace Resolver

The Workspace Resolver transforms telemetry into stable work sessions.

Initial evidence sources:

* Repository roots
* Active folders
* Obsidian vaults
* Recent files
* Known integrations

Future evidence sources:

* Activity clustering
* Semantic relationships
* Workspace embeddings
* Behavioral patterns

---

## Workspace Lease

Workspace persistence is implemented through a lease model.

```python
@dataclass
class WorkspaceLease:
    workspace_id: str

    confidence: float

    expires_at: float
```

Purpose:

Prevent accidental workspace collapse during transient context transitions.

---

# Part III — Context Acquisition Architecture

The platform uses a reliability-first acquisition hierarchy.

```text
Priority 1
Clipboard

Priority 2
Explicit User Input

Priority 3
Workspace Indexes

Priority 4
Known Integrations

Priority 5
UI Automation
```

Rules:

* Higher-ranked sources supersede lower-ranked sources.
* UI Automation is optional.
* Core functionality must remain operational without UI Automation.

---

# Part IV — Intent Resolution Architecture

All resolution systems must expose confidence.

No subsystem may silently execute ambiguous actions.

---

## ResolutionCandidate

```python
@dataclass(frozen=True)
class ResolutionCandidate:
    score: float

    target: object

    source: str
```

---

## Confidence Policy

### Automatic Execution

```text
Score ≥ 0.90
```

Action executes immediately.

---

### Suggestion Mode

```text
0.50 ≤ Score < 0.90
```

Suggestions displayed.

---

### Clarification Mode

```text
Score < 0.50
```

User clarification required.

---

# Part V — Runtime Lifecycle

---

## Phase 0A — Invocation

Immediately on:

```text
Alt+Space
```

System:

```text
Creates Palette
Shows Window
Focuses Input
```

No blocking operations permitted.

---

## Phase 0B — Context Acquisition

Executed asynchronously.

Tasks include:

* Clipboard capture
* Telemetry capture
* Workspace resolution
* Suggestion generation

---

## Phase 1 — Hydration

UI progressively updates as information becomes available.

Hydrated elements include:

* Workspace badges
* Context badges
* Suggestions
* Recent activity

---

## Phase 2 — Intent Resolution

Intent Router evaluates:

* Commands
* Searches
* Plugins
* Automations
* AI requests

Deterministic handlers receive priority.

---

## Phase 3 — Execution

Execution Engine produces structured action results.

---

## Phase 4 — Delivery

Execution results are dispatched to destination targets.

---

# Part VI — Action Architecture

The system operates on actions rather than text.

---

## ActionResult

```python
class ActionResult:
    pass
```

---

## Standard Action Types

```python
@dataclass(frozen=True)
class TextInsertion(ActionResult):
    text: str

@dataclass(frozen=True)
class OpenFile(ActionResult):
    path: Path

@dataclass(frozen=True)
class LaunchApplication(ActionResult):
    executable: str

@dataclass(frozen=True)
class RunCommand(ActionResult):
    command: str

@dataclass(frozen=True)
class CreateNote(ActionResult):
    title: str
    content: str
```

Additional action types may be introduced through architectural governance.

---

## OutputTarget

```python
class OutputTarget:

    def dispatch(
        self,
        result: ActionResult
    ) -> bool:
        raise NotImplementedError
```

Examples:

* SendInputTarget
* ClipboardTarget
* ObsidianTarget
* ShellTarget
* BrowserTarget
* VSCodeTarget

---

# Part VII — Suggestion Engine

The Suggestion Engine exists to minimize interaction cost.

Suggestions are generated before AI reasoning whenever possible.

Example:

```text
Context:
Python Traceback

Suggestions:

Explain Error
Create Issue
Search Notes
Save Snippet
```

Success metric:

Reduce typing.

Reduce routing friction.

Reduce unnecessary AI invocation.

---

# Part VIII — Plugin Architecture

Plugins extend platform behavior without modifying core platform code.

Location:

```text
%APPDATA%\AICommandCenter\plugins\
```

---

## Plugin Contract

```python
class CommandPlugin:

    @property
    def name(self) -> str:
        ...

    @property
    def priority(self) -> int:
        ...

    def match(
        self,
        context: WorkspaceContext
    ) -> bool:
        ...

    def enrich_context(
        self,
        context: WorkspaceContext
    ) -> WorkspaceContext:
        ...

    def execute(
        self,
        context: WorkspaceContext
    ):
        ...
```

---

## Approved Execution Model

### Tier 1

Exclusive Matching

```text
Highest Priority Match Wins
```

Provides:

* Determinism
* Simplicity
* Predictability

---

### Future Evolution

Pipeline enrichment may be introduced for context augmentation.

Example:

```text
Plugin A
↓
Plugin B
↓
Plugin C
```

Only for enrichment.

Not execution.

---

### Outside Approved Baseline

Fan-out execution models are not part of the approved reference architecture.

---

# Part IX — Memory Architecture

Memory is workspace-centric.

Conversation history is secondary.

Primary memory entities:

* Workspace history
* Task history
* Execution history
* File relationships
* Note relationships
* User preferences

Purpose:

Maintain continuity across sessions.

---

# Part X — AI Reasoning Subsystem

AI is a supporting subsystem.

AI does not own:

* State
* Routing
* Execution
* Persistence

AI responsibilities:

* Summarization
* Classification
* Transformation
* Planning
* Context expansion

Inputs:

```text
WorkspaceContext
Intent
Retrieved Knowledge
```

Outputs:

```text
ActionResults
Structured Responses
Suggestions
```

---

# Part XI — Architectural Evolution

This document intentionally defines a reference architecture rather than immutable implementation requirements.

Architectural components may evolve when supported by evidence.

Changes are permitted when:

* Constitutional requirements remain satisfied.
* Phase requirements remain satisfied.
* Frozen contracts are honored or formally migrated.
* Replacement designs provide equal or greater capability.

Architecture exists to serve the product.

Architecture is not an end state.

---

# Part XII — Product North Star

The target user experience is:

```text
User
↓
Command Palette
↓
Workspace Context
↓
Tools / Memory / Automation
↓
AI Reasoning (When Needed)
↓
Execution
```

Not:

```text
User
↓
Chat
↓
AI
↓
Execution
```

The long-term goal is for users to stop thinking about:

```text
Prompts
Models
Agents
Chats
```

and instead think:

```text
Press Alt+Space
State intent
Receive result
```

---

## Architectural Closing Statement

This document establishes the approved Workspace OS Reference Architecture for AI Command Center.

Authority derives from PROJECT_CONSTITUTION_V3.

This architecture serves as the baseline for:

* Phase planning
* Contract design
* Subsystem development
* Verification activities

Future architectural evolution is expected.

Constitutional compliance is required.

Evidence-driven improvement is encouraged.

The architecture exists to transform AI Command Center from an AI application into a true workspace operating layer.
