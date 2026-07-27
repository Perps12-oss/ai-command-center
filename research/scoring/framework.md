# Scoring Framework

Use this rubric to score repositories, pattern candidates, and integration proposals.

## Dimensions

### 1. Engineering quality

| Score | Meaning |
|-------|---------|
| 1-3 | Fragile, poorly tested, or tightly coupled |
| 4-6 | Solid but unremarkable |
| 7-8 | Clean, well-tested, idiomatic |
| 9-10 | Excellent, reference-quality engineering |

### 2. Architectural complexity

| Score | Meaning |
|-------|---------|
| 1-3 | Simple, easy to understand and integrate |
| 4-6 | Moderate complexity; requires adaptation |
| 7-8 | High complexity; significant integration work |
| 9-10 | Overwhelming; likely to destabilize ACC |

*Note: lower complexity is better for ACC fit, but this is scored as complexity level, not preference.*

### 3. Reuse potential

| Score | Meaning |
|-------|---------|
| 1-3 | Specific to the source repository |
| 4-6 | Useful idea but requires rework |
| 7-8 | Strongly reusable across ACC |
| 9-10 | Foundational pattern with broad application |

### 4. ACC architecture fit

| Score | Meaning |
|-------|---------|
| 1-3 | Conflicts with authority model, UI isolation, or repository ownership |
| 4-6 | Adaptable but requires non-trivial changes |
| 7-8 | Fits cleanly with minor adaptation |
| 9-10 | Natural fit for ACC's existing architecture |

### 5. Integration risk

| Score | Meaning |
|-------|---------|
| 1-3 | Low risk; additive and isolated |
| 4-6 | Moderate risk; touches multiple modules |
| 7-8 | High risk; requires architectural change |
| 9-10 | Critical risk; could destabilize core systems |

## Recommendation mapping

| Engineering | Complexity | Reuse | Fit | Risk | Recommendation |
|-------------|------------|-------|-----|------|----------------|
| 8+ | 1-5 | 8+ | 8+ | 1-3 | **Immediate** |
| 7+ | 1-6 | 7+ | 7+ | 1-5 | **Adapt** |
| 6+ | any | 6+ | 6+ | 1-6 | **Future** |
| <6 | any | <6 | <6 | 6+ | **Reject** |

Apply judgment; the table is a guide, not a rule.
