"""UCGS v5 configuration loader and profile merge."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG_NAME = "ucgs.config.yaml"
PROFILES_DIR = "ucgs.profiles"


def find_project_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / DEFAULT_CONFIG_NAME).exists():
            return candidate
        if (candidate / ".git").exists():
            return candidate
    return current


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in {path}")
    return data


def deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in overlay.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            if not value:
                continue
            merged[key] = deep_merge(merged[key], value)
        elif (
            key in merged
            and isinstance(merged[key], list)
            and isinstance(value, list)
            and not value
        ):
            continue
        else:
            merged[key] = value
    return merged


def load_config(project_root: Path | None = None) -> dict[str, Any]:
    root = project_root or find_project_root()
    config_path = root / DEFAULT_CONFIG_NAME
    config = load_yaml(config_path)

    profile_name = config.get("profile", "default")
    profile_path = root / PROFILES_DIR / f"{profile_name}.yaml"
    if profile_path.exists():
        profile = load_yaml(profile_path)
        config = deep_merge(profile, config)

    config["_project_root"] = str(root)
    config["_config_path"] = str(config_path)
    config["_profile"] = profile_name
    return config


def get_enforcement_mode(config: dict[str, Any]) -> str:
    env_mode = os.getenv("UCGS_ENFORCEMENT", "").strip().lower()
    if env_mode in {"warn", "block"}:
        return env_mode
    mode = str(config.get("enforcement_mode", "warn")).strip().lower()
    return mode if mode in {"warn", "block"} else "warn"
