# ACC Inspiration Matrix

Comparison of candidate repositories against patterns/subsystems of interest.

## Repositories compared

| Repository | Language | Subsystems of Interest | Status |
|------------|----------|------------------------|--------|
| block/goose | Rust | Provider registry, context compaction, tool inspection, MCP extensions | Validated |
| OpenHands | Python | Multi-agent orchestration, sandboxing, coding agents | Queued |
| LibreChat | TypeScript | Multi-provider chat, MCP, memory, UI | Queued |
| PyGPT | Python | Desktop UI, local LLM integration | Queued |
| Logseq | Clojure/JS | Knowledge graph, local-first notes | Queued |
| Obsidian | JS/Electron | Plugin system, vault model | Queued |
| React Flow | TypeScript | Graph visualisation | Queued |
| Yjs | JavaScript | CRDT / collaboration | Queued |
| VS Code | TypeScript | Plugin architecture, command palette | Queued |

## Pattern coverage matrix

| Pattern / Subsystem | block/goose | OpenHands | LibreChat | VS Code |
|---------------------|-------------|-----------|-----------|---------|
| Provider registry | Strong | Medium | Medium | - |
| Context compaction | Strong | Medium | - | - |
| Tool inspection pipeline | Strong | Medium | - | - |
| MCP extension manager | Strong | Medium | Strong | - |
| Multi-agent orchestration | - | Strong | - | - |
| Plugin architecture | - | - | - | Strong |
| Command palette | - | - | - | Strong |

## Scoring key

- Strong: directly relevant, well-engineered
- Medium: relevant but requires adaptation
- Weak / -: not a significant source

## Findings

- block/goose is the richest source for provider, context, and tool governance patterns.
- OpenHands is the best candidate for multi-agent orchestration patterns.
- LibreChat is the best candidate for multi-provider UI chat patterns.
- VS Code is the best candidate for plugin and command palette UX.

## Recommendation

Proceed with block/goose patterns first. Queue OpenHands, LibreChat, and VS Code for future expeditions based on ACC roadmap priorities.
