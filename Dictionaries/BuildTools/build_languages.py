#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Build the compact OpenSpellGEOS six-language set from pinned local inputs.

No network access, proprietary data, or third-party Python package is used.
Each input is checked against buildset.json before writing any output. Build
into a new directory; publish/install only after the whole command succeeds.
Each DCT, THS and HYP is at most 500000 bytes (decimal), including its header,
index, leaf padding and blobs. A lower --max-bytes budget is supported.
"""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile

import buildlex
import compactlex

NOTICE_FILES = {
    "licenses/Apache-2.0.txt": "APACHE2.TXT",
    "lexicons/SCOWL-Copyright": "SCOWL.TXT",
    "lexicons/WordNet-3.1-LICENSE.txt": "WORDNET.TXT",
    "lexicons/Moby-Public-Domain.txt": "MOBY.TXT",
    "lexicons/German-Public-Domain.txt": "GERMAN.TXT",
    "lexicons/NST-CC0-NOTICE.txt": "NST.TXT",
    "licenses/CC0-1.0.txt": "CC0.TXT",
    "licenses/hyph-de-1996.txt": "HYPDE.TXT",
    "licenses/hyph-en-gb.txt": "HYPENGB.TXT",
    "licenses/hyph-en-us.txt": "HYPENUS.TXT",
    "licenses/hyph-fr.txt": "HYPFR.TXT",
}


def digest(path):
    """Hash an input incrementally, without duplicating a large word list in RAM."""
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(65536), b""):
            result.update(block)
    return result.hexdigest()


def checked_input(data, name, checksums):
    """Resolve a manifest-relative file and reject path escapes or changed bytes."""
    if not isinstance(name, str) or Path(name).is_absolute():
        raise ValueError("input name must be a relative path")
    path = (data / name).resolve()
    if data not in path.parents or name not in checksums:
        raise ValueError("unlisted input or path outside data directory: " + name)
    if digest(path) != checksums[name]:
        raise ValueError("input checksum mismatch: " + name)
    return path


def write_gdi(profile, path):
    """Write one legacy Preferences record with CRLF and Latin-1 text."""
    lines = [profile["stem"] + ".DCT", profile["display_name"],
             profile["description"], str(profile["language_id"]),
             str(profile["dialect_id"])]
    if len(lines[1]) > 64 or len(lines[2]) > 256:
        raise ValueError("GDI text exceeds Preferences capacity")
    if any("\r" in line or "\n" in line for line in lines):
        raise ValueError("GDI fields must be single lines")
    path.write_bytes(("\r\n".join(lines) + "\r\n").encode("latin-1"))


def copy_notices(stage):
    """Keep full upstream grants and provenance with a standalone data set.

    These notices are required redistribution material, not runtime input.
    Short destination names also allow copying the whole directory to DOS.
    Resolve them beside this script so --data does not silently substitute
    or omit the attribution bundled with the six-profile build recipe.
    """
    sources = Path(__file__).resolve().parent / "Sources"
    licenses = stage / "LICENSES"
    licenses.mkdir()
    for original, destination in sorted(NOTICE_FILES.items()):
        shutil.copyfile(sources / original, licenses / destination)
    introduction = (
        "OpenSpellGEOS linguistic data: redistribution notices\n"
        "\nThe generated files retain their source licenses. They are not all\n"
        "relicensed as Apache-2.0. Keep this file and LICENSES with copies.\n"
        "The engine and conversion tools are separately Apache-2.0 licensed.\n"
        "\nFull-notice mapping (source path -> DOS-compatible destination):\n"
    )
    mapping = "".join("  " + source + " -> LICENSES/" + destination + "\n"
                      for source, destination in sorted(NOTICE_FILES.items()))
    # Preserve the complete provenance text, including upstream URLs and
    # conversion limits, even when only DICTS is redistributed.
    provenance = "\n\n".join((sources / name).read_text(encoding="utf-8")
                              for name in ("SOURCES.md", "LEXICON-SOURCES.md"))
    (stage / "NOTICES.TXT").write_text(introduction + mapping + "\n" + provenance,
                                      encoding="utf-8")
    paths = [stage / "NOTICES.TXT"] + sorted(licenses.iterdir())
    return {path.relative_to(stage).as_posix(): digest(path) for path in paths}


def write_budgeted(kind, stem, entries, priority, max_bytes, stage):
    """Select and write one bounded file; refuse publication if the estimate drifts."""
    selected, selection = compactlex.select_entries(entries, priority, max_bytes)
    extension = {1: ".DCT", 2: ".THS", 3: ".HYP"}[kind]
    metadata = buildlex.build_file(kind, stem, selected, stage / (stem + extension),
                                   max_bytes=max_bytes)
    if metadata["bytes"] != selection["estimated_bytes"]:
        raise ValueError("OLX1 size estimate differs from writer: " + metadata["file"])
    if metadata["bytes"] > max_bytes or metadata["bytes"] > compactlex.MAX_FILE_BYTES:
        raise ValueError("hard file-size ceiling exceeded: " + metadata["file"])
    metadata["selection"] = selection
    return selected, metadata


def build_set(data, output, max_bytes=compactlex.MAX_FILE_BYTES):
    """Verify pinned sources and publish a complete bounded set atomically.

    A single shared ranking controls spelling, synonym order and hyphenation.
    The selected spelling vocabulary also bounds hyphenation preprocessing.
    Source word lists remain intact; every omission and compact-data policy is
    recorded in BUILD.json. No partially built directory becomes the output.
    """
    compactlex.check_budget(max_bytes)
    data = data.resolve()
    output = output.resolve()
    spec = json.loads((data / "buildset.json").read_text(encoding="utf-8"))
    if spec.get("version") != 1 or len(spec.get("profiles", [])) != 6:
        raise ValueError("expected the version 1 six-language build manifest")
    if output.exists():
        raise ValueError("output already exists; choose a new directory")
    inputs = {name: checked_input(data, name, spec["sha256"])
              for name in spec["sha256"]}
    output.parent.mkdir(parents=True, exist_ok=True)
    report = {"project": "OpenSpellGEOS", "format": "OLX1",
              "max_file_bytes": max_bytes, "inputs": spec["sha256"], "profiles": []}
    with tempfile.TemporaryDirectory(prefix="openspellgeos-build-", dir=output.parent) as work:
        stage = Path(work) / "DICTS"
        stage.mkdir()
        report["notices"] = copy_notices(stage)
        for profile in spec["profiles"]:
            stem = profile["stem"]
            if stem not in ("EN_US", "EN_GB", "DE_DE", "SV_SE", "LB_LU", "FR_FR"):
                raise ValueError("unexpected profile stem")
            words = inputs[profile["words"]]
            priority_name = profile.get("priority")
            priority_path = inputs[priority_name] if priority_name else None
            ranking = {"file": priority_name,
                       "kind": profile.get("priority_kind", "deterministic-heuristic"),
                       "source": profile.get("priority_source", "No source priority list supplied"),
                       "sha256": spec["sha256"].get(priority_name)}
            priority = compactlex.Priority(priority_path, ranking)
            result = {"stem": stem, "coverage": profile["coverage"],
                      "ranking": priority.metadata, "files": []}
            all_words = buildlex.read_words(words)
            primary_forms = len(all_words)
            supplement_name = profile.get("word_supplement")
            supplement = buildlex.read_words(inputs[supplement_name]) if supplement_name else {}
            added_forms = sum(key not in all_words for key in supplement)
            all_words.update(supplement)
            dictionary, metadata = write_budgeted(1, stem, all_words, priority, max_bytes, stage)
            metadata["vocabulary"] = {
                "primary_file": profile["words"], "primary_forms": primary_forms,
                "supplement_file": supplement_name, "supplement_forms": len(supplement),
                "supplement_added_forms": added_forms, "candidate_forms": len(all_words),
            }
            result["files"].append(metadata)
            del supplement
            del all_words

            entries, compaction = compactlex.compact_thesaurus(inputs[profile["thesaurus"]], priority)
            thesaurus, metadata = write_budgeted(2, stem, entries, priority, max_bytes, stage)
            compaction["selected_senses"] = sum(len(compactlex.decode_senses(value))
                                                for value in thesaurus.values())
            compaction["selected_synonyms"] = sum(len(sense[2]) for value in thesaurus.values()
                                                  for sense in compactlex.decode_senses(value))
            metadata["compaction"] = compaction
            result["files"].append(metadata)
            del entries, thesaurus

            patterns = inputs[profile["patterns"]] if profile.get("patterns") else None
            exceptions = inputs[profile["exceptions"]] if profile.get("exceptions") else None
            if profile["coverage"]["hyphenation"] == "unavailable":
                entries = {}
                print(stem + ": no verified hyphenation source; writing empty no-break file", file=sys.stderr)
            else:
                entries = compactlex.hyphenation_entries(dictionary, patterns, exceptions,
                                                         profile["left_min"], profile["right_min"])
            hyphenation, metadata = write_budgeted(3, stem, entries, priority, max_bytes, stage)
            metadata["vocabulary"] = {
                "policy": "subset of folded selected DCT; nonempty break lists only",
                "selected_dictionary_forms": len(dictionary),
                "selected_dictionary_folded_forms": len({word.translate(buildlex.LOWER_TABLE)
                                                          for word in dictionary}),
                "candidate_words_with_breaks": len(entries),
                "selected_words_with_breaks": len(hyphenation),
            }
            result["files"].append(metadata)
            del entries, hyphenation, dictionary
            write_gdi(profile, stage / (stem + ".GDI"))
            report["profiles"].append(result)
            print(stem + ": " + ", ".join(str(item["entries"]) + " entries / " +
                                           str(item["bytes"]) + " bytes in " + item["file"]
                                           for item in result["files"]))
        (stage / "BUILD.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        # Staging is a sibling of output on the same filesystem. Rename exposes
        # the whole completed set in one operation, after every ceiling check.
        stage.rename(output)
    return report


def main():
    """Report actionable errors and leave an existing data set untouched."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path(__file__).parent / "Data")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-bytes", type=int, default=compactlex.MAX_FILE_BYTES,
                        help="hard decimal-byte ceiling per DCT/THS/HYP (64..500000)")
    args = parser.parse_args()
    try:
        build_set(args.data, args.output, args.max_bytes)
    except (OSError, KeyError, TypeError, ValueError) as error:
        parser.exit(2, "build_languages: %s\n" % error)
    return 0


if __name__ == "__main__":
    sys.exit(main())
