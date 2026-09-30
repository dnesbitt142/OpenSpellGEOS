#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Check OpenSpellGEOS priority selection, exact ceilings and atomic publication.

This stdlib-only host check exercises actual files and source transformations.
It covers tiny and normal budgets, priority over short-word heuristics, case
aliases, inline and deduplicated blob sizing, compact thesaurus semantics,
selected-vocabulary hyphenation and a failure after staging has begun.
"""

import contextlib
import hashlib
import io
import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile

import build_languages
import buildlex
import compactlex


def require(condition, message):
    """Keep checks active even if Python is invoked with optimization enabled."""
    if not condition:
        raise AssertionError(message)


def must_fail(function):
    """Require a meaningful validation error for the requested invalid operation."""
    try:
        function()
    except ValueError:
        return
    raise AssertionError("invalid operation unexpectedly succeeded")


def check_priority(directory):
    """Show that explicit common-word priorities outrank length and case aliases."""
    path = directory / "priority.txt"
    path.write_text("# ordered source priorities\nDictionary\ndictionary\n\u00e9cole\n", encoding="utf-8")
    priority = compactlex.Priority(path, {"kind": "test-curated"})
    require(len(priority.ranks) == 2, "fold aliases must share the first rank")
    require(priority.key(b"dictionary") < priority.key(b"a"), "priority must outrank short words")
    require(priority.key(b"dictionary") < priority.key(b"Dictionary"), "lowercase tie-break")
    require(priority.contains(buildlex.encode_geos("\u00c9cole")), "accented case alias")
    require(priority.key(b"abc") < priority.key(b"a-b"), "plain words precede punctuation")
    require(priority.key(b"a") < priority.key(b"abcd"), "fallback length order")
    path.write_text("\U0001f600\n", encoding="utf-8")
    must_fail(lambda: compactlex.Priority(path))
    for limit in (63, 500001, -1, True, 100.0):
        must_fail(lambda limit=limit: compactlex.check_budget(limit))
    compactlex.check_budget(64)
    compactlex.check_budget(500000)


def check_sizes(directory):
    """Compare byte predictions and budget decisions with actual complete files."""
    randomizer = random.Random(500000)
    priority = compactlex.Priority()
    for attempt in range(40):
        entries = {}
        for number in range(randomizer.randrange(1, 700)):
            key = ("prefix%04d" % number).encode() + b"x" * randomizer.randrange(0, 24)
            length = randomizer.choice((1, 3, 95, 96, 97, 120, 4096))
            # Shared large values deliberately exercise blob deduplication.
            entries[key] = bytes([65 + number % 3]) * length
        path = directory / "sizing.THS"
        metadata = buildlex.build_file(2, "EN_GB", entries, path)
        require(compactlex.estimate_size(entries) == len(path.read_bytes()) == metadata["bytes"],
                "exact size prediction diverged at inline/blob/page boundary")
        limit = randomizer.randrange(64, min(500000, metadata["bytes"] + 1000) + 1)
        selected, report = compactlex.select_entries(entries, priority, limit)
        metadata = buildlex.build_file(2, "EN_GB", selected, path)
        require(metadata["bytes"] <= limit and metadata["bytes"] == report["estimated_bytes"],
                "selected output exceeds inclusive budget")
        expected_prefix = sorted(entries, key=priority.key)[:len(selected)]
        require(set(selected) == set(expected_prefix), "selection lost a higher priority candidate")
        reversed_entries = dict(reversed(list(entries.items())))
        repeated, repeated_report = compactlex.select_entries(reversed_entries, priority, limit)
        require(selected == repeated and report == repeated_report, "input order changed deterministic selection")
    entries = {b"word": b"\x01"}
    empty, report = compactlex.select_entries(entries, priority, 64)
    require(empty == {} and report["estimated_bytes"] == 64, "empty budget boundary")
    chosen, report = compactlex.select_entries(entries, priority, 1153)
    require(chosen == entries and report["estimated_bytes"] == 1153, "single-leaf inclusive boundary")
    large = {("word%06d" % number).encode(): b"\x01" for number in range(150000)}
    selected, report = compactlex.select_entries(large, priority)
    buildlex.build_file(1, "EN_GB", selected, directory / "ceiling.DCT")
    require((directory / "ceiling.DCT").stat().st_size <= 500000,
            "large dictionary breached default hard ceiling")
    require(report["omitted_records"] > 0 and report["ranking_considered"] < len(large),
            "large-source selection did not apply bounded candidate heap")


def check_writer_gate(directory):
    """Enforce the public writer/CLI ceiling without damaging an existing file."""
    output = directory / "preserved.DCT"
    sentinel = b"previous output must survive a rejected replacement"
    output.write_bytes(sentinel)
    must_fail(lambda: buildlex.build_file(1, "EN_GB", {b"word": b"\x01"},
                                          output, max_bytes=1152))
    require(output.read_bytes() == sentinel, "oversized writer destroyed prior output")
    words = directory / "cli-words.txt"
    words.write_text("word\n", encoding="utf-8")
    command = [sys.executable, str(Path(__file__).parent / "buildlex.py"),
               "dictionary", str(words), str(directory / "rejected.DCT"),
               "--language", "EN_GB", "--max-bytes", "500001"]
    rejected = subprocess.run(command, capture_output=True, text=True, check=False)
    require(rejected.returncode != 0 and "64..500000" in rejected.stderr,
            "standalone CLI accepted a ceiling above 500000")
    require(not (directory / "rejected.DCT").exists(), "rejected CLI created output")
    command[4] = str(directory / "accepted.DCT")
    command[-1] = "1153"
    accepted = subprocess.run(command, capture_output=True, text=True, check=False)
    require(accepted.returncode == 0 and (directory / "accepted.DCT").stat().st_size == 1153,
            "standalone CLI failed a valid inclusive small budget")


def check_thesaurus(directory):
    """Preserve source semantics while enforcing 2 senses, 4 synonyms and 48 bytes."""
    ranking = directory / "rank.txt"
    ranking.write_text("fast\nquick\nswift\nbrisk\nspeedy\nsprint\n", encoding="utf-8")
    priority = compactlex.Priority(ranking)
    source = {
        "rapid": [
            {"pos": "noun", "label": "A burst of movement", "synonyms": ["sprint"]},
            {"pos": "adjective", "label": "A" * 70,
             "synonyms": ["rapid", "Fast", "fast", "quick", "swift", "speedy", "brisk"]},
            {"pos": "adjective", "label": "Another kind of rapid movement", "synonyms": ["quick"]},
        ],
        "term": [{"pos": "unknown", "label": "An explicitly supplied but otherwise unspecified related term in the source", 
                  "synonyms": ["expression"]}],
    }
    path = directory / "synonyms.json"
    path.write_text(json.dumps(source), encoding="utf-8")
    entries, report = compactlex.compact_thesaurus(path, priority)
    senses = compactlex.decode_senses(entries[b"rapid"])
    require(len(senses) == 2 and [sense[0] for sense in senses] == [0, 1],
            "best-synonym ranking or different-known-POS preference failed")
    require(senses[0][1] == b"fast", "overlong first token must use an original synonym")
    require(senses[0][2] == [b"fast", b"quick", b"swift", b"brisk"],
            "synonym priority, self removal or folded deduplication failed")
    original_terms = {buildlex.encode_geos(item) for value in source.values()
                      for sense in value for item in sense["synonyms"]}
    for value in entries.values():
        for pos, label, synonyms in compactlex.decode_senses(value):
            require(len(label) <= 48 and len(synonyms) <= 4,
                    "compact thesaurus field limit exceeded")
            require(all(term in original_terms for term in synonyms), "a synonym was invented")
    require(compactlex.decode_senses(entries[b"term"])[0][0] == 255, "unknown POS was falsified")
    require(report["candidate_labels_shortened"] == 2, "label reductions not reported")
    require(compactlex.short_label(b"first second " + b"x" * 60, b"fallback") == b"first second\xc9",
            "label cut through a word")


def check_hyphenation(directory):
    """Ensure exceptions cannot add rejected words or retain redundant empty rows."""
    patterns = directory / "patterns.txt"
    patterns.write_text("ab1c\n", encoding="utf-8")
    exceptions = directory / "exceptions.json"
    exceptions.write_text('{"abcdef": [3], "outsider": [3], "project": []}', encoding="utf-8")
    dictionary = {b"Abcdef": b"\x02", b"abcdef": b"\x01", b"project": b"\x01"}
    entries = compactlex.hyphenation_entries(dictionary, patterns, exceptions)
    require(entries == {b"abcdef": b"\x03"}, "HYP subset/override/no-break filtering failed")
    must_fail(lambda: compactlex.hyphenation_entries(dictionary, left_min=0))


def check_publication(directory):
    """Prove a completed set is bounded and a later source failure publishes nothing."""
    data = directory / "Data"
    data.mkdir()
    (data / "words.txt").write_text("alpha\nbeta\n", encoding="utf-8")
    (data / "priority.txt").write_text("beta\nalpha\n", encoding="utf-8")
    (data / "synonyms.json").write_text(json.dumps({"alpha": [
        {"pos": "unknown", "label": "Related label", "synonyms": ["beta"]}]}), encoding="utf-8")
    (data / "bad.txt").write_text("\U0001f600\n", encoding="utf-8")
    (data / "supplement.txt").write_text("gamma\nalpha\n", encoding="utf-8")
    spec = {"version": 1, "profiles": [], "sha256": {}}
    for path in data.iterdir():
        spec["sha256"][path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    for stem in ("EN_US", "EN_GB", "DE_DE", "SV_SE", "LB_LU", "FR_FR"):
        spec["profiles"].append({"stem": stem, "words": "words.txt", "thesaurus": "synonyms.json",
                                 "priority": "priority.txt", "priority_kind": "test-curated",
                                 "priority_source": "Synthetic test data", "patterns": None,
                                 "exceptions": None, "left_min": 2, "right_min": 2,
                                 "coverage": {"hyphenation": "unavailable", "thesaurus": "test"},
                                 "display_name": stem, "description": "Test profile",
                                 "language_id": 0, "dialect_id": 0})
    spec["profiles"][3]["word_supplement"] = "supplement.txt"
    manifest = data / "buildset.json"
    manifest.write_text(json.dumps(spec), encoding="utf-8")
    output = directory / "complete"
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        report = build_languages.build_set(data, output, 64)
    require(report["project"] == "OpenSpellGEOS" and report["max_file_bytes"] == 64,
            "project/ceiling missing from report")
    for profile in report["profiles"]:
        for metadata in profile["files"]:
            require((output / metadata["file"]).stat().st_size == 64,
                    "tiny budget not enforced for every file")
            require(metadata["selection"]["selected_records"] == 0,
                    "empty file lacks consistent selection report")
    vocabulary = report["profiles"][3]["files"][0]["vocabulary"]
    require(vocabulary["primary_forms"] == 2 and vocabulary["supplement_forms"] == 2 and
            vocabulary["supplement_added_forms"] == 1 and vocabulary["candidate_forms"] == 3,
            "reviewed supplement union/count metadata is incorrect")
    before = (output / "BUILD.json").read_bytes()
    must_fail(lambda: build_languages.build_set(data, output))
    require((output / "BUILD.json").read_bytes() == before, "existing output was modified")
    spec["profiles"][2]["words"] = "bad.txt"
    manifest.write_text(json.dumps(spec), encoding="utf-8")
    failed = directory / "failed"
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        must_fail(lambda: build_languages.build_set(data, failed))
    require(not failed.exists(), "mid-build failure exposed a partial output directory")
    require(not list(directory.glob("openspellgeos-build-*")), "failed staging directory leaked")


def main():
    """Run bounded-data checks in a temporary directory and report one result."""
    with tempfile.TemporaryDirectory(prefix="openspellgeos-compact-check-") as temporary:
        directory = Path(temporary)
        check_priority(directory)
        check_sizes(directory)
        check_writer_gate(directory)
        check_thesaurus(directory)
        check_hyphenation(directory)
        check_publication(directory)
    print("PASS: OpenSpellGEOS priority, exact 500000-byte ceiling, THS/HYP compaction and atomic publication")


if __name__ == "__main__":
    main()
