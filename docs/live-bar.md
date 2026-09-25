# Live bar

The live bar is a small program you install. It draws one strip across the bottom of the desktop and stays above other windows. An IDE plugin tells that strip which repository is open. Changing repos changes the strip.

The engine is still the system of record. The strip is one reading from `GET /v1/live?repo=`. The dashboard keeps the full Radar, Butterfly, Ghost Lab, and Cost Horizon.

## Install the desktop bar

From a checkout, with the engine already on port 18100:

```bash
engine/.venv/bin/aether livebar
```

The strip uses the repo written by the IDE plugin. If that file is empty, it uses the git checkout you started it from. Click the text to open Radar. Click `hide` to close the strip. It stays above other windows along the bottom edge. A maximized window can sit underneath it.

One reading and no window:

```bash
engine/.venv/bin/aether livebar --print
```

`--api` defaults to `http://127.0.0.1:18100`. `--dashboard` defaults to `http://127.0.0.1:13100`.

## Install the IDE plugin

The plugin is `ide/aether-livebar`. It works in Cursor and VS Code.

1. Open the command palette.
2. Choose **Extensions: Install from Location** (Cursor) or **Developer: Install Extension from Location** (VS Code).
3. Select the `ide/aether-livebar` folder.
4. Reload the window.

On startup, and whenever that window gains focus or its workspace folders change, the plugin writes the open folder to `~/.aether/live-repo`. The desktop strip reads that file about once a second and asks the engine for that repo. The command **Aether: Show desktop live bar** starts the strip if it is not already running.

The plugin looks for `engine/.venv/bin/aether` inside the open folder, then `aether` on `PATH`. Set `AETHER_BIN` if the executable lives somewhere else.

## What the strip shows

The cell is the hottest module on the frame nearest **+8 months**. The line is the repo name, the path, the band, and the pressure. Up to three more modules sit on the right.

| Band | Pressure |
| --- | --- |
| Calm | P < 0.6 |
| Watch | P 0.6–1.2 |
| High-pressure | P ≥ 1.2 |
| Storm | the cell is in a collision |

A path match uses the ingested checkout path. A directory name matches only when exactly one universe uses that name. Two different `app` checkouts are not treated as the same repo.

While a job for that repo is queued or running, the strip shows the percent and the stage, for example `Aether  40%  Parsing snapshot 6/15`. Pressure stays hidden until a forecast exists. A repo with no universe and no running job says `no forecast yet`. A failed ingest with no universe shows the error and still does not invent a pressure number.

## What it does not do

The strip does not rebuild the 24-month timeline on each keystroke, and it does not read an unsaved editor buffer. A structural change shows up after a changeset or a new ingest, on the next poll.

The dashboard also draws a reading along the bottom of Radar, Butterfly, Ghost Lab, Cost Horizon, and Ingest. That one follows the Aether checkout when a universe with that name exists. The desktop strip is the one that follows whichever repo the IDE just focused.
