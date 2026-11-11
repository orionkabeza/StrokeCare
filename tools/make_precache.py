#!/usr/bin/env python3
"""Keep the service worker's offline file list and cache version in step with frontend/site.

Owner: Orion Kabeza (DevOps) · AI-assisted draft, see AI_USE_LOG.md

The app has no build step, so this tiny script is the only "build": it lists every file the app needs to open
without a connection and gives the cache a version that changes whenever any of those files change.

    python tools/make_precache.py            rewrite the list in frontend/site/sw.js
    python tools/make_precache.py --check    exit 1 if the list or version is out of date (used by the tests and CI)
"""
import hashlib
import re
import sys
from pathlib import Path

SITE = Path(__file__).resolve().parents[1] / "frontend" / "site"
SW = SITE / "sw.js"
SKIP = {"sw.js", ".DS_Store", "index.html"}  # index.html is cached as "/" (the server redirects /index.html)
BLOCK = re.compile(r"// BEGIN PRECACHE\n.*?// END PRECACHE", re.S)


def build() -> tuple[str, list[str]]:
    files = sorted(p for p in SITE.rglob("*") if p.is_file() and p.name not in {"sw.js", ".DS_Store"})
    digest = hashlib.sha256()
    urls = []
    for path in files:
        url = "/" + path.relative_to(SITE).as_posix()
        digest.update(url.encode() + b"\0" + path.read_bytes() + b"\0")  # every file counts toward the version...
        if path.name not in SKIP:
            urls.append(url)  # ...but index.html is listed as "/" below
    return digest.hexdigest()[:12], ["/"] + urls


def block(version: str, urls: list[str]) -> str:
    items = ",\n".join(f"  '{u}'" for u in urls)
    return f"// BEGIN PRECACHE\nconst VERSION = '{version}'\nconst PRECACHE = [\n{items},\n]\n// END PRECACHE"


def main() -> int:
    version, urls = build()
    text = SW.read_text()
    fresh = BLOCK.sub(lambda _: block(version, urls), text)
    if "--check" in sys.argv:
        if fresh != text:
            print("frontend/site/sw.js is out of date. Run: python tools/make_precache.py")
            return 1
        print(f"OK: service worker lists {len(urls)} files, version {version}")
        return 0
    SW.write_text(fresh)
    print(f"Wrote {len(urls)} files, version {version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
