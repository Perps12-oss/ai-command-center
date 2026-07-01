#!/usr/bin/env python3
"""AST-based architecture linter enforcing the unidirectional event flow.

Risk area #2 - Concurrency & state violations.

Enforces three rules from ``AGENTS.md`` / ``PROJECT_CONSTITUTION_V4.md``:

R1  No file under ``ui/`` may import from ``services/`` or ``backend/``.
R2  Service classes (``*Service``) may only be *instantiated* inside the
    ``services/`` package or an allow-listed composition root.
R3  No attribute of an ``AppState`` instance may be assigned outside the
    ``app_state`` module (AppState is an immutable snapshot).

The linter is importable (``analyze_source`` / ``scan_tree``) so it can be unit
tested against synthetic fixtures, and runnable as a CLI / pre-commit hook.

A *baseline* JSON file may record pre-existing violations; the CLI then fails
only on **new** violations (a ratchet), e.g.::

    python scripts/arch_lint.py --baseline tests/arch_lint_baseline.json
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "ai_command_center"

# Files permitted to wire services together (the composition root).
_COMPOSITION_ROOTS = {
    "main.py",
    "application.py",
    "core/service_factory.py",
    "core/workspace_os_service.py",  # registers/owns workspace sub-services
}

# Instance names treated as AppState snapshots for the R3 mutation check.
_APPSTATE_INSTANCE_NAMES = {"app_state", "appstate"}

# Classes that end in "Service" but are not concrete services to instantiate-guard.
_SERVICE_NAME_IGNORE = {"BaseService"}


@dataclass(frozen=True)
class Violation:
    rule: str
    file: str
    line: int
    message: str

    def key(self) -> tuple[str, str, str]:
        # Line numbers are excluded from the identity so the baseline survives
        # unrelated edits that merely shift line numbers.
        return (self.rule, self.file, self.message)


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _is_under(rel_path: str, package_subdir: str) -> bool:
    return f"/{package_subdir}/" in f"/{rel_path}"


def _module_targets_layer(module: str | None, layers: tuple[str, ...]) -> bool:
    if not module:
        return False
    for layer in layers:
        if module == f"{PACKAGE}.{layer}" or module.startswith(f"{PACKAGE}.{layer}."):
            return True
    return False


class _Analyzer(ast.NodeVisitor):
    def __init__(self, rel_path: str) -> None:
        self.rel_path = rel_path
        self.violations: list[Violation] = []
        self._in_ui = _is_under(rel_path, "ui")
        self._in_services = _is_under(rel_path, "services")
        self._in_appstate_module = rel_path.endswith("core/app_state.py") or rel_path.endswith(
            "core/state/app_state.py"
        )
        pkg_rel = rel_path.split(f"{PACKAGE}/", 1)[-1]
        self._is_composition_root = pkg_rel in _COMPOSITION_ROOTS

    # R1 - UI must not import service/backend layers.
    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if self._in_ui and _module_targets_layer(node.module, ("services", "backend")):
            self.violations.append(
                Violation(
                    rule="R1",
                    file=self.rel_path,
                    line=node.lineno,
                    message=(
                        f"UI module imports forbidden layer {node.module!r}; "
                        "route through EventBus / AppState instead"
                    ),
                )
            )
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        if self._in_ui:
            for alias in node.names:
                if _module_targets_layer(alias.name, ("services", "backend")):
                    self.violations.append(
                        Violation(
                            rule="R1",
                            file=self.rel_path,
                            line=node.lineno,
                            message=(
                                f"UI module imports forbidden layer {alias.name!r}; "
                                "route through EventBus / AppState instead"
                            ),
                        )
                    )
        self.generic_visit(node)

    # R2 - service classes may only be instantiated in services/ or a root.
    def visit_Call(self, node: ast.Call) -> None:
        if not (self._in_services or self._is_composition_root):
            name = _callee_name(node.func)
            if (
                name
                and name.endswith("Service")
                and name[0].isupper()
                and name not in _SERVICE_NAME_IGNORE
            ):
                self.violations.append(
                    Violation(
                        rule="R2",
                        file=self.rel_path,
                        line=node.lineno,
                        message=(
                            f"service class {name!r} instantiated outside services/ "
                            "or composition root"
                        ),
                    )
                )
        self.generic_visit(node)

    # R3 - no AppState attribute assignment outside the app_state module.
    def visit_Assign(self, node: ast.Assign) -> None:
        if not self._in_appstate_module:
            for target in node.targets:
                self._check_appstate_target(target)
        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        if not self._in_appstate_module:
            self._check_appstate_target(node.target)
        self.generic_visit(node)

    def _check_appstate_target(self, target: ast.expr) -> None:
        if (
            isinstance(target, ast.Attribute)
            and isinstance(target.value, ast.Name)
            and target.value.id.lower() in _APPSTATE_INSTANCE_NAMES
        ):
            self.violations.append(
                Violation(
                    rule="R3",
                    file=self.rel_path,
                    line=target.lineno,
                    message=(
                        f"direct mutation of AppState instance "
                        f"{target.value.id}.{target.attr!r}; AppState is immutable"
                    ),
                )
            )


def _callee_name(func: ast.expr) -> str | None:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def analyze_source(rel_path: str, source: str) -> list[Violation]:
    """Analyze a single module's source text; return violations."""
    tree = ast.parse(source, filename=rel_path)
    analyzer = _Analyzer(rel_path.replace("\\", "/"))
    analyzer.visit(tree)
    return analyzer.violations


def scan_tree(root: Path) -> list[Violation]:
    """Analyze every ``.py`` file under ``root`` (the package directory)."""
    violations: list[Violation] = []
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        try:
            # utf-8-sig transparently strips a leading BOM (several files in the
            # repo are saved as UTF-8 with BOM).
            source = path.read_text(encoding="utf-8-sig")
        except OSError:
            continue
        try:
            violations.extend(analyze_source(_rel(path), source))
        except SyntaxError as exc:
            violations.append(
                Violation(rule="PARSE", file=_rel(path), line=exc.lineno or 0, message=str(exc))
            )
    return violations


def _load_baseline(path: Path | None) -> set[tuple[str, str, str]]:
    if path is None or not path.exists():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    return {(v["rule"], v["file"], v["message"]) for v in data.get("violations", [])}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "root",
        nargs="?",
        default=str(PROJECT_ROOT / PACKAGE),
        help="package directory to scan",
    )
    parser.add_argument("--baseline", help="JSON baseline of accepted violations")
    parser.add_argument(
        "--write-baseline",
        action="store_true",
        help="write the current violations to --baseline and exit 0",
    )
    parser.add_argument("--json", action="store_true", help="emit JSON")
    args = parser.parse_args(argv)

    violations = scan_tree(Path(args.root))

    if args.write_baseline:
        if not args.baseline:
            parser.error("--write-baseline requires --baseline")
        payload = {"violations": [asdict(v) for v in violations]}
        Path(args.baseline).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {len(violations)} violation(s) to {args.baseline}")
        return 0

    baseline = _load_baseline(Path(args.baseline) if args.baseline else None)
    new_violations = [v for v in violations if v.key() not in baseline]

    if args.json:
        print(json.dumps({"violations": [asdict(v) for v in new_violations]}, indent=2))
    else:
        for v in new_violations:
            print(f"  [{v.rule}] {v.file}:{v.line} {v.message}")

    if new_violations:
        print(
            f"\nFAIL: {len(new_violations)} new architecture violation(s).",
            file=sys.stderr,
        )
        return 1
    print(f"OK: no new architecture violations ({len(baseline)} baselined).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
