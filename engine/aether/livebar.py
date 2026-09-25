"""Always-on-top desktop bar. The IDE plugin writes the active repo path.

The engine virtualenv often has no GUI toolkit. When GTK is missing there, this
re-runs under the system Python, which can import gi without importing the engine.
"""

from __future__ import annotations

import json
import os
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

from aether.live import headline, live_repo_path, livebar_pid_path

BAND_COLOR = {
    "calm": "#7dbea8",
    "watch": "#e7a15a",
    "high-pressure": "#e36b5a",
    "storm": "#f59e0b",
}
INGEST_COLOR = "#7eb6ff"
BAR_BG = "#0b1f33"
BAR_FG = "#e7eef2"
MUTED = "#9aa89a"


def read_repo_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def git_root(start: Path) -> str:
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return str(candidate)
    return str(current)


def fetch_live(api: str, repo: str, timeout: float = 20) -> dict:
    query = urllib.parse.urlencode({"repo": repo})
    url = api.rstrip("/") + "/v1/live?" + query
    with urllib.request.urlopen(url, timeout=timeout) as response:
        payload = json.load(response)
    if not isinstance(payload, dict):
        raise ValueError("live reading was not an object")
    return payload


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _is_livebar(pid: int) -> bool:
    try:
        command = Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\x00", b" ").decode()
    except OSError:
        return False
    return "livebar" in command


