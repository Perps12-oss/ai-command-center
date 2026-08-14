"""Session telemetry export — end-of-session snapshot written to disk.

Lives under ``telemetry/`` (not ``services/``) so TelemetryService can call it
without an R4 service→service import. Summary math stays in
``services.telemetry_summary`` (pure functions; no service instance calls).

Telemetry itself stays passive: the bus → SQLite path is unchanged. This module
only *reads* what was already persisted and materializes it as JSON so the data
is inspectable without opening the database.

Two files are produced under the export directory:

* ``session-<session_id>.json`` — the session's raw rows plus its derived
  summary.
* ``stats-cache.json`` — a rolling inventory across sessions (last update
  timestamp, per-session event counts, and every model seen).

Export location resolves as:

1. ``ACC_TELEMETRY_EXPORT_DIR`` if set,
2. otherwise ``<runtime data dir>/telemetry`` (``%APPDATA%/AICommandCenter``
   on Windows).

Set ``ACC_TELEMETRY_EXPORT=0`` to disable the export entirely.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_command_center.domain.telemetry_event import TelemetryEvent
from ai_command_center.platform.runtime_paths import get_runtime_data_dir
from ai_command_center.services.telemetry_summary import compute_session_summary

logger = logging.getLogger(__name__)

ENV_EXPORT_DIR = "ACC_TELEMETRY_EXPORT_DIR"
ENV_EXPORT_ENABLED = "ACC_TELEMETRY_EXPORT"

STATS_CACHE_FILENAME = "stats-cache.json"
STATS_CACHE_VERSION = 1

# The export runs during shutdown, so its cost must stay bounded regardless of
# how long the session ran. Summary/counts/models always cover every row; only
# the verbatim event list is capped (most recent kept).
MAX_EXPORTED_EVENTS = 5000
# Rolling window of sessions retained in stats-cache.json (most recent kept).
MAX_CACHED_SESSIONS = 100

_DISABLED = frozenset({"0", "false", "no", "off"})
# Payload keys that may carry a model identifier, in precedence order.
_MODEL_KEYS = ("model", "model_name")


def export_enabled() -> bool:
    """False only when ``ACC_TELEMETRY_EXPORT`` is explicitly switched off."""
    return os.environ.get(ENV_EXPORT_ENABLED, "1").strip().lower() not in _DISABLED


def resolve_export_dir() -> Path:
    """Export directory, created if missing."""
    override = os.environ.get(ENV_EXPORT_DIR, "").strip()
    path = Path(override) if override else get_runtime_data_dir() / "telemetry"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _models_in(rows: list[TelemetryEvent]) -> list[str]:
    seen: set[str] = set()
    for row in rows:
        payload = row.payload_dict()
        for key in _MODEL_KEYS:
            value = str(payload.get(key, "")).strip()
            if value:
                seen.add(value)
                break
    return sorted(seen)


def _event_counts(rows: list[TelemetryEvent]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row.event_type] = counts.get(row.event_type, 0) + 1
    return dict(sorted(counts.items()))


def build_session_export(session_id: str, rows: list[TelemetryEvent]) -> dict[str, Any]:
    """Serializable session snapshot — summary, counts, models, recent events.

    ``event_count`` and every aggregate cover the whole session; ``events`` is
    truncated to the most recent ``MAX_EXPORTED_EVENTS`` rows.
    """
    retained = rows[-MAX_EXPORTED_EVENTS:]
    return {
        "session_id": session_id,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "event_count": len(rows),
        "events_truncated": len(retained) < len(rows),
        "models": _models_in(rows),
        "event_counts": _event_counts(rows),
        "summary": compute_session_summary(list(rows)),
        "events": [
            {
                "event": row.event_type,
                "timestamp": row.timestamp,
                "payload": row.payload_dict(),
            }
            for row in retained
        ],
    }


def _json_dump(path: Path, data: dict[str, Any]) -> None:
    """Write atomically so a crashed export never leaves a half file behind."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    tmp.replace(path)


def _load_stats_cache(path: Path) -> dict[str, Any]:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def update_stats_cache(
    directory: Path,
    session_id: str,
    export: dict[str, Any],
) -> Path:
    """Merge one session into the rolling inventory and rewrite it.

    Only the most recent ``MAX_CACHED_SESSIONS`` sessions are retained; the
    ``total_*`` and ``models`` fields describe that retained window.
    """
    path = directory / STATS_CACHE_FILENAME
    cache = _load_stats_cache(path)

    sessions = cache.get("sessions")
    if not isinstance(sessions, dict):
        sessions = {}
    sessions[session_id] = {
        "exported_at": export["exported_at"],
        "event_count": export["event_count"],
        "models": export["models"],
    }
    if len(sessions) > MAX_CACHED_SESSIONS:
        ordered = sorted(
            sessions.items(), key=lambda kv: str(kv[1].get("exported_at", ""))
        )
        sessions = dict(ordered[-MAX_CACHED_SESSIONS:])

    models: set[str] = set()
    for entry in sessions.values():
        models.update(str(m) for m in entry.get("models", ()))

    _json_dump(
        path,
        {
            "version": STATS_CACHE_VERSION,
            "last_update": export["exported_at"],
            "models": sorted(models),
            "total_sessions": len(sessions),
            "total_events": sum(int(e.get("event_count", 0)) for e in sessions.values()),
            "sessions": sessions,
        },
    )
    return path


def export_session(
    repo: Any,
    session_id: str,
    *,
    directory: Path | None = None,
) -> Path | None:
    """Write the session snapshot and refresh ``stats-cache.json``.

    Returns the session file path, or ``None`` when the export is disabled or
    the session produced no rows. Never raises — a failed export must not
    interfere with shutdown.
    """
    if not export_enabled():
        return None
    try:
        rows = repo.fetch_session(session_id)
    except Exception:
        logger.exception("Telemetry export could not read session %s", session_id)
        return None
    if not rows:
        return None

    try:
        target = directory if directory is not None else resolve_export_dir()
        target.mkdir(parents=True, exist_ok=True)
        export = build_session_export(session_id, rows)
        path = target / f"session-{session_id}.json"
        _json_dump(path, export)
        update_stats_cache(target, session_id, export)
    except Exception:
        logger.exception("Telemetry export failed for session %s", session_id)
        return None
    return path
