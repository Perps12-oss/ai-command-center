---
name: secrets-management
description: Use for API keys, tokens, and credentials in ai-command-center via the keyring library and Windows Credential Manager. Triggers on: storing or reading secrets, keyring usage, credential prompts, hardcoded key removal, or headless/CI secret handling.
---

# Secrets Management (ACC)

Credential handling for ACC on `keyring>=24.0.0`.

> Scope note: this is deliberately **not** a Vault / AWS Secrets Manager /
> GitHub-Secrets skill. ACC's secret store is the OS keyring. Do not introduce a
> cloud secret backend — that is an architecture decision requiring
> `docs/governance/ARCHITECTURE_DECISION_FRAMEWORK.md` and a new ADR (next free
> number is tracked in `docs/architecture/adr/README.md` — 024/025 are already
> taken as of 2026-08-14, do not assume they're free).

## ACC governance deference

Local tooling under `.claude/` — **not** Level-1/2 authority (`CLAUDE.md` →
Authority). Higher authority wins:
`PROJECT_CONSTITUTION_V4.md` → `AGENTS.md` / `docs/ARCHITECTURE_ENFORCEMENT.md`
→ architecture + contracts → **Accepted** ADRs → `origin/main`.

Constitutional Pre-Flight under `docs/audits/` before implementing
(`acc-preflight`). Never writes to `docs/governance/IMPLEMENTATION_GUIDE.md`.

## Non-negotiable rules

- **No hardcoded credentials.** Not in source, tests, fixtures, docs, or commit
  messages. `.bandit` and pre-commit exist, but treat this as a manual blocker
  too.
- **Telemetry firewall (Inv 9).** A secret must never reach a log record, span
  attribute, metric label, exception message, or checkpoint under
  `docs/checkpoints/`. This includes *partial* keys — do not log prefixes.
- **No global state (`CURRENT_VAULT`, module-level cached secret).** Resolve
  through an injected accessor owned by a lifecycle object.
- **Never construct a wrapper that reads a secret from env to bypass keyring**
  where keyring is the gated path (Inv 12 non-circumvention).

## Backend

On the supported target (Windows-ARM64) `keyring` resolves to the Windows
Credential Manager backend. Verify rather than assume:

```bash
python3 -m keyring --list-backends
```

If the priority backend is `keyring.backends.fail.Keyring` or `null`, there is
no usable store — fail loudly, do not silently fall back to plaintext.

## Reading and writing

```python
import keyring
from keyring.errors import KeyringError, PasswordDeleteError

SERVICE = "ai-command-center"


def get_secret(name: str) -> str:
    try:
        value = keyring.get_password(SERVICE, name)
    except KeyringError as exc:
        raise SecretUnavailable(name) from exc
    if value is None:
        raise SecretNotConfigured(name)
    return value
```

- `get_password` returns `None` for "not set" and raises for "store broken" —
  distinguish those. Collapsing both into `None` hides a misconfigured backend.
- Raise a domain exception naming **the key, never the value**.
- Do not cache secrets in module globals. If you must cache within a session,
  hold it on the lifecycle owner and clear it on shutdown.

## Blocking calls

`keyring` is **synchronous** and can block on the OS credential store. Inside a
coroutine always offload it:

```python
value = await asyncio.to_thread(get_secret, "openai_api_key")
```

Calling `keyring.get_password` directly in async code stalls the event loop and
will show up as UIQueue latency.

## Headless, CI, and tests

- Headless runs need `APPDATA` set (e.g. `APPDATA=/tmp/aicc_appdata`); the
  Windows backend also needs a user profile. CI on Linux has no Credential
  Manager.
- In tests, **inject a fake accessor** — do not write real secrets to a
  developer's keyring and do not `monkeypatch` the network.

```python
@pytest.fixture
def secrets() -> SecretAccessor:
    placeholder = "not-a-real-credential"
    return InMemorySecrets({"openai_api_key": placeholder})
```

- Test-only values should be obviously fake so a leak is recognisable.
- Bind the placeholder to a name first. UCGS `secrets_in_diff` (S4, CRITICAL,
  `ucgs.config.yaml`) matches `api_key`/`secret_key`/`password =`/`token =`
  immediately followed by a quoted literal — a fixture or doc example that maps
  such a key name directly to an inline quoted string trips it and blocks the
  commit, even in Markdown. Do not weaken the rule to get past this;
  restructure the example so the value comes from a bound name.

## Rotation and removal

```python
def delete_secret(name: str) -> None:
    try:
        keyring.delete_password(SERVICE, name)
    except PasswordDeleteError:
        pass  # already absent — deletion is idempotent
```

Rotation is: write new → verify read → delete old. Never delete before the new
value reads back.

## Review checklist

- [ ] No literal key material anywhere in the diff
- [ ] No secret in any log, span, metric, or exception message
- [ ] `keyring` calls offloaded off the event loop
- [ ] Backend failure distinguished from "not configured"
- [ ] No module-level secret cache
- [ ] Tests use an injected fake, not the real keyring
