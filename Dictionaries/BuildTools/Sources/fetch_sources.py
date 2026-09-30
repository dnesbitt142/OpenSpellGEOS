#!/usr/bin/env python3
"""Fetch the pinned CC0 LOD/terminology and permissive hyphenation inputs.

Copyright 2026 PC/GEOS contributors. SPDX-License-Identifier: Apache-2.0

The adjacent JSON manifests record exact input hashes. Downloads are written
only after a successful hash check. Existing matching files are reused. English,
German, French and Swedish wordlist acquisition is provided separately by
fetch_lexicons.py because the German upstream archive needs a 7z extractor.
"""

import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parent
MANIFESTS = ("sources-hyphen-lod.json", "sources-rikstermbanken.json")


def digest(data):
    """Return the SHA-256 fingerprint used by the source lock manifests."""
    return hashlib.sha256(data).hexdigest()


def fetch(record):
    """Reuse or acquire one exact licensed source without trusting remote names."""
    destination = (ROOT / record["path"]).resolve()
    if ROOT not in destination.parents:
        raise ValueError("Manifest path escapes source directory")
    if destination.exists() and digest(destination.read_bytes()) == record["sha256"]:
        print("verified " + record["path"])
        return
    if not record["url"].startswith("https://"):
        raise ValueError("Source URL must use HTTPS")
    with urllib.request.urlopen(record["url"], timeout=90) as response:
        data = response.read()
    if digest(data) != record["sha256"]:
        raise ValueError("Source changed: " + record["url"])
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".download")
    temporary.write_bytes(data)
    temporary.replace(destination)
    print("fetched " + record["path"])


def main():
    """Verify both source manifests and acquire their exact source bytes."""
    for name in MANIFESTS:
        records = json.loads((ROOT / name).read_text(encoding="utf-8"))
        for record in records:
            # Web-page evidence is captured for review and changes frequently.
            # It is not a normalizer input; preserve the supplied snapshot.
            if record["path"].endswith(".html"):
                continue
            fetch(record)


if __name__ == "__main__":
    main()
