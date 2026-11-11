#!/usr/bin/env python3
"""Split the repository into one folder (and zip) per team member, following OWNERS.json.

Owner: Orion Kabeza (DevOps) · AI-assisted draft, see AI_USE_LOG.md

  python tools/make_handoff.py --check    every file has exactly one owner (exit 1 if not)
  python tools/make_handoff.py            writes handoff/<Name>/ and handoff/<Name>.zip

Each person unzips into the root of their own clone of the repository, reads their files, and commits them
under their own name. Folder structure is preserved, so files land in the right place.
"""
import fnmatch
import json
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", "handoff", "__pycache__", ".pytest_cache", "node_modules", ".venv", "staticfiles", "dist"}
SKIP_FILES = {".gitkeep", ".DS_Store", ".demo-credentials.txt"}


def all_files():
    for p in sorted(ROOT.rglob("*")):
        rel = p.relative_to(ROOT)
        if p.is_file() and not (SKIP_DIRS & set(rel.parts)) and p.name not in SKIP_FILES and p.suffix != ".pyc":
            yield rel.as_posix()


def matches(pattern: str, path: str) -> bool:
    if pattern.endswith("/**"):
        return path.startswith(pattern[:-2])
    return fnmatch.fnmatch(path, pattern)


def assign():
    cfg = json.loads((ROOT / "OWNERS.json").read_text(encoding="utf-8"))["owners"]
    explicit, general = [], []  # "pattern:Name" overrides the section owner, so those are tried first
    for section_owner, info in cfg.items():
        for rule in info["rules"]:
            pattern, _, override = rule.partition(":")
            (explicit if override else general).append((pattern, override or section_owner))
    rules = explicit + general
    owned, orphans = {}, []
    for path in all_files():
        owner = next((o for pat, o in rules if matches(pat, path)), None)
        (owned.setdefault(owner, []).append(path) if owner else orphans.append(path))
    return owned, orphans


def main():
    owned, orphans = assign()
    if orphans:
        print("Files with NO owner. Add them to OWNERS.json:")
        print("\n".join(f"  {p}" for p in orphans))
        return 1
    if "--check" in sys.argv:
        print(f"OK: {sum(map(len, owned.values()))} files, each with one owner.")
        return 0
    out = ROOT / "handoff"
    out.mkdir(exist_ok=True)
    for owner, files in sorted(owned.items()):
        folder = out / owner.replace(" ", "_")
        # replace only this tool's own output; anything else kept in handoff/ (notes, screenshots) stays
        shutil.rmtree(folder, ignore_errors=True)
        (out / f"{owner.replace(' ', '_')}.zip").unlink(missing_ok=True)
        for rel in files:
            dest = folder / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / rel, dest)
        with zipfile.ZipFile(out / f"{owner.replace(' ', '_')}.zip", "w", zipfile.ZIP_DEFLATED) as z:
            for rel in files:
                z.write(ROOT / rel, rel)
        print(f"{owner:34} {len(files):3} files -> handoff/{owner.replace(' ', '_')}.zip")
    return 0


if __name__ == "__main__":
    sys.exit(main())
