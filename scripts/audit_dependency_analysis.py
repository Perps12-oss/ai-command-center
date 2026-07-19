#!/usr/bin/env python3
"""Static audit: service graph, EventBus topology, Workspace OS adoption."""

from __future__ import annotations

import ast
import re
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PKG = PROJECT_ROOT / "ai_command_center"

# ── helpers ──────────────────────────────────────────────────────────────────

def read_py(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def py_files_under(*roots: Path) -> list[Path]:
    out: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for p in root.rglob("*.py"):
            if "__pycache__" in p.parts:
                continue
            out.append(p)
    return sorted(set(out))


def module_path(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix().replace(".py", "").replace("/", ".")


def class_name_in_file(path: Path) -> str | None:
    try:
        tree = ast.parse(read_py(path))
    except SyntaxError:
        return None
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name.endswith("Service"):
            return node.name
    return None


def attr_to_service(attr: str, known: set[str]) -> str | None:
    """Map self._entity_service -> EntityService."""
    a = attr.lstrip("_")
    if not a.endswith("_service"):
        return None
    base = a[: -len("_service")]
    cand = "".join(part.capitalize() for part in base.split("_")) + "Service"
    return cand if cand in known else None


# ── 1. Service dependency graph ─────────────────────────────────────────────

SERVICE_SCAN_ROOTS = [
    PKG / "services",
    PKG / "core",
    PKG / "telemetry",
]

SKIP_FILES = {"base.py", "base_service.py", "states.py", "__init__.py"}


def build_service_graph() -> dict:
    files = [p for p in py_files_under(*SERVICE_SCAN_ROOTS) if p.name not in SKIP_FILES]
    class_to_file: dict[str, str] = {}
    file_to_class: dict[str, str] = {}
    for p in files:
        cn = class_name_in_file(p)
        if cn:
            rel = p.relative_to(PROJECT_ROOT).as_posix()
            class_to_file[cn] = rel
            file_to_class[rel] = cn

    known = set(class_to_file.keys())
    inject: dict[str, set[str]] = defaultdict(set)
    call: dict[str, set[str]] = defaultdict(set)
    import_dep: dict[str, set[str]] = defaultdict(set)

    # Constructor injection via service_factory
    factory = PKG / "core" / "service_factory.py"
    ftext = read_py(factory)
    # Pattern: FooService(bus, bar_service) or FooService(entity_service, bus)
    for m in re.finditer(r"(\w+Service)\s*\(([^)]*)\)", ftext):
        callee, args = m.group(1), m.group(2)
        if callee not in known:
            continue
        for arg in re.findall(r"(\w+_service)", args):
            dep = attr_to_service(arg, known) or attr_to_service("_" + arg, known)
            if dep and dep != callee:
                inject[callee].add(dep)

    # WorkspaceOsService(...) multi-line
    wos_match = re.search(
        r"WorkspaceOsService\s*\(\s*([\s\S]*?)\n\s*\)",
        ftext,
    )
    if wos_match:
        block = wos_match.group(1)
        for kw in re.findall(r"(\w+_service)\s*=", block):
            dep = attr_to_service(kw, known)
            if dep:
                inject["WorkspaceOsService"].add(dep)

    # Per-file: __init__ annotations + self._x_service calls
    for p in files:
        cn = class_name_in_file(p)
        if not cn:
            continue
        text = read_py(p)
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "__init__":
                for arg in node.args.args:
                    if arg.annotation and hasattr(ast, "unparse"):
                        ann = ast.unparse(arg.annotation)
                        for sc in known:
                            if sc in ann and sc != cn:
                                inject[cn].add(sc)

        for m in re.finditer(r"self\.(_[a-z_]+_service)\.", text):
            dep = attr_to_service(m.group(1), known)
            if dep and dep != cn:
                call[cn].add(dep)

        # Direct import of another service module
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                mod = node.module
                if "service" in mod.lower():
                    tail = mod.split(".")[-1]
                    # module entity_service -> EntityService
                    cand = "".join(x.capitalize() for x in tail.split("_"))
                    if cand in known and cand != cn:
                        import_dep[cn].add(cand)

    # Bus-native: no direct dep between registered BaseServices in services/
    # except via factory injection

    all_edges: list[tuple[str, str, str]] = []
    for cn in sorted(known):
        for dep in sorted(inject.get(cn, set())):
            all_edges.append((cn, dep, "inject"))
        for dep in sorted(call.get(cn, set())):
            if dep not in inject.get(cn, set()):
                all_edges.append((cn, dep, "call"))
            elif (cn, dep, "call") not in [(a, b, k) for a, b, k in all_edges]:
                pass
        for dep in sorted(call.get(cn, set())):
            if dep in inject.get(cn, set()):
                all_edges.append((cn, dep, "call"))

    # Dedupe edge kinds
    edge_map: dict[tuple[str, str], set[str]] = defaultdict(set)
    for src, dst, kind in all_edges:
        edge_map[(src, dst)].add(kind)
    for src, dst in list(edge_map.keys()):
        if "inject" in edge_map[(src, dst)] and "call" in edge_map[(src, dst)]:
            edge_map[(src, dst)] = {"inject", "call"}

    graph: dict[str, set[str]] = defaultdict(set)
    for (src, dst), kinds in edge_map.items():
        graph[src].add(dst)

    def find_cycles(g: dict[str, set[str]]) -> list[list[str]]:
        cycles: list[list[str]] = []
        seen: set[tuple[str, ...]] = set()

        def dfs(node: str, path: list[str], on_stack: set[str]) -> None:
            if node in on_stack:
                idx = path.index(node)
                cyc = path[idx:] + [node]
                key = tuple(cyc)
                if key not in seen:
                    seen.add(key)
                    cycles.append(cyc)
                return
            if node in path:
                return
            on_stack.add(node)
            for nb in sorted(g.get(node, [])):
                dfs(nb, path + [node], on_stack)
            on_stack.discard(node)

        for n in sorted(g.keys()):
            dfs(n, [], set())
        return cycles

    cycles = find_cycles(graph)

    # Bus-only services (no direct outbound edges)
    bus_only = sorted(cn for cn in known if cn not in graph or not graph[cn])

    return {
        "classes": class_to_file,
        "edges": edge_map,
        "graph": graph,
        "cycles": cycles,
        "bus_only": bus_only,
        "inject": inject,
        "call": call,
    }


# ── 2. EventBus topic topology ───────────────────────────────────────────────

def resolve_topic(node: ast.AST, topic_names: dict[str, str]) -> str | None:
    """Resolve subscribe/publish first arg to topic string."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name) and node.id in topic_names:
        return topic_names[node.id]
    if isinstance(node, ast.Attribute):
        # T.UI_COMMAND style
        try:
            if hasattr(ast, "unparse"):
                expr = ast.unparse(node)
                if expr in topic_names:
                    return topic_names[expr]
                # module alias
                for k, v in topic_names.items():
                    if expr == k or expr.endswith("." + k.split(".")[-1]):
                        return v
        except Exception:
            pass
    return None


def load_topic_constants() -> dict[str, str]:
    topics_file = PKG / "core" / "events" / "topics.py"
    text = read_py(topics_file)
    names: dict[str, str] = {}
    for m in re.finditer(r"^([A-Z][A-Z0-9_]*)\s*=\s*[\"']([^\"']+)[\"']", text, re.M):
        names[m.group(1)] = m.group(2)
    return names


def analyze_eventbus() -> dict:
    topic_names = load_topic_constants()
    all_py = py_files_under(PKG, PROJECT_ROOT / "scripts", PROJECT_ROOT / "tests")

    publishers: dict[str, set[str]] = defaultdict(set)
    subscribers: dict[str, set[str]] = defaultdict(set)

    for p in all_py:
        rel = p.relative_to(PROJECT_ROOT).as_posix()
        try:
            tree = ast.parse(read_py(p))
        except SyntaxError:
            continue

        # Track local imports from topics
        local_topics = dict(topic_names)
        for node in tree.body:
            if isinstance(node, ast.ImportFrom) and node.module and "topics" in node.module:
                for alias in node.names:
                    if alias.name in topic_names:
                        local_topics[alias.asname or alias.name] = topic_names[alias.name]

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            method = None
            if isinstance(func, ast.Attribute):
                method = func.attr
            if method not in ("publish", "subscribe"):
                continue
            if not node.args:
                continue
            topic = resolve_topic(node.args[0], local_topics)
            if not topic:
                # try string literal in common patterns
                if isinstance(node.args[0], ast.Constant):
                    topic = str(node.args[0].value)
            if topic:
                if method == "publish":
                    publishers[topic].add(rel)
                else:
                    subscribers[topic].add(rel)

    all_topics = sorted(set(publishers) | set(subscribers))
    rows = []
    for t in all_topics:
        pub_n = len(publishers[t])
        sub_n = len(subscribers[t])
        fanout = sub_n
        rows.append((t, pub_n, sub_n, fanout, publishers[t], subscribers[t]))

    rows.sort(key=lambda r: (-(r[1] + r[2]), -r[2], r[0]))

    dead = [t for t in all_topics if not publishers[t] or not subscribers[t]]
    orphan_subs = [t for t in all_topics if subscribers[t] and not publishers[t]]
    orphan_pubs = [t for t in all_topics if publishers[t] and not subscribers[t]]

    return {
        "rows": rows,
        "dead": dead,
        "orphan_subs": orphan_subs,
        "orphan_pubs": orphan_pubs,
        "publishers": publishers,
        "subscribers": subscribers,
    }


# ── 3. Workspace OS adoption ─────────────────────────────────────────────────

WORKSPACE_TOPIC_PREFIXES = (
    "workspace.",
    "entity.",
    "relationship.",
    "timeline.",
    "ui.create_",
    "ui.launch_",
    "ui.search_workspace",
    "permission.",
    "snapshot.",
    "capability.",
)

WORKSPACE_UI_FILES = [
    "ai_command_center/ui/views/workspace_view.py",
    "ai_command_center/ui/workspace_os_controller.py",
    "ai_command_center/ui/workspace_os_inspector.py",
    "ai_command_center/ui/workspace_os_dialogs.py",
]


def analyze_workspace_os(eb: dict) -> dict:
    topic_names = load_topic_constants()
    workspace_topics = [
        v
        for v in topic_names.values()
        if any(v.startswith(p) or p.rstrip("_") in v for p in WORKSPACE_TOPIC_PREFIXES)
        or "workspace" in v
        or "entity" in v
    ]
    workspace_topics = sorted(set(workspace_topics))

    pub = eb["publishers"]
    sub = eb["subscribers"]

    wos_pub_files: set[str] = set()
    wos_sub_files: set[str] = set()
    for t in workspace_topics:
        wos_pub_files |= pub.get(t, set())
        wos_sub_files |= sub.get(t, set())

    # All UI publish sites
    ui_controller = PKG / "ui" / "controller.py"
    wos_controller = PKG / "ui" / "workspace_os_controller.py"
    ui_pub_topics: set[str] = set()
    wos_pub_topics: set[str] = set()

    for path, bucket in ((ui_controller, ui_pub_topics), (wos_controller, wos_pub_topics)):
        if not path.exists():
            continue
        tree = ast.parse(read_py(path))
        local = dict(topic_names)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "publish" and node.args:
                    t = resolve_topic(node.args[0], local)
                    if t:
                        bucket.add(t)

    # Feature routing in app/shell
    app_py = read_py(PKG / "ui" / "app.py")
    default_workspace = '_default_view = "workspace"' in app_py or 'default_view = "workspace"' in app_py

    # Service factory: workspace_os_enabled default
    factory = read_py(PKG / "core" / "service_factory.py")
    wos_default_on = "workspace_os_enabled: bool = True" in factory

    # Count services: wos cluster vs bus-only palette stack
    wos_services = {
        "WorkspaceOsService",
        "WorkspaceService",
        "EntityService",
        "RelationshipService",
        "TimelineService",
        "SnapshotService",
        "ObservabilityService",
        "AICapabilityRegistryService",
        "CommandPaletteService",
        "PermissionService",
    }
    registered_bus = {
        "SettingsService",
        "CommandRouterService",
        "ModelRouterService",
        "ToolRegistryService",
        "ToolExecutorService",
        "WorkflowEngineService",
        "ShellToolService",
        "PluginRegistryService",
        "OllamaHttpService",
        "OpenAIHttpService",
        "ObsidianService",
        "MemoryGraphService",
        "SessionService",
        "AgentRuntimeService",
        "ChatHandlerService",
        "TelemetryService",
        "ChatExportService",
        "SystemMonitorService",
    }

    # Topic traffic share estimate (static): workspace-related vs all
    all_pub_count = sum(len(v) for v in pub.values())
    wos_pub_count = sum(len(pub.get(t, set())) for t in workspace_topics)

    all_sub_count = sum(len(v) for v in sub.values())
    wos_sub_count = sum(len(sub.get(t, set())) for t in workspace_topics)

    # UI view registration
    shell = read_py(PKG / "ui" / "shell" / "view_manager.py") if (PKG / "ui" / "shell" / "view_manager.py").exists() else ""
    views_in_shell = re.findall(r'"(home|workspace|chat|notes|memory|settings|system|plugins)"', shell)

    return {
        "workspace_topics": workspace_topics,
        "wos_pub_files": wos_pub_files,
        "wos_sub_files": wos_sub_files,
        "ui_pub_topics": ui_pub_topics,
        "wos_pub_topics": wos_pub_topics,
        "default_workspace": default_workspace,
        "wos_default_on": wos_default_on,
        "wos_services": wos_services,
        "registered_bus": registered_bus,
        "all_pub_count": all_pub_count,
        "wos_pub_count": wos_pub_count,
        "all_sub_count": all_sub_count,
        "wos_sub_count": wos_sub_count,
        "views_in_shell": views_in_shell,
        "workspace_ui_files": WORKSPACE_UI_FILES,
    }


def main() -> None:
    sg = build_service_graph()
    eb = analyze_eventbus()
    wos = analyze_workspace_os(eb)

    print("=" * 72)
    print("PART X — SERVICE DEPENDENCY ANALYSIS")
    print("=" * 72)
    print(f"Service classes scanned: {len(sg['classes'])}")
    print(f"Direct dependency edges: {len(sg['edges'])}")
    print(f"Services with outbound direct deps: {sum(1 for k,v in sg['graph'].items() if v)}")
    print(f"Bus-only services (no direct outbound deps): {len(sg['bus_only'])}")
    print()
    print("--- Complete direct-dependency graph (composition / call edges) ---")
    for (src, dst), kinds in sorted(sg["edges"].items()):
        print(f"  {src} --[{','.join(sorted(kinds))}]--> {dst}")
    print()
    print(f"Cycles detected: {len(sg['cycles'])}")
    for c in sg["cycles"]:
        print(f"  {' -> '.join(c)}")
    print()
    print("--- Bus-native services (factory-registered, no direct peer edges) ---")
    for cn in sorted(sg["bus_only"]):
        if cn in sg["classes"]:
            print(f"  {cn}")

    print()
    print("=" * 72)
    print("PART X — EVENTBUS TOPOLOGY (static publish/subscribe sites)")
    print("=" * 72)
    print(f"Distinct topics with activity: {len(eb['rows'])}")
    print()
    print("--- Top 20 topics by (publishers + subscribers) ---")
    for t, pub_n, sub_n, fanout, _, _ in eb["rows"][:20]:
        crit = "SYNC_CRITICAL" if t in {
            "ui.command",
            "execution.authority.decision",
            "goal.submit.request",
            "settings.snapshot",
            "settings.set_request",
        } else ""
        print(f"  {t:40s}  pub={pub_n:2d}  sub={sub_n:2d}  fan-out={fanout:2d}  {crit}")
    print()
    print(f"Dead/orphan topics (no pub or no sub): {len(eb['dead'])}")
    for t in sorted(eb["dead"])[:15]:
        print(f"  {t}  pub={len(eb['publishers'][t])} sub={len(eb['subscribers'][t])}")
    if len(eb["dead"]) > 15:
        print(f"  ... and {len(eb['dead'])-15} more")
    print()
    print(f"Orphan subscribers (sub but no pub): {len(eb['orphan_subs'])}")
    for t in sorted(eb["orphan_subs"])[:10]:
        print(f"  {t}")
    print()
    print(f"Orphan publishers (pub but no sub): {len(eb['orphan_pubs'])}")
    for t in sorted(eb["orphan_pubs"])[:10]:
        print(f"  {t}")

    print()
    print("=" * 72)
    print("PART X — WORKSPACE OS ADOPTION ANALYSIS")
    print("=" * 72)
    print(f"Workspace-related topics: {len(wos['workspace_topics'])}")
    print(f"Default home = workspace: {wos['default_workspace']}")
    print(f"workspace_os_enabled default True in factory: {wos['wos_default_on']}")
    print()
    print("--- Workspace topic publisher/subscriber file share ---")
    total_py = len(py_files_under(PKG))
    print(f"  Files publishing workspace topics: {len(wos['wos_pub_files'])} / {total_py} package modules")
    print(f"  Files subscribing workspace topics: {len(wos['wos_sub_files'])} / {total_py}")
    print()
    print("--- Static traffic share (publish+subscribe site counts) ---")
    pub_share = 100.0 * wos["wos_pub_count"] / max(wos["all_pub_count"], 1)
    sub_share = 100.0 * wos["wos_sub_count"] / max(wos["all_sub_count"], 1)
    combined = 100.0 * (wos["wos_pub_count"] + wos["wos_sub_count"]) / max(
        wos["all_pub_count"] + wos["all_sub_count"], 1
    )
    print(f"  Workspace publish sites: {wos['wos_pub_count']} / {wos['all_pub_count']} ({pub_share:.1f}%)")
    print(f"  Workspace subscribe sites: {wos['wos_sub_count']} / {wos['all_sub_count']} ({sub_share:.1f}%)")
    print(f"  Combined static site share: {combined:.1f}%")
    print()
    print("--- UIController publish topics (palette stack) ---")
    for t in sorted(wos["ui_pub_topics"]):
        print(f"  {t}")
    print("--- WorkspaceOsController publish topics ---")
    for t in sorted(wos["wos_pub_topics"]):
        print(f"  {t}")
    print()
    print("--- Views registered in shell ---")
    print(f"  {wos['views_in_shell']}")
    print()
    print("--- Features BYPASSING Workspace OS (bus-native palette path) ---")
    bypass = [
        "Chat (UI_COMMAND -> ExecutionAuthority -> LLM step -> LLM)",
        "Notes/Obsidian search (NOTE_* topics)",
        "Memory graph (MEMORY_* topics)",
        "Plugins (PLUGIN_* topics)",
        "Settings (SETTINGS_* topics)",
        "System monitor (SYSTEM_SNAPSHOT)",
        "Shell tools (ExecutionOrchestrator -> TOOL_INVOKE)",
        "Agents (AGENT_* topics)",
        "Workflows (WORKFLOW_* topics)",
    ]
    for b in bypass:
        print(f"  - {b}")
    print()
    print("--- Features USING Workspace OS ---")
    using = [
        "Workspace canvas view (entity grid from AppState workspace_entities)",
        "Create workspace/card/resource (UI_CREATE_* -> WorkspaceOsService)",
        "Launch resource (UI_LAUNCH_RESOURCE -> action_registry)",
        "Entity inspector / dialogs",
        "Entity-scoped chat sessions (entity_conversation_id in SessionService)",
        "Permission checks for agent spawn (PermissionService)",
    ]
    for u in using:
        print(f"  - {u}")


if __name__ == "__main__":
    main()
