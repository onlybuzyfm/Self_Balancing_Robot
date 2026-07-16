#!/usr/bin/env python3
import subprocess


def main() -> None:
    cmd = [
        "gz",
        "service",
        "-s",
        "/world/tumbller_lab/control",
        "--reqtype",
        "gz.msgs.WorldControl",
        "--reptype",
        "gz.msgs.Boolean",
        "--timeout",
        "2000",
        "--req",
        "reset: {all: true}",
    ]
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()