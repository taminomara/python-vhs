from __future__ import annotations

import os
import subprocess
import sys

import vhs


def _main():
    runner = vhs.resolve(reporter=vhs.DefaultProgressReporter())
    res = subprocess.run(
        ["vhs"] + sys.argv[1:],
        env={
            **os.environ,
            "PATH": runner._path,
        },
    )
    sys.exit(res.returncode)


if __name__ == "__main__":
    _main()
