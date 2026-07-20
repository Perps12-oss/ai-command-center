"""ProjectionBudgetManager — token budgets for planner context projection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class BudgetWeights:
    """Fractional allocation of the token budget by section."""

    goal: float = 0.30
    workspace: float = 0.20
    recent_activity: float = 0.20
    entities: float = 0.15
    memories: float = 0.10
    relationships: float = 0.05


@dataclass(frozen=True, slots=True)
class ProjectionSection:
    name: str
    priority: int  # lower = keep longer
    lines: tuple[str, ...]


def _estimate_tokens(text: str) -> int:
    # Rough heuristic: ~4 chars per token.
    return max(1, (len(text) + 3) // 4) if text else 0


class ProjectionBudgetManager:
    """Truncate projection sections to fit a hard token budget by priority."""

    SECTION_ORDER: tuple[str, ...] = (
        "goal",
        "workspace",
        "recent_activity",
        "entities",
        "memories",
        "relationships",
    )

    def __init__(
        self,
        *,
        max_tokens: int = 4096,
        weights: BudgetWeights | None = None,
    ) -> None:
        self.max_tokens = max_tokens
        self.weights = weights or BudgetWeights()

    def section_budgets(self) -> dict[str, int]:
        w = self.weights
        mapping = {
            "goal": w.goal,
            "workspace": w.workspace,
            "recent_activity": w.recent_activity,
            "entities": w.entities,
            "memories": w.memories,
            "relationships": w.relationships,
        }
        return {k: max(32, int(self.max_tokens * v)) for k, v in mapping.items()}

    def allocate(self, sections: list[ProjectionSection]) -> list[str]:
        """Return snippets within budget; truncate lowest-priority first."""
        budgets = self.section_budgets()
        by_name = {s.name: s for s in sections}
        out: list[str] = []
        total = 0

        for name in self.SECTION_ORDER:
            section = by_name.get(name)
            if section is None or not section.lines:
                continue
            budget = budgets.get(name, 128)
            kept: list[str] = []
            used = 0
            for line in section.lines:
                cost = _estimate_tokens(line)
                if used + cost > budget:
                    break
                if total + cost > self.max_tokens:
                    break
                kept.append(line)
                used += cost
                total += cost
            out.extend(kept)
            if total >= self.max_tokens:
                break

        # If still over (edge case), drop from the end (lowest priority sections last in order).
        while out and sum(_estimate_tokens(x) for x in out) > self.max_tokens:
            out.pop()
        return out

    def allocate_dict(self, sections: dict[str, list[str]]) -> list[str]:
        priority = {name: i for i, name in enumerate(self.SECTION_ORDER)}
        typed = [
            ProjectionSection(
                name=name,
                priority=priority.get(name, 99),
                lines=tuple(lines),
            )
            for name, lines in sections.items()
            if lines
        ]
        typed.sort(key=lambda s: s.priority)
        return self.allocate(typed)

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_tokens": self.max_tokens,
            "weights": {
                "goal": self.weights.goal,
                "workspace": self.weights.workspace,
                "recent_activity": self.weights.recent_activity,
                "entities": self.weights.entities,
                "memories": self.weights.memories,
                "relationships": self.weights.relationships,
            },
            "section_budgets": self.section_budgets(),
        }
