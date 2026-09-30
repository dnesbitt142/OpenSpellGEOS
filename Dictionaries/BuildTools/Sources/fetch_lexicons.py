#!/usr/bin/env python3
"""Fetch the exact permissive lexicon inputs recorded in lexicon-provenance.json.

Copyright 2026. Licensed under the Apache License, Version 2.0.
The downloaded databases retain the separate licenses recorded in the manifest.

Run with host Python 3. Existing files must match SHA-256; changed or incomplete
upstream files fail closed. Downloads use a sibling temporary file and atomic
replacement. German extraction requires 7z, 7zz or bsdtar; alternatively extract
exactly german.dic from german.7z manually before normalize_lexicons.py.
"""

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import urllib.request

ROOT = Path(__file__).resolve().parent
RAW = ROOT / 'lexicons'


def checksum(path):
    """Hash a local file in bounded chunks without retaining its contents."""
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def fetch(entry):
    """Download and verify one manifest entry, preserving any valid local copy."""
    target = RAW / entry['file']
    expected = entry['sha256']
    if target.exists() and checksum(target) == expected:
        print('verified', target.name, flush=True)
        return
    temporary = target.with_name(target.name + '.part')
    try:
        with urllib.request.urlopen(entry['url'], timeout=120) as response:
            with temporary.open('wb') as output:
                shutil.copyfileobj(response, output, 1024 * 1024)
        if checksum(temporary) != expected:
            raise ValueError('Upstream content changed for ' + target.name)
        temporary.replace(target)
        print('downloaded', target.name, flush=True)
    finally:
        if temporary.exists():
            temporary.unlink()


def extract_german(expected):
    """Extract only the selected German word list; do not include variants.dic."""
    target = RAW / 'german.dic'
    if target.exists() and checksum(target) == expected:
        return
    command = None
    for executable in ['7z', '7zz']:
        found = shutil.which(executable)
        if found:
            command = [found, 'x', '-so', str(RAW / 'german.7z'), 'german.dic']
            break
    if command is None:
        found = shutil.which('bsdtar')
        if found:
            command = [found, '-xOf', str(RAW / 'german.7z'), 'german.dic']
    if command is None:
        raise RuntimeError('Install 7-Zip or bsdtar, or extract german.dic manually.')
    temporary = target.with_name('german.dic.part')
    try:
        with temporary.open('wb') as output:
            subprocess.run(command, stdout=output, check=True)
        if checksum(temporary) != expected:
            raise ValueError('Extracted german.dic SHA-256 mismatch')
        temporary.replace(target)
    finally:
        if temporary.exists():
            temporary.unlink()


def main():
    """Fetch exact source snapshots, then verify the selected archive member."""
    manifest = json.loads((ROOT / 'lexicon-provenance.json').read_text('utf-8'))
    RAW.mkdir(parents=True, exist_ok=True)
    for entry in manifest['downloads']:
        fetch(entry)
    extract_german(manifest['german_extracted_sha256'])


if __name__ == '__main__':
    main()
