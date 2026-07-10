# 03 — Plan Graph Specification

**Status:** Phase C0 — Constitution (Authoritative Specification)  
**Authority:** Subordinate to `PROJECT_CONSTITUTION_V4.md` and `01_PLANNER_ARCHITECTURE.md`  
**Purpose:** Define the structure and semantics of planner output graphs

---

## Purpose

Define the canonical structure for representing plans as directed acyclic graphs (DAGs). The Plan Graph is the primary output of the Planner and the primary input to the Runtime.

---

## Responsibilities

### Core Responsibilities

1. **Graph Construction** — Build valid plan representations
2. **Node Management** — Define and validate plan nodes
3. **Edge Management** — Define dependencies and execution order
4. **Validation** — Ensure graph is executable
5. **Transformation** — Convert between graph representations

### Non-Responsibilities

| Not Owned By | Owned By |
|-------------|----------|
| Plan execution | Runtime |
| Graph persistence | Memory |
| Graph visualization | UI |
| Graph optimization | Evaluator |

---

## Graph Structures

### PlanGraph

The top-level plan container.

```json
{
  "planGraph": {
    "graphId": "uuid",
    "goalId": "uuid",
    "createdAt": "ISO8601",
    "version": "1.0",
    "metadata": {
      "generatedBy": "planner_id",
      "confidence": 0.85,
      "modelUsed": "model_name",
      "generationTimeMs": 2340
    },
    "objectives": [ ... ],
    "tasks": [ ... ],
    "actions": [ ... ],
    "dependencies": [ ... ],
    "constraints": [ ... ],
    "metrics": { ... }
  }
}
```

### ObjectiveNode

Top-level goal representation.

```json
{
  "objectiveNode": {
    "nodeId": "obj_uuid",
    "nodeType": "OBJECTIVE",
    "label": "Deploy application to production",
    "description": "Complete deployment pipeline including build, test, and deploy",
    "priority": "high",
    "deadline": "ISO8601",
    "successCriteria": [
      "All tests pass",
      "Deployment successful",
      "Health checks green"
    ],
    "childTaskRefs": ["task_uuid_1", "task_uuid_2"],
    "status": "pending"
  }
}
```

### TaskNode

Mid-level work unit.

```json
{
  "taskNode": {
    "nodeId": "task_uuid",
    "nodeType": "TASK",
    "objectiveRef": "obj_uuid",
    "label": "Build application",
    "description": "Compile and package the application",
    "priority": "high",
    "estimatedDuration": "5m",
    "requiredCapabilities": ["build_tool"],
    "childActionRefs": ["action_uuid_1", "action_uuid_2"],
    "status": "pending",
    "retryPolicy": {
      "maxRetries": 2,
      "backoffMultiplier": 1.5
    }
  }
}
```

### ActionNode

Atomic execution unit.

```json
{
  "actionNode": {
    "nodeId": "action_uuid",
    "nodeType": "ACTION",
    "taskRef": "task_uuid",
    "label": "Run build command",
    "description": "Execute 'npm run build' in project directory",
    "capability": "shell_execute",
    "parameters": {
      "command": "npm run build",
      "workingDirectory": "/project",
      "timeout": 300
    },
    "requiresApproval": false,
    "riskLevel": "low",
    "estimatedDuration": "2m",
    "rollbackAction": {
      "capability": "shell_execute",
      "parameters": { "command": "npm run clean" }
    },
    "status": "pending",
    "executionConfig": {
      "environment": {},
      "secrets": []
    }
  }
}
```

### DependencyEdge

Relationships between nodes.

```json
{
  "dependencyEdge": {
    "edgeId": "edge_uuid",
    "edgeType": "DEPENDS_ON",
    "sourceNode": "action_uuid_1",
    "targetNode": "action_uuid_2",
    "condition": null,
    "failurePropagation": {
      "onSourceFailure": "fail|cancel|skip|continue",
      "onSourceTimeout": "cancel|skip|continue"
    }
  }
}
```

---

## Graph Properties

### Can DAGs Branch?

**YES.** Plan graphs may have multiple outgoing edges from a single node.

```text
    ┌─────────────┐
    │  Task A     │
    └──────┬──────┘
           │
     ┌─────┴─────┐
     ▼           ▼
┌─────────┐ ┌─────────┐
│Action B │ │Action C │
└─────────┘ └─────────┘
```

### Can DAGs Merge?

**YES.** Plan graphs may have multiple incoming edges to a single node.

```text
┌─────────┐
│Action A │
└────┬────┘
     │
┌────┴────┐
▼         │
┌─────────┐│
│Action B │◀┌─────────┐
└─────────┘ │Action C │
            └─────────┘
```

### Can DAGs Recurse?

**NO.** Recursion is forbidden in plan graphs.

```text
Prohibited:
    ┌─────────────┐
    │  Node A     │
    └──────┬──────┘
           │
           ▼
    ┌─────────────┐
    │  Node B     │──────┐
    └─────────────┘      │
           │             │
           ▼             │
    ┌─────────────┐      │
    │  Node C     │◀─────┘
    └─────────────┘
```

