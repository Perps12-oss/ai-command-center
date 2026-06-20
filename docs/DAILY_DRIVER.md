# Daily Driver Test — Manual Protocol



> **Phase 5C supersedes this document** for full sign-off.  

> See [PHASE5C_STRESS_TEST.md](PHASE5C_STRESS_TEST.md) for the 4-layer stress protocol and scorecard.



This file remains a **quick subset** (Tests A–C) aligned with Layer 1 + Layer 4.



**Goal:** Validate the system is *useful*, not just architecturally correct.



Record results in `docs/PHASE_LEDGER.md` § Current after Phase 5C gate PASS.



---



## Prerequisites



- [ ] Ollama running (`ollama serve`)

- [ ] Model pulled (`ollama pull llama3.2:3b` or your `default_model`)

- [ ] ARM64 Python: `C:\Users\S8633\AppData\Local\Python\bin\python.exe`

- [ ] Optional: `obsidian_vault_path` set if testing notes

- [ ] Phase 5C preflight PASS: `python scripts/verify_phase5c_preflight.py`



---



## Test A — Clipboard summarize (primary)



| Step | Action | Pass? | Notes |

|------|--------|-------|-------|

| 1 | Copy text to clipboard | | |

| 2 | Alt+Space → palette opens | | |

| 3 | Type: `Summarize this clipboard` | | |

| 4 | Chat view shows streaming response | | |

| 5 | Close palette (✕ or Alt+Space) | | |

| 6 | Reopen → history visible | | |



**Score (1–5 each):**



| Dimension | Score | Notes |

|-----------|-------|-------|

| Latency (total < 10s goal) | /5 | Record wall-clock: _____ s |

| Friction (steps intuitive?) | /5 | |

| Usability (non-dev can use?) | /5 | |

| Predictability (expected behavior?) | /5 | |



---



## Test B — Note injection (optional)



| Step | Action | Pass? |

|------|--------|-------|

| 1 | `note: {keyword}` | |

| 2 | Notes view → **Use in chat** | |

| 3 | Ask question about note | |

| 4 | Response references note content | |



---



## Test C — Failure recovery



| Step | Action | Pass? |

|------|--------|-------|

| 1 | Stop Ollama | |

| 2 | Ask a question | |

| 3 | Clear error, UI responsive | |

| 4 | Start Ollama, retry succeeds | |



---



## Automated preflight (run before manual)



```powershell

$py = "C:\Users\S8633\AppData\Local\Python\bin\python.exe"

& $py scripts/verify_phase5c_preflight.py

```



Includes contracts, phase gates 1–5B, note audit, and `run_daily_driver.py`.



---



## Phase 5C sign-off



```powershell

& $py scripts/phase5c_scorecard.py record

& $py scripts/verify_phase5c.py

```



Scorecard path: `%APPDATA%\AICommandCenter\phase5c_scorecard.json`



Gold standard: Core ≥ 4, Context ≥ 4, Failure Recovery ≥ 4, `natural_reuse: true`.



---



## Legacy sign-off template



```

Manual daily-driver: {PASS | FAIL | PARTIAL}

Date:

Tester:

Latency (Test A): ___ s

Friction / Usability / Predictability: ___ / ___ / ___ (avg)

Blockers:

```


