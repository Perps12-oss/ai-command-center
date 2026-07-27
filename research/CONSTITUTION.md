# Research Constitution

1. **Research is descriptive, never prescriptive.**
   Research describes what exists and why it might matter. It does not mandate implementation.

2. **No code may be copied without understanding the underlying pattern.**
   Borrow ideas, not snippets. Understand the problem, solution, trade-offs, and risks before reuse.

3. **Every adopted pattern must trace back to a Pattern Registry entry, an Integration Proposal, and an ADR.**
   A pattern is not adopted until it has completed the full promotion pipeline.

4. **Every investigated repository must produce a Research Decision (RD).**
   Each expedition ends with a recorded decision: `Proceed`, `Reject`, or `Hold`. This prevents duplicate investigations.

5. **ACC architecture always takes precedence over external projects.**
   External projects provide capabilities and patterns. ACC owns user experience, workspace, orchestration, and state authority. No external pattern may weaken those.

6. **The goal is to extract engineering patterns, not replicate products.**
   Do not turn ACC into Goose, OpenHands, or LibreChat. Extract the ideas that strengthen ACC and discard the rest.

---

## Promotion pipeline

```text
Repository Expedition
       ↓
Pattern Candidate extraction
       ↓
Pattern Validation (ACC fit, reuse, risk)
       ↓
Pattern Registry (PAT-NNN)
       ↓
Integration Proposal
       ↓
Architecture Review (Tom)
       ↓
ADR in docs/architecture/adr/
       ↓
Implementation Plan
       ↓
Implementation
       ↓
Verification
       ↓
Documentation
```
