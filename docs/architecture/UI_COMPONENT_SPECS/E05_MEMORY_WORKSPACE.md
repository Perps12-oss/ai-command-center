# E05 — Memory Workspace

**Slice:** PR-UI-E05  
**Status:** COMPLETE on `main` — **not Queue 1**.

## Purpose

Evolve Memory into a workspace with catalog, search, detail, injection indicator, and inspector selection.

## Composition

```
MemoryView
├── Search entry → local filter + UI_MEMORY_SEARCH
├── MemoryCard list
├── MemoryDetail
└── Injection indicator (memory_selected ∪ global_context.sources)
```

## Topics

| Topic | Intent |
|-------|--------|
| `ui.memory.select` | Memory focused |
| `ui.memory.clear` | Clear selection |
| `ui.memory.search` | Search query changed |
