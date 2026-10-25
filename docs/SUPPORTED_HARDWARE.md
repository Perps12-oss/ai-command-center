# Supported hardware — v1.0 desktop SKU

**Contract:** [`PLATFORM_CONTRACT.md`](PLATFORM_CONTRACT.md)

| SKU | Status |
|-----|--------|
| Windows ARM64, native ARM64 Python, native ARM64 Ollama | **v1.0** |
| Windows x86-64 | Not in v1.0 (re-open multi-arch audit only after ISA gate on `main`) |
| macOS / Linux GUI | Stream G; not v1.0 |

**Operator proof:** [`audits/ARM64_ISA_EVIDENCE_2026-08-16.md`](audits/ARM64_ISA_EVIDENCE_2026-08-16.md)

**Reference hardware:** Lenovo 83N3, Snapdragon X, 16 GB RAM.

Do not use PATH x64-emulated `python` on ARM64 Windows.
