"""Provider SDK base types and protocols."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

SDK_VERSION = "1.0"


@dataclass(frozen=True, slots=True)
class ProviderTestContext:
    """Context passed to provider certification harness."""

    provider_id: str
    dev_mode: bool = False


class CertifiableProvider(Protocol):
    """Minimal surface exercised by the certification harness."""

    provider_id: str

    def health(self) -> tuple[bool, str]: ...
