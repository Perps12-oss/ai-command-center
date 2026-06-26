"""Intent Resolution (Reference Architecture v3.5, Part IV).

Deterministic, classify-only intent layer. Every resolution exposes a confidence
``score``; the confidence policy maps that score to a :class:`ResolutionMode`:

    score >= 0.90            -> AUTO_EXECUTE  (caller may execute immediately)
    0.50 <= score < 0.90     -> SUGGEST       (offer the candidate, await a key)
    score <  0.50            -> CLARIFY       (ask the user to disambiguate)

This module never executes anything and never invokes AI — it ranks candidates
deterministically and reports the policy decision (A2 Execution-readiness exposed
as confidence, A5 Determinism Before AI). No subsystem may silently execute an
ambiguous action, so an empty or low-confidence candidate set resolves to CLARIFY.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import Enum

# Confidence policy thresholds (Part IV).
AUTO_EXECUTE_THRESHOLD: float = 0.90
SUGGEST_THRESHOLD: float = 0.50


class ResolutionMode(Enum):
    """Action disposition implied by a candidate's confidence score."""

    AUTO_EXECUTE = "auto_execute"
    SUGGEST = "suggest"
    CLARIFY = "clarify"


@dataclass(frozen=True, slots=True)
class ResolutionCandidate:
    """A single way to satisfy an intent, with the confidence it is correct."""

    score: float
    target: object
    source: str


def classify(score: float) -> ResolutionMode:
    """Map a confidence score to its :class:`ResolutionMode` per the policy."""
    if score >= AUTO_EXECUTE_THRESHOLD:
        return ResolutionMode.AUTO_EXECUTE
    if score >= SUGGEST_THRESHOLD:
        return ResolutionMode.SUGGEST
    return ResolutionMode.CLARIFY


@dataclass(frozen=True, slots=True)
class IntentResolution:
    """Outcome of resolving an intent: the policy decision plus ranked candidates."""

    mode: ResolutionMode
    best: ResolutionCandidate | None
    candidates: tuple[ResolutionCandidate, ...] = field(default_factory=tuple)

    @property
    def should_auto_execute(self) -> bool:
        return self.mode is ResolutionMode.AUTO_EXECUTE

    @property
    def needs_clarification(self) -> bool:
        return self.mode is ResolutionMode.CLARIFY

    @property
    def suggestions(self) -> tuple[ResolutionCandidate, ...]:
        """Candidates within the suggestion band (0.50 <= score < 0.90)."""
        return tuple(
            c for c in self.candidates if classify(c.score) is ResolutionMode.SUGGEST
        )


class IntentResolver:
    """Deterministically ranks candidates and applies the confidence policy.

    Classify-only: it selects and labels, but never executes. Ranking is stable and
    reproducible — strongest score first, ties broken by ``source`` — so the same
    candidate set always yields the same decision (A5).
    """

    def resolve(self, candidates: Iterable[ResolutionCandidate]) -> IntentResolution:
        ranked = tuple(
            sorted(candidates, key=lambda c: (-c.score, c.source))
        )
        if not ranked:
            return IntentResolution(ResolutionMode.CLARIFY, None, ())
        best = ranked[0]
        return IntentResolution(classify(best.score), best, ranked)
