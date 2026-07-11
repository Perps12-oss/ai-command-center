"""Canonical orchestration intent types (rule-based, no LLM)."""

from __future__ import annotations

from enum import Enum


class OrchestrationIntent(str, Enum):
    """Truth-bound intents handled without LLM inference."""

    LAUNCH_APPLICATION = "launch_application"
    SYSTEM_TIME_QUERY = "system_time_query"
    CALENDAR_QUERY = "calendar_query"
    SEND_EMAIL = "send_email"
    CALENDAR_EVENT_CREATE = "calendar_event_create"
    EXECUTE_SHELL = "execute_shell"
    UNHANDLED = "unhandled"
