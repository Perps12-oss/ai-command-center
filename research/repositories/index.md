# Repository Registry

**STATUS:** RESEARCH REGISTRY — **not product Queue 1**

Canonical list of repositories investigated by the ACC Engineering Intelligence Program (Class B).  
“Queued” here means **research expedition queued**, not product implementation. Goose extras remain **GATED** (Stage 3).

Product Queue 1: [`docs/governance/IMPLEMENTATION_GUIDE.md`](../docs/governance/IMPLEMENTATION_GUIDE.md) (**EMPTY**).

**ID lifecycle:** `exp-NNN` identifiers are **reserved when a row is added** (including `Queued`). The ID is immutable for that investigation. Folder name: `{exp-NNN}-{repo-name}/`.

| ID | Repository | Language | Subsystems of Interest | Status | Expedition Folder | Research Decision |
|----|------------|----------|------------------------|--------|-------------------|-------------------|
| exp-001 | block/goose | Rust | Provider registry, context compaction, tool inspection, MCP extensions | Validated | [exp-001-goose](./exp-001-goose/) (operational) | [RD-001](../decisions/RD-001.md) |
| exp-002 | OpenHands | Python | Multi-agent orchestration, sandboxing | Queued | | |
| exp-003 | LibreChat | TypeScript | Multi-provider chat, MCP, memory, UI | Queued | | |
| exp-004 | PyGPT | Python | Desktop UI, local LLM integration | Queued | | |
| exp-005 | Logseq | Clojure/JS | Knowledge graph, local-first notes | Queued | | |
| exp-006 | Obsidian | JS/Electron | Plugin system, vault model | Queued | | |
| exp-007 | React Flow | TypeScript | Graph visualisation | Queued | | |
| exp-008 | Cytoscape.js | JS | Graph visualisation | Queued | | |
| exp-009 | ElkJS | TypeScript | Graph layout | Queued | | |
| exp-010 | Yjs | JavaScript | CRDT / collaboration | Queued | | |
| exp-011 | Automerge | Rust/JS | CRDT / collaboration | Queued | | |
| exp-012 | VS Code | TypeScript | Plugin architecture, command palette | Queued | | |
| exp-013 | Ollama | Go | Local AI runtime, model management | Queued | | |

> **Historical:** `expedition-001-goose/` is preserved Agent-1 evidence for Goose; it is **not** the operational provenance tree. See that folder’s `HISTORICAL.md`.

## Status values

- `Queued` — in backlog, not started
- `In Progress` — expedition active
- `Validated` — report and research decision complete
- `On Hold` — paused pending further context
- `Rejected` — investigated and rejected with documented reason

## Folder layout

Each repository has a folder named `{expedition-id}-{repo-name}/` containing:

- `report.md` — expedition report from `templates/repository/repository_template.md`
- `patterns.md` — extracted pattern candidates and validation notes
- `decisions.md` — research decision summary
- `notes/` — scratch notes, diagrams, and supporting material
