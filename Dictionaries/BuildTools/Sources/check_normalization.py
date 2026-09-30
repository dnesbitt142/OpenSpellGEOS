#!/usr/bin/env python3
"""Check licensing-sensitive extraction boundaries and representative records.

Copyright 2026 PC/GEOS contributors. SPDX-License-Identifier: Apache-2.0

These checks validate observed public-source facts and the shared UI contract.
They intentionally reject an earlier tempting but invalid translation-derived
thesaurus: Old Testament and New Testament must never become synonym pairs.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "normalized"


def load(name):
    """Load one normalized UTF-8 JSON snapshot."""
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def synonyms(data, headword):
    """Collect direct alternatives for an audit assertion without inferring links."""
    return {word for sense in data.get(headword, []) for word in sense["synonyms"]}


def main():
    """Run representative source-boundary and binary-format contract assertions."""
    lb = load("LB.thesaurus.json")
    sv = load("SV.thesaurus.json")
    de = load("DE.thesaurus.json")
    fr = load("FR.thesaurus.json")
    assert "Alphabet" in synonyms(lb, "ABC")
    assert "adressymbol" in synonyms(sv, "adressikon")
    assert "URL-ikon" not in synonyms(sv, "adressikon")  # Source marks UPTE.
    assert "Moho" not in sv  # Its only source alternative cannot use GEOS SBCS.
    assert "Nouveau Testament" not in synonyms(fr, "Ancien Testament")
    assert "Neues Testament" not in synonyms(de, "Altes Testament")
    for data in (lb, sv, de, fr):
        for headword, senses in data.items():
            assert 0 < len(headword) <= 26
            assert 0 < len(senses) <= 16
            for sense in senses:
                assert sense["pos"] in {"unknown", "noun", "verb", "adjective", "adverb"}
                assert 0 < len(sense["synonyms"]) <= 40
                assert all(0 < len(word) <= 26 and "." not in word and "," not in word
                           for word in sense["synonyms"])
    assert load("EN_GB.hyp-exceptions.json")["manuscript"] == [2, 4]
    for language in ("EN_US", "EN_GB", "DE", "FR"):
        patterns = (ROOT / (language + ".patterns.txt")).read_text().splitlines()
        assert patterns and all("\\" not in value and "{" not in value for value in patterns)
    print("Source boundaries and normalized data contracts passed.")


if __name__ == "__main__":
    main()
