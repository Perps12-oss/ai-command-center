# Architecture Contracts

Locked at Phase 3D → 4 transition. **Bump version only via governance review.**

Gate: `python scripts/verify_contracts.py`

Constants: `ai_command_center/core/contracts.py`

---

## ContextBundle v1.1 (current)

```python
@dataclass
class ContextBundle:
    prompt: str
    sources: tuple[str, ...]  # may include conversation_summary, memory_graph_*
    token_estimate: int
    version: str = "1.1"
```

v1.0 remains in `SUPPORTED_VERSIONS` for backward compatibility.

**Producer:** `ContextManager.build_context()` only  
**Consumer:** `OllamaService.stream_chat()` / `.stream()` / `.chat()`

---

## command.routed v1.0

Unchanged — see prior spec. `contract_version: "1.0"`.

---

## tool.invoke / tool.result v1.0 (Phase 4B)

```json
{
  "contract_version": "1.0",
  "invoke_id": "uuid",
  "tool": "shell",
  "args": {}
}
```

**Producer:** `ShellToolService` (and future tool bridges)  
**Consumer:** `ToolExecutorService` — one invocation per event, no loops

---

## OllamaService API v1.0

Unchanged.

---

## Version bump policy

1. Update `core/contracts.py` + `SUPPORTED_VERSIONS`
2. Update this document
3. Add migration note in `PHASE_LEDGER.md`
4. Run full phase regression suite
