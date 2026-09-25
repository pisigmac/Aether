# Diffusion budget

One Butterfly horizon is `propagate` in `engine/aether/physics/butterfly.py`. The graph is sparse: each node has three outgoing import edges, destinations `(i + step * 997) % n`, origin `"0"`, horizon 8 months. p95 is nearest-rank over 21 timed calls after one warmup.

The bar is one horizon, not the four horizons a forecast builds.

| Nodes | Bar | Measured p95 | Min | Max |
| --- | --- | --- | --- | --- |
| 10,000 | 250 ms | 79.9 ms | 36.3 ms | 95.7 ms |
| 50,000 | 800 ms | 398.1 ms | 199.1 ms | 413.6 ms |

NetworkX `snapshot_graph` plus `propagate` missed that bar before this change: about 307 ms at 10,000 nodes and 1.2 s at 50,000 (7 calls, same graph shape). The walk itself stops after a few hops because intensity decays below 0.08. The time was the graph build.

Diffusion now walks a Python adjacency list. Metrics and cycle detection still use NetworkX. There is no Rust kernel.

The decay on a weight-1 chain at month 0 is unchanged: intensities 1.0, 0.5, 0.18, then stop.
