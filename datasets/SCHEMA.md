# Evolution Record schema

Phase 1 persists one row per sampled commit so a later training job can drop in without rewriting the IR or UI.

| Field | Type | Notes |
| --- | --- | --- |
| `repo_id` | string | Stable hash of repo path |
| `commit_sha` | string | Git SHA or `WORKING_TREE` |
| `authored_at` | ISO-8601 | Commit timestamp |
| `snapshot_hash` | string | Hash of IR nodes + edges |
| `metric_vector` | object | `mass`, `coupling`, `churn`, `cycles`, `god_module_count`, `contract_leak_count` |
| `pattern_labels` | string[] | `god_module`, `cyclic_dep`, `schema_leak`, `chatty_rpc`, `unbounded_list`, `missing_index` |
| `delta_from_prev` | object | `nodes_added/removed`, `edges_added/removed` |
| `horizon_target` | object? | Same metric vector at the next sample (supervised label) |

Rows live in SQLite table `evolution`. IR version is `1`.
