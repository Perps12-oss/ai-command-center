"""System facts provider — date, time, timezone, hostname, platform, uptime."""

from __future__ import annotations

import platform
import socket
from datetime import datetime, timezone
from typing import Callable
from zoneinfo import ZoneInfo

from ai_command_center.orchestration.intents.intent_types import OrchestrationIntent
from ai_command_center.orchestration.providers.execution_result import ProviderExecutionResult


class SystemFactsProvider:
    """Ground-truth system facts without LLM inference."""

    provider_id = "system_facts"

    def __init__(
        self,
        *,
        now_fn: Callable[[], datetime] | None = None,
        uptime_seconds_fn: Callable[[], float] | None = None,
    ) -> None:
        self._now_fn = now_fn
        self._uptime_seconds_fn = uptime_seconds_fn

    def health(self) -> tuple[bool, str]:
        return True, "ready"

    def execute(
        self,
        intent: OrchestrationIntent,
        *,
        request_id: str,
        query: str,
        args: dict[str, str],
    ) -> ProviderExecutionResult:
        if intent is not OrchestrationIntent.SYSTEM_TIME_QUERY:
            return ProviderExecutionResult(
                success=False,
                error=f"unsupported intent: {intent.value}",
            )
        now = self._now_fn() if self._now_fn else datetime.now(timezone.utc)
        local_tz = datetime.now().astimezone().tzinfo
        tz_name = str(local_tz) if local_tz is not None else "UTC"
        try:
            tz_name = str(ZoneInfo(datetime.now().astimezone().tzname() or "UTC"))
        except Exception:
            pass
        local_now = now.astimezone()
        time_str = local_now.strftime("%I:%M %p").lstrip("0")
        if time_str.startswith(":"):
            time_str = "12" + time_str

        date_str = local_now.strftime("%A, %B %d, %Y")
        hostname = socket.gethostname()
        system_platform = platform.platform()
        uptime = self._uptime_seconds_fn() if self._uptime_seconds_fn else None

        facts: dict[str, object] = {
            "time": time_str,
            "date": date_str,
            "timezone": tz_name,
            "hostname": hostname,
            "platform": system_platform,
        }
        if uptime is not None:
            facts["uptime_seconds"] = uptime

        response = f"It is {time_str} on {date_str} ({tz_name})."
        return ProviderExecutionResult(
            success=True,
            response_text=response,
            facts=facts,
        )
