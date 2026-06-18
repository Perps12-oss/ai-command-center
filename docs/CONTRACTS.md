# Architecture Contracts v1.0

Locked at Phase 3D → 4 transition. **Bump version only via governance review.**

Gate: `python scripts/verify_contracts.py`

Constants: `ai_command_center/core/contracts.py`

---

## ContextBundle v1.0

```python
@dataclass
class ContextBundle:
    prompt: str
    sources: tuple[str, ...]
    token_estimate: int
    version: str = "1.0"
```

**Producer:** `ContextManager.build_context()` only  
**Consumer:** `OllamaService.stream_chat()` / `.stream()` / `.chat()`

---

## command.routed v1.0

```json
{
  "contract_version": "1.0",
  "text": "user input",
  "intent": "chat | note_search | ...",
  "args": {},
  "status": "pending | processing",
  "metadata": { "executing": false, "source_router": "command_router" }
}
```

**Producer:** `CommandRouterService` only  
**Rule:** `metadata.executing` must remain `false` (router never executes)

---

## OllamaService API v1.0

| Contract method | Implementation | Notes |
|-----------------|----------------|-------|
| `chat(bundle, model=, request_id=)` | alias | Entry point |
| `stream(bundle, model=, request_id=)` | alias → `stream_chat` | Streaming |
| `stream_chat(bundle, ...)` | primary | Phase 3 impl name |
| `cancel(request_id=)` | required | |
| `api_version` | `"1.0"` | class attribute |

**Input:** `ContextBundle` with `version == "1.0"` only (until 1.1 bump)

---

## Version bump policy

1. Update `core/contracts.py` + `SUPPORTED_VERSIONS`
2. Update this document
3. Add migration note in `PHASE_LEDGER.md`
4. Run `verify_contracts.py` + full phase regression suite
