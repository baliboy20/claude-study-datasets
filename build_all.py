"""Build every dataset, then check the shared files.  Run from the project root:  python3 build_all.py

Runs each dataset's own build (datasets/<name>/generator/build.py) in turn, prints its version and data
checksum, then runs check_shared.py. Exits with code 1 if any build or the shared-file check fails.
Use it before publishing a release. To build one dataset, run its build from its own folder instead.
"""

import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
DATASETS = os.path.join(ROOT, "datasets")


def version(folder):
    text = open(os.path.join(folder, "generator", "release.py"), encoding="utf-8").read()
    m = re.search(r'^VERSION = "([^"]+)"', text, re.M)
    return m.group(1) if m else "?"


def main():
    failed = []
    names = sorted(d for d in os.listdir(DATASETS) if os.path.isfile(os.path.join(DATASETS, d, "generator", "build.py")))
    print(f"{'Dataset':<22} {'Version':<8} Result")
    for name in names:
        folder = os.path.join(DATASETS, name)
        run = subprocess.run([sys.executable, "-B", os.path.join("generator", "build.py")], cwd=folder,
                             capture_output=True, text=True)
        last = (run.stdout.strip().splitlines() or [""])[-1]
        m = re.search(r"sha256 (\w+)", last)
        if run.returncode == 0 and m:
            print(f"{name:<22} {version(folder):<8} passed, seed.sql checksum {m.group(1)}")
        else:
            failed.append(name)
            print(f"{name:<22} {version(folder):<8} FAILED")
            print("    " + "\n    ".join((run.stdout + run.stderr).strip().splitlines()[-15:]))
    print()
    shared = subprocess.run([sys.executable, "-B", os.path.join(ROOT, "check_shared.py")], cwd=ROOT,
                            capture_output=True, text=True)
    print((shared.stdout.strip().splitlines() or [""])[-1])
    if shared.returncode:
        print(shared.stdout)
        failed.append("shared files")
    if failed:
        print(f"\nFailed: {', '.join(failed)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
