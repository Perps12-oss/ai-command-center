# Repository Backlog

**STATUS:** RESEARCH / CLASS B — **not product Queue 1**

Candidate repositories for the ACC Engineering Intelligence Program. Research is **descriptive, never prescriptive** (`research/CONSTITUTION.md`).  
Goose / external patterns are **Stream F** (Integration Proposal + ADR; not Goose compatibility). Do **not** implement product work from this table.

Canonical product queue: [`docs/governance/IMPLEMENTATION_GUIDE.md`](../docs/governance/IMPLEMENTATION_GUIDE.md) (Strategic Runtime Program).

| Priority | Repository | Language | Subsystems of Interest | Assigned Expedition ID | Notes |
|----------|------------|----------|------------------------|------------------------|-------|
| High | Goose | Rust | Desktop runtime, provider abstraction, extensions | exp-001 | Pilot completed — see registry; operational tree `exp-001-goose` |
| High | OpenHands | Python | Multi-agent orchestration, sandboxing, coding agents | exp-002 | ID reserved in registry (Queued) |
| High | LibreChat | TypeScript | Multi-provider chat, MCP, memory, UI | exp-003 | ID reserved in registry (Queued) |
| Medium | PyGPT | Python | Desktop UI, local LLM integration | exp-004 | ID reserved in registry (Queued) |
| Medium | Logseq | Clojure / JS | Knowledge graph, local-first notes | exp-005 | ID reserved in registry (Queued) |
| Medium | Obsidian | JS / Electron | Plugin system, vault model | exp-006 | Ecosystem, not core repo; ID reserved |
| Medium | React Flow | TypeScript | Graph visualisation | exp-007 | If ACC moves to web frontend |
| Medium | Cytoscape.js | JS | Graph visualisation | exp-008 | ID reserved in registry (Queued) |
| Medium | ElkJS | TypeScript | Graph layout | exp-009 | ID reserved in registry (Queued) |
| Low | Yjs | JavaScript | CRDT / collaboration | exp-010 | ID reserved in registry (Queued) |
| Low | Automerge | Rust/JS | CRDT / collaboration | exp-011 | ID reserved in registry (Queued) |
| Low | VS Code | TypeScript | Plugin architecture, command palette | exp-012 | ID reserved in registry (Queued) |
| Low | Ollama | Go | Local AI runtime, model management | exp-013 | ID reserved in registry (Queued) |

## How to add a repository

1. Add a row to this table **and** reserve the next free `exp-NNN` ID in `repositories/index.md` (same commit).
2. Assign a priority based on ACC roadmap needs.
3. **IDs are reserved at registry creation** and remain the stable identity through Queued → In Progress → Validated. Do not renumber when an expedition starts.
4. When work begins, set status to `In Progress` in `repositories/index.md` and create `repositories/{exp-NNN}-{repo-name}/`.