### Can DAGs Contain Cycles?

**NO.** Cycles are explicitly prohibited.

### Can DAGs Have Parallel Branches?

**YES.** Independent branches can execute in parallel.

```text
┌─────────────────────────────────────┐
│           Entry Point               │
└─────────────┬───────────────────────┘
              │
    ┌─────────┴─────────┐
    ▼                   ▼
┌─────────┐       ┌─────────┐
│Branch A │       │Branch B │
│(parallel│       │(parallel│
│execute) │       │execute) │
└────┬────┘       └────┬────┘
     │                   │
     └─────────┬─────────┘
               ▼
       ┌───────────────┐
       │  Merge Point  │
       └───────────────┘
```

---

## Size Constraints

### Maximum Graph Depth

```yaml
graph_limits:
  max_depth: 10
  max_nodes: 100
  max_edges: 200
  max_parallel_branches: 5
  
reasoning:
  depth_reason: "Prevents infinite planning loops"
  nodes_reason: "Context window limitations"
  branches_reason: "Resource allocation constraints"
```

### Maximum Graph Size

```json
{
  "graphSizeLimits": {
    "maxObjectives": 5,
    "maxTasksPerObjective": 20,
    "maxActionsPerTask": 10,
    "maxTotalNodes": 100,
    "maxTotalEdges": 200,
    "maxParallelPaths": 5,
    "maxSerializationBytes": 1048576
  }
}
```

---

## Validation Rules

### Node Validation

```python
def validate_node(node):
    errors = []
    
    # Required fields
    if not node.nodeId:
        errors.append("nodeId required")
    if not node.nodeType:
        errors.append("nodeType required")
    
    # Type-specific validation
    if node.nodeType == "ACTION":
        if not node.capability:
            errors.append("Action requires capability")
        if not node.parameters:
            errors.append("Action requires parameters")
    
    # Constraint validation
    if node.constraints:
        for constraint in node.constraints:
            if not is_satisfiable(constraint):
                errors.append(f"Unsatisfiable constraint: {constraint}")
    
    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors
    )
```

### Edge Validation

```python
def validate_edge(edge, graph):
    errors = []
    
    # Node existence
    if edge.sourceNode not in graph.nodes:
        errors.append(f"Source node {edge.sourceNode} not found")
    if edge.targetNode not in graph.nodes:
        errors.append(f"Target node {edge.targetNode} not found")
    
    # No self-loops
    if edge.sourceNode == edge.targetNode:
        errors.append("Self-loops prohibited")
    
    # No cycles
    if would_create_cycle(edge, graph):
        errors.append("Cycles prohibited")
    
    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors
    )
```

### Graph Validation

```python
def validate_graph(graph):
    errors = []
    warnings = []
    
    # Node validation
    for node in graph.nodes:
        result = validate_node(node)
        errors.extend(result.errors)
    
    # Edge validation
    for edge in graph.edges:
        result = validate_edge(edge, graph)
        errors.extend(result.errors)
    
    # Structural validation
    if not has_single_entry_point(graph):
        errors.append("Graph must have single entry point")
    if has_unreachable_nodes(graph):
        warnings.append("Some nodes are unreachable")
    
    # Size validation
    if len(graph.nodes) > MAX_NODES:
        errors.append(f"Graph exceeds max nodes: {len(graph.nodes)}")
    if len(graph.edges) > MAX_EDGES:
        errors.append(f"Graph exceeds max edges: {len(graph.edges)}")
    
    return GraphValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings
    )
```

---

## Execution Ordering

### Topological Sort

```python
def compute_execution_order(graph):
    # Compute in-degree for each node
    in_degree = {node.nodeId: 0 for node in graph.nodes}
    for edge in graph.edges:
        in_degree[edge.targetNode] += 1
    
    # Initialize queue with nodes that have no dependencies
    queue = [node for node in graph.nodes if in_degree[node.nodeId] == 0]
    execution_order = []
    
    while queue:
        # Process next ready node
        current = queue.pop(0)
        execution_order.append(current)
        
        # Update dependent nodes
        for edge in graph.edges:
            if edge.sourceNode == current.nodeId:
                in_degree[edge.targetNode] -= 1
                if in_degree[edge.targetNode] == 0:
                    queue.append(find_node(edge.targetNode))
    
    # Check for cycles
    if len(execution_order) != len(graph.nodes):
        raise CycleDetectedError()
    
    return execution_order
```

### Parallel Execution Groups

```python
def compute_parallel_groups(execution_order, graph):
    groups = []
    current_group = []
    
    for node in execution_order:
        # Check if node can run in parallel with current group
        can_parallel = all(
            not depends_on(node, other, graph)
            for other in current_group
        )
        
        if can_parallel:
            current_group.append(node)
        else:
            if current_group:
                groups.append(current_group)
            current_group = [node]
    
    if current_group:
        groups.append(current_group)
    
    return groups
```

---

## Dependency Resolution

### Resolution Algorithm

