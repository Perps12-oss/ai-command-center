# Phase 6: External Capability Bridge

**Status:** PARTIAL (code-verified 2026-07-20 — bridge exists; MCP scan exit incomplete)  
**Priority:** HIGH  
**Estimated Effort:** 2-3 weeks  
**Dependencies:** Phase 4 Phase E scaffold ✅  
**Authority:** `AGENT_RUNTIME_INTERFACE.md`, `PROJECT_CONSTITUTION_V4.md`  
**Verification:** `docs/audits/PHASE_PLANS_ARCHIVE_VERIFICATION.md`

---

## Executive Summary

Create a bridge service that aggregates external capabilities (MCP servers, external agents) into the planner-facing capability catalog. This enables the planner to dispatch to external runtimes through the ARI interface while maintaining constitutional compliance.

---

## Current State

**Scaffold:** `ExternalCapabilityBridgeService` class exists

**Missing:**
- MCP manifest schema
- Capability aggregation
- Runtime invocation bridge

---

## Architecture

### Service Architecture

```text
┌─────────────────────────────────────────────────────────────────┐
│                    ExternalCapabilityBridgeService              │
├─────────────────────────────────────────────────────────────────┤
│  manifest_loader: ManifestLoader                                │
│  capability_catalog: CapabilityPromptCatalogService             │
│  runtime_registry: RuntimeProviderRegistry                      │
└─────────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ MCP Manifest│    │ ExternalRuntime  │    │   EventBus      │
│  Loader     │    │   Providers     │    │   Integration   │
└─────────────┘    └─────────────────┘    └─────────────────┘
```

### EventBus Topics

| Topic | Direction | Payload |
|-------|-----------|---------|
| `external.capability.register` | Inbound | `{ provider_id, manifest, capabilities[] }` |
| `external.capability.unregister` | Inbound | `{ provider_id }` |
| `external.capability.registered` | Outbound | `{ provider_id, capabilities[] }` |
| `capability.runtime.request` | Outbound | `{ request_id, capability, args, provider_id }` |
| `capability.runtime.response` | Inbound | `{ request_id, result, error? }` |

---

## Implementation

### 6.1 MCP Manifest Schema

**File:** `plugins/runtime_manifests/mcp_manifest.py`

```python
@dataclass
class MCPCapabilityManifest:
    provider_id: str
    provider_type: Literal["mcp"]
    server_url: str
    capabilities: list[MCPCapability]
    auth: MCPAuthConfig | None = None

@dataclass
class MCPCapability:
    name: str
    description: str
    parameters: dict[str, Any]
    risk_level: RiskLevel
    requires_approval: bool
```

### 6.2 Manifest Loader

**File:** `ai_command_center/services/external_capability_bridge_service.py`

**Responsibilities:**
- Scan `runtime_manifests/` directory
- Validate manifest schema
- Load MCP server configs
- Publish `external.capability.registered`

### 6.3 Capability Aggregation

**File:** `ai_command_center/services/capability_prompt_catalog_service.py` (update)

**Changes:**
- Subscribe to `external.capability.registered`
- Merge external capabilities into planner catalog
- Update `get_available_prompt_specs()` to include external

### 6.4 Runtime Invocation Bridge

**File:** `ai_command_center/runtime/mcp_runtime_provider.py`

**Responsibilities:**
- Maintain MCP server connections
- Translate capability calls to MCP protocol
- Handle authentication
- Publish `capability.runtime.response`

---

## Files

### Create

```
plugins/runtime_manifests/mcp_manifest.py
ai_command_center/runtime/mcp_runtime_provider.py
tests/test_external_capability_bridge_service.py
tests/test_mcp_manifest_loader.py
```

### Modify

```
ai_command_center/services/external_capability_bridge_service.py
ai_command_center/services/capability_prompt_catalog_service.py
ai_command_center/core/events/topics.py
```

### Create Manifests

```
plugins/runtime_manifests/README.md (manifest format documentation)
plugins/runtime_manifests/example_mcp.yaml (example manifest)
```

---

## Testing

### Unit Tests

- [ ] `test_mcp_manifest_validation`
- [ ] `test_manifest_loader_scans_directory`
- [ ] `test_external_capability_registered_event`
- [ ] `test_capability_catalog_aggregates_external`

### Integration Tests

- [ ] `test_mcp_server_connection` (mock)
- [ ] `test_runtime_invocation_flow`
- [ ] `test_external_capability_unregister`

---

## Exit Criteria

- [ ] `ExternalCapabilityBridgeService` starts successfully
- [ ] Manifests load from `runtime_manifests/`
- [ ] Capability catalog includes external capabilities
- [ ] Unit tests pass
- [ ] Architecture lint clean
- [ ] UCGS PASS

---

## Non-Goals

- Full MCP wire-up (future work)
- Actual MCP server implementation
- Real authentication integration

---

## Revision History

| Date | Change |
|------|--------|
| 2026-07-11 | Initial plan |
