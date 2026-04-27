from __future__ import annotations

import signal
import subprocess
import sys
import time


SERVICE_MODULES = [
    "services.users.app",
    "services.catalog.app",
    "services.orders.app",
    "services.notifications.app",
    "services.gateway.app",
]


def main() -> int:
    processes: list[subprocess.Popen] = []
    stopping = False

    def stop(signum=None, frame=None) -> None:
        nonlocal stopping
        if stopping:
            return
        stopping = True
        for process in processes:
            process.terminate()

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    for module in SERVICE_MODULES:
        processes.append(subprocess.Popen([sys.executable, "-m", module]))
        time.sleep(0.2)

    print("API Gateway: http://127.0.0.1:8080", flush=True)
    try:
        while not stopping:
            failed = [process for process in processes if process.poll() is not None]
            if failed:
                stop()
                return failed[0].returncode or 1
            time.sleep(0.5)
    finally:
        for process in processes:
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
