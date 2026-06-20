#!/usr/bin/env python3
"""Print read-only telemetry session summary for Phase 5C+ daily driver."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai_command_center.db.connection import connect
from ai_command_center.db.telemetry_repository import TelemetryRepository
from ai_command_center.services.telemetry_summary import (
    compute_session_summary,
    format_session_summary,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Telemetry session summary (read-only)")
    parser.add_argument(
        "--session",
        help="Session id (default: latest session_id in telemetry log)",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text")
    args = parser.parse_args()

    conn = connect()
    repo = TelemetryRepository(conn)
    try:
        if args.session:
            session_id = args.session
        else:
            row = conn.execute(
                """
                SELECT payload
                FROM telemetry_events
                ORDER BY id DESC
                LIMIT 1
                """
            ).fetchone()
            if row is None:
                print("No telemetry events recorded yet.")
                return 0
            import json

            payload = json.loads(row["payload"])
            session_id = str(payload.get("session_id", ""))
            if not session_id:
                print("Latest event has no session_id.")
                return 1

        rows = repo.fetch_session(session_id)
        summary = compute_session_summary(rows)
        if args.json:
            import json

            print(json.dumps({"session_id": session_id, **summary}, indent=2))
        else:
            print(format_session_summary(summary, session_id=session_id))
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
