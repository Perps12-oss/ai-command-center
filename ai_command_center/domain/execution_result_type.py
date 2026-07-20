"""Canonical execution outcome kinds — includes NO_OP for idempotent short-circuits."""

from __future__ import annotations

from enum import Enum


class ExecutionResultType(str, Enum):
    """Result classification for runs and virtual receipts."""

    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    NO_OP = "no_op"
