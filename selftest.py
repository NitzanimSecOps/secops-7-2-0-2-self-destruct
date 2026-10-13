#!/usr/bin/env python3
"""Self-check for service.py. Run:  python3 selftest.py"""
import os
import signal
import subprocess
import sys
import tempfile
import time
from datetime import date
from pathlib import Path

SERVICE = Path(__file__).resolve().parent / "service.py"
LAUNCH_TIMEOUT = 5
EXIT_TIMEOUT = 8


def _wait(pred, timeout, interval=0.1):
    end = time.time() + timeout
    while time.time() < end:
        if pred():
            return True
        time.sleep(interval)
    return pred()


def _start(wd):
    return subprocess.Popen([sys.executable, str(SERVICE)], cwd=wd,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            start_new_session=True)


def _kill(p):
    try:
        os.killpg(os.getpgid(p.pid), signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass


def _report(name, ok):
    print(("PASS" if ok else "FAIL"), name)
    return ok


def main():
    results = []
    with tempfile.TemporaryDirectory() as wd:
        wd = Path(wd)
        lock, log = wd / "service.lock", wd / "service.log"
        p = _start(str(wd))
        try:
            results.append(_report("creates service.lock on startup",
                                   _wait(lambda: lock.exists(), LAUNCH_TIMEOUT)))
            time.sleep(1)
            results.append(_report("keeps running until signalled", p.poll() is None))
            p.terminate()
            exited = _wait(lambda: p.poll() is not None, EXIT_TIMEOUT)
            text = log.read_text() if log.exists() else ""
            results.append(_report(
                "SIGTERM: graceful (log line + date, lock removed, exit 0)",
                exited and not lock.exists() and "shutdown complete" in text
                and str(date.today().year) in text and p.returncode == 0))
        finally:
            _kill(p)

    with tempfile.TemporaryDirectory() as wd:
        wd = Path(wd)
        lock, log = wd / "service.lock", wd / "service.log"
        p = _start(str(wd))
        try:
            _wait(lambda: lock.exists(), LAUNCH_TIMEOUT)
            p.kill()
            _wait(lambda: p.poll() is not None, EXIT_TIMEOUT)
            text = log.read_text() if log.exists() else ""
            results.append(_report(
                "SIGKILL: no cleanup (lock stays, no 'shutdown complete')",
                lock.exists() and "shutdown complete" not in text))
        finally:
            _kill(p)

    print(f"\n{sum(results)}/{len(results)} checks passed.")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
