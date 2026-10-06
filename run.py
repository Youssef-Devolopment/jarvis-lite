from __future__ import annotations
import sys
from logger import get_logger, setup_logging

setup_logging("INFO")
log = get_logger("run")

try:
    from config import get_settings
    from server import app
except Exception as exc:
    log.critical("Startup failed: %s", exc, exc_info=True)
    print(f"\n[!] Startup failed: {exc}\n")
    sys.exit(1)


def main():
    s = get_settings()
    import moods, memory
    print(f"\n  JARVIS Lite online  ->  http://{s.host}:{s.port}")
    print(f"  Model   : {s.model}")
    print(f"  Voice   : {s.voice_name}")
    print(f"  Mood    : {moods.current_name()}")
    print(f"  Memory  : {len(memory.all_facts())} facts on file\n")

    try:
        from memory import context as ctx_tracker
        _sid = ctx_tracker.start_session()
        import atexit
        atexit.register(lambda: ctx_tracker.end_session(_sid, "server stopped"))
    except Exception:
        pass

    # Global hotkeys: Ctrl+Alt+J opens the web UI, Alt+Space the HUD.
    # Non-blocking, degrades to a log line without keyboard/pynput.
    try:
        from system import hotkey
        hotkey.start()
    except Exception as exc:
        log.warning("Hotkeys unavailable: %s", exc)

    app.run(host=s.host, port=s.port, debug=s.debug, threaded=True)


if __name__ == "__main__":
    main()
