# E10 — Evidence Workspace

**Slice:** PR-UI-E10  
**Status:** Implemented on feature branch (pending merge)

## Purpose

New Evidence Workspace listing orchestration claims with truth status; selection shows facts, receipt, and trace.

## Composition

```
EvidenceView
├── Hero (claim count, navigate to Execution Center)
├── Claims list (ClaimCard + TruthBadge)
└── Detail
    ├── TruthValidationPanel (reused)
    ├── ReceiptViewerPanel (reused)
    └── ReceiptChain (facts / receipt / trace)
```

## State

- Reads `AppState.orchestration_run` only
- No new AppState fields

## Topics

| Topic | Intent |
|-------|--------|
| `ui.evidence.select` | Claim focused |
| `ui.evidence.open` | Open evidence workspace |

Selection also publishes `UI_INSPECT_SELECT` kind `evidence`.
