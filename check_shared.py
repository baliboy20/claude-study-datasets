"""Check that the files every dataset shares are identical across datasets.

Run from the project root:  python3 check_shared.py
Exits with code 1 and lists the differences if any copy has drifted.

Shared files (each dataset keeps its own copy, by design):
  generator/common/*        names, UK formats, the firm, staff register, tables, page layout, theme, publishing step
  generator/build.py        the build runner
  api/src/*                 the local API and data browser
  api/tsconfig.json, api/.dev.vars.example
  docs/appraisal-types.html the agreed appraisal types; compared with the dataset's title masked
  theme.css at the project root is compared with generator/common/theme.css.
"""

import difflib
import hashlib
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
DATASETS = os.path.join(ROOT, "datasets")
# Folders whose every file is shared, plus single shared files. Anything else in a dataset is its own.
SHARED_DIRS = ["generator/common", "api/src"]
SHARED_FILES = ["generator/build.py", "api/tsconfig.json", "api/.dev.vars.example", "docs/appraisal-types.html"]


def shared_paths(names):
    paths = set(SHARED_FILES)
    for d in names:
        for folder in SHARED_DIRS:
            full = os.path.join(DATASETS, d, folder)
            if os.path.isdir(full):
                paths |= {f"{folder}/{f}" for f in os.listdir(full)
                          if os.path.isfile(os.path.join(full, f)) and not f.startswith(".") and f != "__pycache__"}
    return sorted(paths)


def dataset_title(folder):
    """The dataset's title from generator/release.py, or None if the dataset has no release yet."""
    path = os.path.join(folder, "generator", "release.py")
    if not os.path.exists(path):
        return None
    m = re.search(r'^TITLE = "([^"]+)"', open(path, encoding="utf-8").read(), re.M)
    return m.group(1) if m else None


def normalised(path, title):
    text = open(path, encoding="utf-8").read()
    if path.endswith(".html") and title:
        # Only the title as a whole element's text (crumbs and footer), so a dataset named in the body still counts.
        text = text.replace(f">{title}<", "><dataset title><")
    return text


def main():
    names = sorted(d for d in os.listdir(DATASETS) if os.path.isdir(os.path.join(DATASETS, d)))
    titles = {d: dataset_title(os.path.join(DATASETS, d)) for d in names}
    problems, notes = [], []
    for rel in shared_paths(names):
        copies = {}
        for d in names:
            path = os.path.join(DATASETS, d, rel)
            if os.path.exists(path):
                copies[d] = normalised(path, titles[d])
            else:
                notes.append(f"{d}: no {rel} yet")
        if rel.endswith("theme.css") and os.path.exists(os.path.join(ROOT, "theme.css")):
            copies["(project root)"] = open(os.path.join(ROOT, "theme.css"), encoding="utf-8").read()
        groups = {}
        for who, text in copies.items():
            groups.setdefault(hashlib.sha256(text.encode()).hexdigest(), []).append(who)
        if len(groups) <= 1:
            print(f"ok    {rel}  ({len(copies)} copies identical)")
            continue
        # Report against the version most copies share.
        ranked = sorted(groups.values(), key=len, reverse=True)
        base = ranked[0][0]
        print(f"DIFF  {rel}  ({len(groups)} different versions)")
        for group in ranked[1:]:
            who = group[0]
            diff = list(difflib.unified_diff(copies[base].splitlines(), copies[who].splitlines(),
                                             f"{base}/{rel}", f"{who}/{rel}", n=0, lineterm=""))
            problems.append((rel, base, group, diff))
            print(f"      {', '.join(group)} differs from {', '.join(ranked[0])}:")
            for line in diff[2:14]:
                print("        " + line[:150])
            if len(diff) > 14:
                print(f"        ... {len(diff) - 14} more lines")
    for n in notes:
        print(f"note  {n}")
    if problems:
        print(f"\n{len(problems)} shared file(s) have drifted. Make every copy identical, then raise its version.")
        sys.exit(1)
    print("\nAll shared files are identical across datasets.")


if __name__ == "__main__":
    main()
