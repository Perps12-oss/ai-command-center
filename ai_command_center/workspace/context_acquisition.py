"""Context Acquisition (Reference Architecture v3.5, Part III).

A reliability-first, **pull-based** acquisition hierarchy. Context is gathered only
when :meth:`ContextAcquirer.acquire` is called explicitly — there is no background
polling or auto-ingestion (a UCGS-forbidden pattern). Providers are injected, so the
core is pure, deterministic, and platform-agnostic; OS-specific readers (clipboard,
UI automation) are supplied as thin adapters by higher layers.

Reliability ranking (most reliable first); a higher-ranked source supersedes a
lower-ranked one for the same key:

    1 Clipboard
    2 Explicit User Input
    3 Workspace Indexes
    4 Known Integrations
    5 UI Automation   (optional — core must work without it)
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from enum import IntEnum


class ContextSource(IntEnum):
    """Acquisition sources, ordered by reliability (lower value = higher rank)."""

    CLIPBOARD = 1
    EXPLICIT_INPUT = 2
    WORKSPACE_INDEX = 3
    KNOWN_INTEGRATION = 4
    UI_AUTOMATION = 5

    @property
    def is_optional(self) -> bool:
        return self is ContextSource.UI_AUTOMATION


@dataclass(frozen=True, slots=True)
class ContextFragment:
    """A single piece of acquired context, tagged with its originating source."""

    key: str
    value: object
    source: ContextSource

    @property
    def rank(self) -> int:
        # Reliability rank: smaller is more reliable / higher priority.
        return int(self.source)


class ContextProvider:
    """Base pull-based provider. Subclasses implement :meth:`acquire`.

    ``acquire`` is invoked only on demand; it must not start threads or perform
    background work. Returning an empty sequence means "nothing available now".
    """

    source: ContextSource

    def acquire(self) -> Sequence[ContextFragment]:  # pragma: no cover - interface
        raise NotImplementedError


class CallableProvider(ContextProvider):
    """Adapter that turns a reader callable into a provider for one source.

    Keeps OS-specific code (e.g. a Windows clipboard reader) out of this layer:
    the reader is injected and may return a value, a mapping, or fragments.
    """

    def __init__(
        self,
        source: ContextSource,
        reader: Callable[[], object],
        *,
        key: str | None = None,
    ) -> None:
        self.source = source
        self._reader = reader
        self._key = key or source.name.lower()

    def acquire(self) -> Sequence[ContextFragment]:
        raw = self._reader()
        if raw is None:
            return ()
        if isinstance(raw, ContextFragment):
            return (raw,)
        if isinstance(raw, dict):
            return tuple(
                ContextFragment(key=str(k), value=v, source=self.source)
                for k, v in raw.items()
            )
        # str/bytes are scalar values, not fragment collections.
        if not isinstance(raw, (str, bytes)) and isinstance(raw, Iterable):
            items = tuple(raw)
            if not items:
                return ()
            if all(isinstance(item, ContextFragment) for item in items):
                return items
            # A non-fragment iterable is treated as a single scalar value.
            return (ContextFragment(key=self._key, value=items, source=self.source),)
        return (ContextFragment(key=self._key, value=raw, source=self.source),)


@dataclass(frozen=True, slots=True)
class AcquiredContext:
    """Merged, deterministic view of context after applying the supersede rule."""

    fragments: tuple[ContextFragment, ...] = field(default_factory=tuple)
    errors: tuple[tuple[ContextSource, str], ...] = field(default_factory=tuple)

    def get(self, key: str) -> ContextFragment | None:
        for fragment in self.fragments:
            if fragment.key == key:
                return fragment
        return None

    def value(self, key: str, default: object = None) -> object:
        fragment = self.get(key)
        return fragment.value if fragment is not None else default

    def __contains__(self, key: object) -> bool:
        return any(f.key == key for f in self.fragments)


class ContextAcquirer:
    """Runs registered providers and merges fragments by reliability.

    Deterministic: the merged result depends only on the registered providers and
    their output, not on call timing. For each key the most reliable source wins;
    a failing provider is skipped (recorded in ``errors``) so core functionality —
    in particular, operation without the optional UI Automation source — is never
    blocked by one provider.
    """

    def __init__(self, providers: Iterable[ContextProvider] = ()) -> None:
        self._providers: list[ContextProvider] = list(providers)

    def register(self, provider: ContextProvider) -> None:
        self._providers.append(provider)

    def acquire(self, *, include_ui_automation: bool = False) -> AcquiredContext:
        chosen: dict[str, ContextFragment] = {}
        errors: list[tuple[ContextSource, str]] = []

        for provider in self._providers:
            if provider.source.is_optional and not include_ui_automation:
                continue
            try:
                produced = provider.acquire()
            except Exception as exc:  # noqa: BLE001 - resilience is the contract here
                errors.append((provider.source, f"{type(exc).__name__}: {exc}"))
                continue
            for fragment in produced:
                incumbent = chosen.get(fragment.key)
                # Higher-ranked (lower rank value) source supersedes lower-ranked.
                if incumbent is None or fragment.rank < incumbent.rank:
                    chosen[fragment.key] = fragment

        # Deterministic ordering: by rank, then key.
        ordered = tuple(
            sorted(chosen.values(), key=lambda f: (f.rank, f.key))
        )
        return AcquiredContext(fragments=ordered, errors=tuple(errors))