def claim_pid(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        try:
            previous = int(path.read_text(encoding="utf-8").strip() or "0")
        except ValueError:
            previous = 0
        if previous and previous != os.getpid() and _pid_alive(previous) and _is_livebar(previous):
            os.kill(previous, 15)
    path.write_text(str(os.getpid()), encoding="utf-8")


def _reexec_system_python(api: str, dashboard: str, repo: str) -> None:
    if os.environ.get("AETHER_LIVEBAR_INNER") == "1":
        raise SystemExit("GTK is not available to the live bar.")
    engine_root = str(Path(__file__).resolve().parents[1])
    env = os.environ.copy()
    env["PYTHONPATH"] = engine_root + os.pathsep + env.get("PYTHONPATH", "")
    env["AETHER_LIVEBAR_INNER"] = "1"
    env["GDK_BACKEND"] = "x11"
    env["AETHER_LIVEBAR_API"] = api
    env["AETHER_LIVEBAR_DASHBOARD"] = dashboard
    env["AETHER_LIVEBAR_REPO"] = repo
    python = "/usr/bin/python3"
    os.execve(python, [python, "-m", "aether.livebar"], env)


def run(api: str, dashboard: str, repo: str = "", repo_file: Path | None = None) -> None:
    # Wayland ignores a request to sit on an edge. The X11 backend honors it.
    os.environ["GDK_BACKEND"] = "x11"
    try:
        import gi
    except ImportError:
        _reexec_system_python(api, dashboard, repo)
        return

    gi.require_version("Gtk", "3.0")
    gi.require_version("Gdk", "3.0")
    from gi.repository import Gdk, GLib, Gtk

    repo_file = repo_file or live_repo_path()
    claim_pid(livebar_pid_path())
    fallback = repo or git_root(Path.cwd())
    state = {
        "repo": read_repo_file(repo_file) or fallback,
        "reading": {"state": "empty", "repo": "", "band": "", "neighbors": [], "pressure": None, "error": ""},
    }
    stop = threading.Event()

    def poll() -> None:
        while not stop.is_set():
            current = read_repo_file(repo_file) or state["repo"]
            state["repo"] = current
            try:
                state["reading"] = fetch_live(api, current)
            except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
                state["reading"] = {
                    "state": "error",
                    "repo": Path(current).name or "repo",
                    "error": str(exc),
                    "band": "",
                    "neighbors": [],
                    "pressure": None,
                }
            stop.wait(2)

    threading.Thread(target=poll, daemon=True).start()

    window = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
    window.set_title("Aether")
    window.set_decorated(False)
    window.set_keep_above(True)
    window.set_skip_taskbar_hint(True)
    window.set_skip_pager_hint(True)
    window.stick()
    window.set_type_hint(Gdk.WindowTypeHint.DOCK)
    window.set_app_paintable(True)
    screen = window.get_screen()
    display = Gdk.Display.get_default()
    monitor = display.get_primary_monitor() if display is not None else None
    if monitor is None and display is not None and display.get_n_monitors():
        monitor = display.get_monitor(0)
    geom = monitor.get_geometry() if monitor is not None else None
    width = geom.width if geom is not None else screen.get_width()
    screen_height = geom.height if geom is not None else screen.get_height()
    origin_x = geom.x if geom is not None else 0
    origin_y = geom.y if geom is not None else 0
    height = 42
    bottom_y = origin_y + screen_height - height
    window.set_default_size(width, height)
    window.move(origin_x, bottom_y)

    css = Gtk.CssProvider()
    css.load_from_data(
        f"""
        window, box {{ background-color: {BAR_BG}; }}
        label {{ color: {BAR_FG}; font-family: monospace; font-size: 13px; }}
        label.brand {{ color: {INGEST_COLOR}; padding-left: 16px; }}
        label.quiet {{ color: {MUTED}; padding-right: 16px; }}
        button.hide {{
          background: none;
          border: none;
          box-shadow: none;
          color: {MUTED};
          padding: 0 16px;
        }}
        button.hide:hover {{ color: {BAR_FG}; }}
        """.encode()
    )
    Gtk.StyleContext.add_provider_for_screen(screen, css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
    window.add(box)
    background = Gdk.RGBA()
    background.parse(BAR_BG)
    for widget in (window, box):
        widget.override_background_color(Gtk.StateFlags.NORMAL, background)
    brand = Gtk.Label(label="Aether")
    brand.get_style_context().add_class("brand")
    detail = Gtk.Label(label="Open a repo")
    detail.set_halign(Gtk.Align.START)
    detail.set_hexpand(True)
    neighbors = Gtk.Label(label="")
    neighbors.get_style_context().add_class("quiet")
    hide = Gtk.Button(label="hide")
    hide.set_relief(Gtk.ReliefStyle.NONE)
    hide.set_can_focus(True)
    hide.get_style_context().add_class("hide")
    box.pack_start(brand, False, False, 0)
    box.pack_start(detail, True, True, 0)
    box.pack_end(hide, False, False, 0)
    box.pack_end(neighbors, False, False, 0)

    def close(*_args: object) -> None:
        stop.set()
        Gtk.main_quit()

    def open_dashboard(_widget: object, _event: object) -> bool:
        webbrowser.open(dashboard.rstrip("/") + "/radar")
        return True

    window.connect("destroy", lambda *_args: close())
    hide.connect("clicked", close)
    detail.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
    brand.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
    detail.connect("button-press-event", open_dashboard)
    brand.connect("button-press-event", open_dashboard)

    def paint() -> bool:
        reading = state["reading"]
        text = GLib.markup_escape_text(headline(reading))
        band = str(reading.get("band") or "")
        if reading.get("state") == "ingesting":
            color = INGEST_COLOR
        elif band in BAND_COLOR:
            color = BAND_COLOR[band]
        else:
            color = BAR_FG
        detail.set_markup(f'<span foreground="{color}">{text}</span>')
        if text != state.get("shown"):
            state["shown"] = text
            print(headline(reading), flush=True)
        extras = reading.get("neighbors") or []
        chunks = []
        for item in extras[:3]:
            if not isinstance(item, dict):
                continue
            pressure = item.get("pressure")
            shown = f"{pressure:.2f}" if isinstance(pressure, (int, float)) else ""
            chunks.append(f"{item.get('path') or ''} P {shown}".strip())
        neighbors.set_text("   ".join(chunks))
        window.set_keep_above(True)
        gdk_window = window.get_window()
        if gdk_window is not None:
            gdk_window.move_resize(origin_x, bottom_y, width, height)
        return True

    def place_on_bottom(_widget: Gtk.Window) -> None:
        gdk_window = window.get_window()
        if gdk_window is not None:
            gdk_window.move_resize(origin_x, bottom_y, width, height)

    window.connect("map", place_on_bottom)
    window.show_all()
    GLib.timeout_add(400, paint)
    Gtk.main()
    stop.set()
    pid_file = livebar_pid_path()
    try:
        if pid_file.is_file() and pid_file.read_text(encoding="utf-8").strip() == str(os.getpid()):
            pid_file.unlink()
    except OSError:
        pass


def main() -> None:
    run(
        os.environ.get("AETHER_LIVEBAR_API", os.environ.get("AETHER_API", "http://127.0.0.1:18100")),
        os.environ.get("AETHER_LIVEBAR_DASHBOARD", os.environ.get("AETHER_DASHBOARD", "http://127.0.0.1:13100")),
        os.environ.get("AETHER_LIVEBAR_REPO", ""),
    )


if __name__ == "__main__":
    main()
