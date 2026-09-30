#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Audit an OpenSpellGEOS compact release and query real samples in the C core.

This release check is separate from the synthetic unit/regression checks. It
walks every on-disk record with an independent structural decoder, validates
all payload schemas, compact size bounds and whole-file hashes, then uses the
compiled C89 reader for real accent, spelling-case, synonym and hyphenation
samples. It requires Python 3, a C compiler and a completed build_languages.py output directory.
"""

import argparse
import hashlib
import json
from pathlib import Path
import struct
import tempfile

import buildlex
import compactlex
import selfcheck

MAX_FILE_BYTES = 500000
MAX_THS_SENSES = 2
MAX_THS_SYNONYMS = 4
MAX_THS_LABEL_BYTES = 48

SAMPLES = {
    "EN_US": ["color", "hello", "dictionary"],
    "EN_GB": ["colour", "hello", "dictionary"],
    "DE_DE": ["Haus", "H\u00e4user", "Stra\u00dfe", "W\u00f6rterbuch"],
    "SV_SE": ["hus", "m\u00f6jlighet", "spr\u00e5k", "det", "i", "som",
              "p\u00e5", "den", "av", "de"],
    "LB_LU": ["Haus", "L\u00ebtzebuerg", "Wuert"],
    "FR_FR": ["maison", "fran\u00e7ais", "\u00e9cole"],
}
# The Swedish source is specialist terminology. Its retained physical-work
# sense of arbete replaces the omitted rigging term A-bock in the compact set;
# hus is not a source thesaurus headword and must not be invented as a sample.
THESAURUS_SAMPLES = {"EN_US": "rapid", "EN_GB": "rapid", "DE_DE": "Haus",
                     "SV_SE": "arbete", "LB_LU": "schnell", "FR_FR": "maison"}


def require(condition, description):
    """Raise an actionable validation failure, independent of Python -O mode."""
    if not condition:
        raise ValueError(description)


def pinned_input(source_directory, specification, report, name):
    """Check one deterministic rebuild input against both pinned manifests."""
    require(isinstance(name, str) and not Path(name).is_absolute(),
            "invalid rebuild input name")
    root = source_directory.resolve()
    path = (root / name).resolve()
    require(root in path.parents and name in specification["sha256"],
            "rebuild input escapes sources or is not pinned: " + name)
    expected = specification["sha256"][name]
    require(report["inputs"].get(name) == expected,
            "BUILD.json input hash disagrees with pinned manifest: " + name)
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(65536), b""):
            digest.update(block)
    require(digest.hexdigest() == expected, "rebuild input hash mismatch: " + name)
    return path


def printable(value):
    """Check that a GEOS text field has no control, DEL or NUL bytes."""
    return bool(value) and all(byte >= 32 and byte != 127 for byte in value)


def decode_thesaurus(payload):
    """Independently parse a THS value and enforce the compact release limits."""
    require(bool(payload) and 1 <= payload[0] <= MAX_THS_SENSES, "bad THS sense count")
    position = 1
    labels_total = 1
    senses = []
    for _ in range(payload[0]):
        require(position + 2 <= len(payload), "truncated THS sense header")
        pos, label_length = payload[position:position + 2]
        position += 2
        require(pos in (0, 1, 2, 3, 255), "invalid THS part of speech")
        require(1 <= label_length <= MAX_THS_LABEL_BYTES and position + label_length < len(payload),
                "truncated/overlength THS label")
        label = payload[position:position + label_length]
        require(printable(label), "THS label contains controls")
        position += label_length
        synonym_count = payload[position]
        position += 1
        require(1 <= synonym_count <= MAX_THS_SYNONYMS, "invalid THS synonym count")
        synonyms = []
        synonym_bytes = 0
        for _ in range(synonym_count):
            require(position < len(payload), "truncated THS synonym length")
            length = payload[position]
            position += 1
            require(1 <= length <= 26 and position + length <= len(payload),
                    "truncated/overlength THS synonym")
            synonym = payload[position:position + length]
            require(printable(synonym) and b"." not in synonym and b"," not in synonym,
                    "THS synonym contains UI delimiters or controls")
            synonyms.append(synonym)
            synonym_bytes += length + 1
            position += length
        require(synonym_bytes < 1600, "THS synonym display overflow")
        labels_total += label_length + 8
        senses.append((pos, label, synonyms))
    require(position == len(payload), "trailing bytes in THS value")
    require(labels_total < 1600, "THS meaning display overflow")
    return senses


def inspect_file(path, metadata):
    """Walk all records, including unqueried leaves and every referenced blob.

    The scan checks global key ordering, index correspondence, value schemas,
    exact counts, zero padding, and a gap-free, nonoverlapping blob arena.
    Selected records are retained for independent native C lookup checks.
    """
    content = path.read_bytes()
    require(64 <= len(content) <= MAX_FILE_BYTES,
            "linguistic file exceeds the 500000-byte release bound: " + path.name)
    require(hashlib.sha256(content).hexdigest() == metadata["sha256"],
            "SHA-256 differs from BUILD.json: " + path.name)
    require(len(content) >= 64, "short header")
    header = struct.unpack_from("<4sBBBBHHIIIIII", content)
    magic, kind, encoding, key_max, flags, header_size, block_size = header[:7]
    count, blocks, index_offset, data_offset, blob_offset, file_size = header[7:]
    require((magic, encoding, key_max, flags, header_size, block_size) ==
            (b"OLX1", 1, 64, 0, 64, 1024), "invalid header constants")
    require(kind == metadata["kind"] and count == metadata["entries"] and
            blocks == metadata["blocks"] and file_size == metadata["bytes"],
            "header and build report disagree")
    require(index_offset == 64 and data_offset == 64 + blocks * 65 and
            blob_offset == data_offset + blocks * 1024 and
            blob_offset <= file_size == len(content) <= 0x7FFFFFFF,
            "invalid region offsets")
    require(content[36:44].rstrip(b"\0").decode("ascii") == path.stem,
            "header language differs from filename")
    require(not any(content[44:64]), "nonzero header reserved bytes")
    wanted = {buildlex.encode_geos(word) for word in SAMPLES[path.stem]}
    if kind == 2:
        wanted = {buildlex.encode_geos(THESAURUS_SAMPLES[path.stem]).translate(buildlex.LOWER_TABLE)}
    if kind == 3:
        wanted = {buildlex.encode_geos(word).translate(buildlex.LOWER_TABLE)
                  for word in ("associate", "project", "hyphenation", "dictionary")}
    samples = {}
    keys = set()
    seen = 0
    previous_global = b""
    previous_index = b""
    blobs = {}
    for block in range(blocks):
        index_record = content[64 + 65 * block:64 + 65 * (block + 1)]
        index_length = index_record[0]
        require(1 <= index_length <= 64 and not any(index_record[index_length + 1:]),
                "invalid sparse index length/padding")
        first_key = index_record[1:1 + index_length]
        require(printable(first_key) and first_key > previous_index,
                "unsorted or nonprintable sparse index")
        previous_index = first_key
        leaf = content[data_offset + 1024 * block:data_offset + 1024 * (block + 1)]
        used, records = struct.unpack_from("<HH", leaf)
        require(9 <= used <= 1024 and 1 <= records <= 204,
                "invalid leaf used/count fields")
        position = 4
        previous = b""
        for record in range(records):
            require(position + 4 <= used, "truncated record header")
            prefix, suffix, length = struct.unpack_from("<BBH", leaf, position)
            position += 4
            require(prefix <= len(previous) and suffix > 0 and prefix + suffix <= 64 and
                    position + suffix <= used and length <= 4096,
                    "invalid prefix/suffix/value length")
            key = previous[:prefix] + leaf[position:position + suffix]
            position += suffix
            require(printable(key) and key > previous_global, "unsorted/invalid key")
            require(record != 0 or key == first_key, "sparse index disagrees with leaf")
            if length <= 96:
                require(position + length <= used, "inline value overruns leaf")
                value = leaf[position:position + length]
                position += length
            else:
                require(position + 4 <= used, "truncated blob pointer")
                offset = struct.unpack_from("<I", leaf, position)[0]
                position += 4
                require(blob_offset <= offset <= len(content) - length, "blob outside file")
                require(offset not in blobs or blobs[offset] == length,
                        "one blob pointer has conflicting lengths")
                blobs[offset] = length
                value = content[offset:offset + length]
            if kind == 1:
                require(value in (b"\x01", b"\x02"), "invalid DCT flag")
            elif kind == 2:
                require(key == key.translate(buildlex.LOWER_TABLE), "unfolded THS key")
                decode_thesaurus(value)
            elif kind == 3:
                require(key == key.translate(buildlex.LOWER_TABLE), "unfolded HYP key")
                require(bool(value), "no-break HYP entries must be omitted")
                require(list(value) == sorted(set(value)) and
                        all(0 < point < len(key) for point in value), "invalid HYP boundaries")
            else:
                raise ValueError("unknown file kind")
            if key in wanted or seen % max(1, count // 8) == 0 or seen == count - 1:
                samples[key] = value
            keys.add(key)
            previous = key
            previous_global = key
            seen += 1
        require(position == used and not any(leaf[used:]), "leaf count/padding mismatch")
    require(seen == count, "header count differs from decoded record count")
    end = blob_offset
    for offset, length in sorted(blobs.items()):
        require(offset == end, "overlap or unreferenced gap in blob arena")
        end += length
    require(end == len(content), "unreferenced trailing bytes")
    # The normal release must retain its real-language regression vocabulary.
    # An explicitly smaller user budget can legitimately select even zero rows.
    if kind in (1, 2) and metadata.get("selection", {}).get("max_bytes", MAX_FILE_BYTES) == MAX_FILE_BYTES:
        require(wanted <= samples.keys(), "documented language sample missing: " + path.name)
    return content, samples, keys


def audit_set(directory, source_directory):
    """Validate a completed six-profile release and log native sample evidence."""
    report = json.loads((directory / "BUILD.json").read_text(encoding="utf-8"))
    require(report.get("project") == "OpenSpellGEOS", "wrong release project name")
    byte_limit = report.get("max_file_bytes")
    require(isinstance(byte_limit, int) and 64 <= byte_limit <= MAX_FILE_BYTES,
            "missing or excessive release file-size bound")
    require(len(report["profiles"]) == 6 and
            {profile["stem"] for profile in report["profiles"]} == set(SAMPLES),
            "expected exactly the six language profiles")
    with tempfile.TemporaryDirectory(prefix="openlex-audit-") as temporary:
        library = selfcheck.native_library(Path(temporary))
        checked = 0
        for profile in report["profiles"]:
            stem = profile["stem"]
            profile_keys = {}
            require(len(profile["files"]) == 3 and
                    {metadata["kind"] for metadata in profile["files"]} == {1, 2, 3},
                    "expected one DCT, THS and HYP per profile: " + stem)
            for metadata in profile["files"]:
                expected_name = stem + {1: ".DCT", 2: ".THS", 3: ".HYP"}[metadata["kind"]]
                require(metadata["file"] == expected_name,
                        "unexpected profile filename: " + str(metadata["file"]))
                selection = metadata.get("selection", {})
                require(selection.get("max_bytes") == byte_limit and
                        metadata["bytes"] <= byte_limit,
                        "selection metadata omits or exceeds the file-size bound: " + expected_name)
                require(selection.get("selected_records") == metadata["entries"] and
                        isinstance(selection.get("candidate_records"), int) and
                        selection["candidate_records"] >= metadata["entries"] and
                        selection.get("omitted_records") ==
                            selection["candidate_records"] - metadata["entries"] and
                        selection.get("estimated_bytes") == metadata["bytes"],
                        "selection counts/size disagree with output: " + expected_name)
                path = directory / metadata["file"]
                content, samples, keys = inspect_file(path, metadata)
                profile_keys[metadata["kind"]] = keys
                reader = selfcheck.Reader(library, content, metadata["kind"])
                require(reader.status == 1, "native open failed: " + path.name)
                for key, expected in samples.items():
                    status, actual, length = reader.find(key)
                    require((status, actual, length) == (1, expected, len(expected)),
                            "native/source decoder disagreement: " + path.name + " " + repr(key))
                if metadata["kind"] == 1:
                    present_words = []
                    omitted_words = []
                    for word in SAMPLES[stem]:
                        key = buildlex.encode_geos(word)
                        lookup = reader.find(key)
                        if key not in keys and byte_limit < MAX_FILE_BYTES:
                            require(lookup[0] == 0, "omitted spelling did not return a miss: " + word)
                            omitted_words.append(word)
                            continue
                        expected = b"\x01" if key == key.translate(buildlex.LOWER_TABLE) else b"\x02"
                        require(lookup[1] == expected, "incorrect case flag: " + word)
                        present_words.append(word)
                    print(stem + " spelling/accent/case samples: " + ", ".join(present_words))
                    if omitted_words:
                        print(stem + " smaller-budget spelling omissions verified: " + ", ".join(omitted_words))
                elif metadata["kind"] == 2:
                    word = THESAURUS_SAMPLES[stem]
                    key = buildlex.encode_geos(word).translate(buildlex.LOWER_TABLE)
                    lookup = reader.find(key)
                    if key not in keys and byte_limit < MAX_FILE_BYTES:
                        require(lookup[0] == 0, "omitted THS key did not return a miss: " + word)
                        print(stem + " smaller-budget thesaurus omission verified: " + word)
                    else:
                        senses = decode_thesaurus(lookup[1])
                        synonym = buildlex.decode_geos(senses[0][2][0])
                        print(stem + " thesaurus sample: " + word + " -> " + synonym)
                elif stem in ("EN_US", "EN_GB"):
                    expected = {"EN_US": {b"associate": b"\x02\x04", b"project": None,
                                          b"hyphenation": b"\x02\x06"},
                                "EN_GB": {b"associate": b"\x02\x04\x06", b"project": b"\x03",
                                          b"hyphenation": b"\x02\x06\x07"}}[stem]
                    for key, value in expected.items():
                        result = reader.find(key)
                        if key not in keys and byte_limit < MAX_FILE_BYTES:
                            require(result[0] == 0, "omitted HYP key did not return a miss: " + repr(key))
                        else:
                            require((result[0] == 0 if value is None else result == (1, value, len(value))),
                                    "hyphenation golden sample failed: " + stem + " " + repr(key))
                    print(stem + " available hyphenation golden samples and omitted-key misses: PASS")
                elif stem == "LB_LU":
                    require(metadata["entries"] == 0 and reader.find(b"Linguistik")[0] == 0,
                            "Luxembourgish unavailable source must stay a no-break file")
                    print(stem + " hyphenation: explicitly unavailable; empty no-break file verified")
                print("PASS " + path.name + ": %d records, %d bytes, %d native samples, SHA-256 %s" %
                      (metadata["entries"], len(content), len(samples), metadata["sha256"]))
                checked += metadata["entries"]
            folded_dictionary = {key.translate(buildlex.LOWER_TABLE)
                                 for key in profile_keys[1]}
            require(profile_keys[3] <= folded_dictionary,
                    "HYP contains words absent from selected DCT: " + stem)
            print("PASS " + stem + ": every hyphenated key belongs to the selected dictionary")
        # Repeat one complete real-language build from pinned source inputs,
        # exercising determinism independently of the decoded byte stream.
        specification = json.loads((source_directory / "buildset.json").read_text(encoding="utf-8"))
        british = next(profile for profile in specification["profiles"]
                       if profile["stem"] == "EN_GB")
        words = pinned_input(source_directory, specification, report, british["words"])
        ranking = None
        if british.get("priority"):
            ranking = pinned_input(source_directory, specification, report, british["priority"])
        priority = compactlex.Priority(ranking)
        dictionary = buildlex.read_words(words)
        if british.get("word_supplement"):
            supplement = pinned_input(source_directory, specification, report,
                                      british["word_supplement"])
            dictionary.update(buildlex.read_words(supplement))
        selected, _ = compactlex.select_entries(dictionary, priority, byte_limit)
        duplicate = Path(temporary) / "EN_GB.DCT"
        buildlex.build_file(1, "EN_GB", selected, duplicate)
        require(duplicate.read_bytes() == (directory / "EN_GB.DCT").read_bytes(),
                "repeated real dictionary build is not byte-identical")
        print("PASS EN_GB.DCT: repeated compact selection/build from source is byte-identical")
    print("PASS OpenSpellGEOS release audit: %d total records in all 18 files" % checked)


def main():
    """Audit the requested release directory, returning nonzero on any mismatch."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--sources", type=Path, default=Path(__file__).parent / "Data")
    args = parser.parse_args()
    audit_set(args.directory, args.sources)


if __name__ == "__main__":
    main()