```python
def resolve_dependencies(graph):
    resolved = {}
    unresolved = set(graph.nodes)
    
    while unresolved:
        # Find nodes with no unresolved dependencies
        ready = [
            node for node in unresolved
            if all(
                dep in resolved
                for dep in get_dependencies(node, graph)
            )
        ]
        
        if not ready:
            raise CircularDependencyError()
        
        # Resolve ready nodes
        for node in ready:
            resolved[node.nodeId] = node
            unresolved.remove(node)
    
    return resolved
```

---

## Failure Propagation

### Edge Failure Modes

```yaml
failure_propagation:
  on_source_failure:
    options:
      - fail: "Entire plan fails"
      - cancel: "Cancel dependent nodes"
      - skip: "Skip dependent nodes"
      - continue: "Continue dependent nodes"
    default: cancel
  
  on_source_timeout:
    options:
      - cancel: "Cancel dependent nodes"
      - skip: "Skip dependent nodes"
      - continue: "Continue dependent nodes"
    default: skip
  
  on_source_success:
    behavior: "Continue to dependent nodes"
```

---

## Cancellation Behavior

### Cancellation Request

```json
{
  "cancellationRequest": {
    "planId": "uuid",
    "reason": "user_requested|goal_obsolete|resource_exhausted|...",
    "scope": "full|partial",
    "targetNodes": ["node_uuids"]  // for partial cancellation
  }
}
```

### Cancellation Rules

```python
def cancel_plan(cancellation_request):
    plan = get_plan(cancellation_request.planId)
    
    if cancellation_request.scope == "full":
        # Cancel all pending/running nodes
        for node in plan.nodes:
            if node.status in ["pending", "running"]:
                node.status = "cancelled"
    
    elif cancellation_request.scope == "partial":
        # Cancel specific nodes and dependents
        target_nodes = set(cancellation_request.targetNodes)
        to_cancel = compute_dependents(target_nodes, plan)
        for node in to_cancel:
            if node.status in ["pending", "running"]:
                node.status = "cancelled"
    
    # Publish cancellation event
    publish_event("plan.cancelled", {
        "planId": plan.planId,
        "cancelledNodes": to_cancel,
        "reason": cancellation_request.reason
    })
```

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|------------|
| PGS-001 | DAGs can branch | Enables parallel planning |
| PGS-002 | DAGs can merge | Enables convergence |
| PGS-003 | No recursion | Prevents infinite loops |
| PGS-004 | No cycles | Enables deterministic ordering |
| PGS-005 | Max depth = 10 | Balances complexity vs capability |
| PGS-006 | Failure propagation configurable | Flexibility vs safety |

---

## Tradeoffs

### Benefits

1. **Clear Semantics** — Unambiguous execution order
2. **Parallelism** — Independent branches can run concurrently
3. **Validation** — Invalid graphs caught early
4. **Debugging** — Clear dependency tracking
5. **Optimization** — Enables execution optimization

### Costs

1. **Complexity** — Graph representation is more complex than linear plans
2. **Validation Overhead** — Must validate before execution
3. **Visualization** — Harder to visualize than linear plans
4. **Serialization** — Larger than linear representations

---

## Failure Modes

| Mode | Detection | Impact | Recovery |
|------|-----------|--------|----------|
| Cycle detected | Validation | Invalid plan | Reject, regenerate |
| Max depth exceeded | Validation | Plan too complex | Simplify or split |
| Unreachable nodes | Validation | Inefficient plan | Warn, prune |
| No entry point | Validation | Invalid graph | Reject |
| Parallel limit exceeded | Validation | Resource issue | Reduce parallelism |

---

## Recovery Strategy

```python
def recover_from_graph_failure(failure):
    if failure == "CYCLE_DETECTED":
        return break_cycle_heuristically()
    elif failure == "MAX_DEPTH_EXCEEDED":
        return decompose_plan()
    elif failure == "UNREACHABLE_NODES":
        return prune_unreachable()
    elif failure == "PARALLEL_LIMIT_EXCEEDED":
        return reduce_parallelism()
    else:
        return escalate_to_human()
```

---

## Future Evolution Path

### Phase C1: Conditional Branching

- Add conditional edges (if/then/else)
- Enable dynamic path selection
- Support loop structures (bounded)

### Phase C2: Nested Graphs

- Support sub-graphs
- Enable graph composition
- Add hierarchical planning

### Phase C3: Probabilistic Graphs

- Support uncertainty in edges
- Enable probabilistic planning
- Add success probability to paths

---

## References

| Document | Role |
|----------|------|
| `PROJECT_CONSTITUTION_V4.md` | Supreme authority |
| `01_PLANNER_ARCHITECTURE.md` | Planner requirements |
| `05_PLAN_EVALUATION_FRAMEWORK.md` | Graph evaluation metrics |
| `06_GOAL_DECOMPOSITION_ENGINE.md` | Goal-to-graph transformation |

---

## Revision History

| Date | Change | Author |
|------|--------|--------|
| 2026-07-10 | Initial C0 Constitution | ACC Planner Evolution Program |
