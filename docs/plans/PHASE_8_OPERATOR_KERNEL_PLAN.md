# Phase 8: Operator Kernel & Model Independence

**Status:** PLANNED  
**Priority:** HIGH  
**Estimated Effort:** 6-8 weeks  
**Dependencies:** Phase 7 (Operational Intelligence) complete ✅, Phase 5 (Async) ✅  
**Authority:** `PROJECT_CONSTITUTION_V4.md`, `AGENTS.md`

---

## Mission

Transform ACC from **Operator Runtime** into **Model-Agnostic Operator Platform**.

```
GPT Claude Gemini Qwen DeepSeek Llama
all behave as Operator

rather than becoming:

Operator behaves differently depending on model
```

---

## Core Principle

```
Behavior belongs to ACC
Reasoning belongs to LLM
```

---

## Architecture

```
                USER
                  │
                  ▼
        ┌─────────────────┐
        │ Operator Kernel │
        └────────┬────────┘
                 │
      ┌──────────┼──────────┐
      ▼          ▼          ▼
    Intent    Planning   Policies
      └──────────┼──────────┘
                 ▼
      Prompt Assembly Service
                 ▼
          Model Adapter
                 ▼
        GPT Claude Qwen DeepSeek Gemini
                 ▼
        Compliance Engine
                 ▼
        Response Contract
                 ▼
         UI Renderer
```

---

## Major Subsystems

### 8.1 Operator Kernel

**New Root Package:** `ai_command_center/operator/`

| Component | Purpose |
|-----------|---------|
| `OperatorKernel` | Single source of operational behavior |
| `IntentResolver` | Classify user intent |
| `ModeResolver` | Determine operator mode (Chat, Command, Investigation, Architect) |
| `PolicyEngine` | Enforce constitutional rules |
| `ExecutionCoordinator` | Coordinate execution flow |
| `ComplianceEngine` | Validate responses, detect hallucinations |
| `ResponseRenderer` | Render structured responses |

**The kernel owns:**
- Behavior
- Rules
- Governance

**The model owns:**
- Reasoning
- Summarization
- Planning assistance

### 8.2 Prompt Assembly Framework

**New Service:** `ai_command_center/operator/prompt_assembly.py`

**Builds prompts dynamically in layers:**

```
BASE RULES
MODE RULES
WORKSPACE STATE
PROVIDER STATE
EVIDENCE
USER REQUEST
```

**Principles:**
- No giant prompts
- No duplicated prompt files
- Layered composition

### 8.3 Model Adapter Layer

**Package:** `ai_command_center/models/`

```
base.py              — ModelAdapter contract
openai_adapter.py   — OpenAI / Azure OpenAI
anthropic_adapter.py — Claude
gemini_adapter.py    — Gemini
ollama_adapter.py   — Local models
registry.py          — Model registry
```

**Adapter Contract:**

```python
class ModelAdapter(ABC):
    @abstractmethod
    def complete(self, prompt: str, config: ModelConfig) -> ModelResponse:
        """Generate completion."""
        
    @abstractmethod
    def stream(self, prompt: str, config: ModelConfig) -> Iterator[ModelResponse]:
        """Stream completion."""
        
    @property
    @abstractmethod
    def supported_modes(self) -> set[OperatorMode]:
        """Modes this adapter supports."""
```

**ACC never consumes raw model output. All output goes through ModelResponse contract.**

### 8.4 Structured Response Contracts

**All modes use contracts. No free-form operational responses.**

| Mode | Contract | Key Fields |
|------|----------|------------|
| Chat | `ChatResponse` | message, artifacts[], suggestions[] |
| Command | `CommandResponse` | command, explanation, confirm_required |
| Investigation | `InvestigationResponse` | findings[], evidence[], confidence |
| Architect | `ArchitectResponse` | design, alternatives[], tradeoffs[] |

### 8.5 Compliance Engine

**Validates every response:**

```python
class ComplianceCheck:
    HALLUCINATED_CAPABILITY = "Capability not in registry"
    INVALID_PROVIDER = "Unknown provider referenced"
    MISSING_EVIDENCE = "Claim without supporting evidence"
    CONTRACT_VIOLATION = "Response violates mode contract"
    FORBIDDEN_CLAIM = "Disallowed claim type"
```

**Can reject outputs and require regeneration.**

### 8.6 Provider-Neutral Tool Calling

**Operator never directly knows:**
- OpenAI tools
- Anthropic tools
- Gemini tools

**Everything maps to:**

```python
class CapabilityRequest:
    capability: str
    parameters: dict
    risk_level: RiskLevel
```

**Runtime translates to provider-specific format.**

---

## Golden Validation Suite

**New Package:** `tests/operator/`

### Test Coverage

| Test | Purpose |
|------|---------|
| Mode resolution | Correct mode for each query type |
| Intent classification | Accurate intent detection |
| Command generation | Valid, safe commands across providers |
| Evidence compliance | All claims backed by evidence |
| Hallucination resistance | Detects and rejects hallucinations |

### Model Independence Testing

**Execute against:**
- GPT-4
- Claude
- Gemini
- Qwen
- DeepSeek
- Llama

**Produces:**
```python
ModelIndependenceScore(
    model: str,
    behavior_consistency: float,  # 0-1
    hallucination_resistance: float,  # 0-1
    contract_compliance: float,  # 0-1
    overall: float  # 0-1
)
```

---

## Success Criteria

- [ ] Swap models without UI changes
- [ ] Swap models without prompt rewrites
- [ ] Swap models without capability changes
- [ ] Same command behavior across providers
- [ ] Compliance catches hallucinations
- [ ] Operator identity remains consistent

---

## Files

### Create

```
ai_command_center/operator/
├── __init__.py
├── kernel.py
├── intent_resolver.py
├── mode_resolver.py
├── policy_engine.py
├── prompt_assembly.py
├── compliance_engine.py
├── response_contracts.py
└── execution_coordinator.py

ai_command_center/models/
├── __init__.py
├── base.py
├── adapter.py
├── adapters/
│   ├── __init__.py
│   ├── openai_adapter.py
│   ├── anthropic_adapter.py
│   ├── gemini_adapter.py
│   └── ollama_adapter.py
└── registry.py

tests/operator/
├── __init__.py
├── test_kernel.py
├── test_intent_resolver.py
├── test_mode_resolver.py
├── test_compliance_engine.py
├── test_response_contracts.py
├── test_model_independence.py
└── golden/
    ├── __init__.py
    ├── test_chat_mode.py
    ├── test_command_mode.py
    ├── test_investigation_mode.py
    └── test_architect_mode.py
```

### Modify

```
ai_command_center/services/chat_handler_service.py
ai_command_center/core/event_bus.py
ai_command_center/core/events/topics.py
```

---

## Exit Criteria

- [ ] All operator modes implemented with structured contracts
- [ ] Model adapters for all supported providers
- [ ] Compliance engine catches 100% of test hallucinations
- [ ] Golden test suite passes for all models
- [ ] Model independence score > 0.95
- [ ] Architecture lint clean
- [ ] UCGS PASS

---

## Revision History

| Date | Change |
|------|--------|
| 2026-07-11 | Initial plan |
