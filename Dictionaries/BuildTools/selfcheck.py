#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exercise the OpenSpellGEOS C89 reader against valid and damaged files.

Run with Python 3 and a C compiler (CC defaults to cc). This check uses only
stdlib modules, builds in a temporary directory, and never modifies installed
Ensemble files. It tests exact lookups, block boundaries, external values,
short buffers, unsupported encodings, case maps, bounded suggestions, Liang
exceptions, and malformed lengths, offsets, ordering, padding and truncation.
It is a host correctness check, not a claim of 286 timing or GEOS execution.
"""

import argparse
import ctypes
import itertools
import json
import os
from pathlib import Path
import random
import struct
import subprocess
import tempfile

import buildlex

READ = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_ulong,
                       ctypes.c_ushort, ctypes.POINTER(ctypes.c_ubyte))


class Reader:
    """Own a byte-backed native context and its callback for one test file."""

    def __init__(self, library, content, kind):
        """Open immutable bytes with an exact-read callback and tracked I/O."""
        self.content = content
        self.calls = 0
        self.bytes_read = 0
        self.fail_at = None
        self.context = ctypes.create_string_buffer(8192)
        self.suggestions = ctypes.create_string_buffer(768)
        self.library = library
        self.callback = READ(self.read)
        self.status = library.olOpen(self.context, self.callback, None, kind)

    def read(self, unused, offset, count, destination):
        """Implement the target exact-read contract and reject every short read."""
        del unused
        self.calls += 1
        self.bytes_read += count
        if offset == self.fail_at or offset > len(self.content) or count > len(self.content) - offset:
            return 0
        ctypes.memmove(destination, self.content[offset:offset + count], count)
        return 1

    def find(self, key, capacity=4096):
        """Return status, copied bytes, and required length from native lookup."""
        output = ctypes.create_string_buffer(b"!" * max(1, capacity))
        length = ctypes.c_ushort(65535)
        status = self.library.olFind(self.context, key, len(key), output,
                                     capacity, ctypes.byref(length))
        return status, output.raw[:length.value], length.value

    def suggest(self, key, capacity=256):
        """Return all NUL-terminated alternatives emitted by the native engine."""
        output = ctypes.create_string_buffer(max(1, capacity))
        length = ctypes.c_ushort(65535)
        status = self.library.olSuggest(self.context, key, len(key), output,
                                        capacity, ctypes.byref(length), self.suggestions)
        assert status == 1
        assert length.value <= capacity
        result = output.raw[:length.value]
        assert not result or result.endswith(b"\0")
        return result[:-1].split(b"\0") if result else []


def native_library(directory, source=None):
    """Compile the unmodified runtime with strict C89 warnings and load its API."""
    source = Path(source) if source is not None else Path(__file__).resolve().parent
    output = directory / "openlex.so"
    size_check = directory / "sizecheck.test"
    size_check.write_text('#include "openlex.h"\n'
                          '/* Report context allocation size without exposing internals. */\n'
                          'unsigned long olContextBytes(void) { return sizeof(OLContext); }\n'
                          '/* Report spelling-only allocation and probe work for tests. */\n'
                          'unsigned long olSuggestBytes(void) { return sizeof(OLSuggestWorkspace); }\n'
                          '/* Read the bounded exact-probe counter after a query. */\n'
                          'unsigned long olSuggestProbeCount(OLSuggestWorkspace *p) { return p->probes; }\n',
                          encoding="ascii")
    subprocess.run([os.environ.get("CC", "cc"), "-std=c89", "-pedantic",
                    "-Wall", "-Wextra", "-Werror", "-fPIC", "-shared", "-x", "c",
                    "-I", str(source), str(source / "openlex.inc"),
                    str(size_check), "-o", str(output)], check=True)
    library = ctypes.CDLL(str(output))
    library.olOpen.argtypes = [ctypes.c_void_p, READ, ctypes.c_void_p, ctypes.c_ubyte]
    library.olOpen.restype = ctypes.c_int
    library.olFind.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_ushort,
                              ctypes.c_void_p, ctypes.c_ushort,
                              ctypes.POINTER(ctypes.c_ushort)]
    library.olFind.restype = ctypes.c_int
    library.olSuggest.argtypes = library.olFind.argtypes + [ctypes.c_void_p]
    library.olSuggest.restype = ctypes.c_int
    library.olLower.argtypes = [ctypes.c_ubyte]
    library.olLower.restype = ctypes.c_ubyte
    library.olUpper.argtypes = [ctypes.c_ubyte]
    library.olUpper.restype = ctypes.c_ubyte
    library.olContextBytes.restype = ctypes.c_ulong
    library.olSuggestBytes.restype = ctypes.c_ulong
    library.olSuggestProbeCount.argtypes = [ctypes.c_void_p]
    library.olSuggestProbeCount.restype = ctypes.c_ulong
    return library


def distance(left, right):
    """Calculate unbounded reference optimal-string-alignment edit distance."""
    rows = [[0] * (len(right) + 1) for _ in range(len(left) + 1)]
    for row in range(len(left) + 1):
        rows[row][0] = row
    for column in range(len(right) + 1):
        rows[0][column] = column
    for row in range(1, len(left) + 1):
        for column in range(1, len(right) + 1):
            rows[row][column] = min(rows[row - 1][column] + 1,
                                    rows[row][column - 1] + 1,
                                    rows[row - 1][column - 1] +
                                    (left[row - 1] != right[column - 1]))
            if (row > 1 and column > 1 and left[row - 1] == right[column - 2]
                    and left[row - 2] == right[column - 1]):
                rows[row][column] = min(rows[row][column], rows[row - 2][column - 2] + 1)
    return rows[-1][-1]


def must_fail(function):
    """Require a source-validation error instead of silent approximate output."""
    try:
        function()
    except ValueError:
        return
    raise AssertionError("invalid input unexpectedly accepted")


def check_sources(directory):
    """Verify charset, source caps, pattern overlays, exceptions and determinism."""
    words = directory / "words.txt"
    words.write_text("alpha\nAlpha\nna\u00efve\n\u00dcber\n", encoding="utf-8")
    entries = buildlex.read_words(words)
    assert entries[b"alpha"] == b"\x01" and entries[b"Alpha"] == b"\x02"
    assert buildlex.encode_geos("\u00e9") == buildlex.encode_geos("e\u0301") == b"\x8e"
    assert buildlex.encode_geos("\u00fd\u00dd\u00a4") == b"\xde\xdf\xdb"
    must_fail(lambda: buildlex.encode_geos("\U0001F600"))
    must_fail(lambda: buildlex.encode_key("a" * 65))
    must_fail(lambda: buildlex.encode_geos("a\tb"))
    thesaurus = directory / "thesaurus.json"
    sense = {"pos": "unknown", "label": "Related term", "synonyms": ["beta"]}
    thesaurus.write_text(json.dumps({"Alpha": [sense], "alpha": [sense]}), encoding="utf-8")
    thesaurus_entries = buildlex.read_thesaurus(thesaurus)
    assert list(thesaurus_entries) == [b"alpha"]
    assert thesaurus_entries[b"alpha"][:2] == b"\x01\xff"
    sense["synonyms"] = ["bad,split"]
    thesaurus.write_text(json.dumps({"alpha": [sense]}), encoding="utf-8")
    must_fail(lambda: buildlex.read_thesaurus(thesaurus))
    patterns = directory / "patterns.tex"
    patterns.write_text("% test\n\\patterns{a1b ab2c c1d}\n"
                        "\\hyphenation{ab-cd abcdx}\n", encoding="utf-8")
    words.write_text("abcd\nabcdx\n", encoding="utf-8")
    hyphens = buildlex.build_hyphenation(words, patterns, tex=True, left_min=1, right_min=1)
    assert hyphens == {b"abcd": b"\x02"}
    exceptions = directory / "exceptions.json"
    exceptions.write_text('{"abcd": [1, 3], "abcdx": []}', encoding="utf-8")
    hyphens = buildlex.build_hyphenation(words, patterns, exceptions, 1, 1, True)
    assert hyphens == {b"abcd": b"\x01\x03"}
    assert buildlex.pattern_breaks(b"abcd", buildlex.read_patterns(patterns, True), 1, 1) == b"\x01\x03"
    must_fail(lambda: buildlex.parse_pattern("a1b/x=y"))
    must_fail(lambda: buildlex.parse_pattern("a12b"))
    must_fail(lambda: buildlex.encode_sense({"pos": "noun", "label": "x", "synonyms": "wrong type"}))
    exceptions.write_text('{"abcd": [2, 2]}', encoding="utf-8")
    must_fail(lambda: buildlex.read_exceptions(exceptions))
    first = directory / "first.dct"
    second = directory / "second.dct"
    buildlex.build_file(1, "EN_GB", entries, first)
    buildlex.build_file(1, "EN_GB", dict(reversed(list(entries.items()))), second)
    assert first.read_bytes() == second.read_bytes()


def check_runtime(directory, library):
    """Exercise block transitions, mixed value storage and all API statuses."""
    entries = {("word%05d" % number).encode(): b"\x01" for number in range(4000)}
    entries[b"z" * 64] = b"\x02"
    entries[buildlex.encode_geos("\u00e4pfel")] = b"\x01"
    path = directory / "multi.dct"
    metadata = buildlex.build_file(1, "DE", entries, path)
    reader = Reader(library, path.read_bytes(), 1)
    assert reader.status == 1 and metadata["blocks"] > 10
    for key, value in entries.items():
        assert reader.find(key) == (1, value, len(value))
    for key in (b"aaa", b"word09999", b"zzzz"):
        assert reader.find(key) == (0, b"", 0)
    status, value, required = reader.find(b"word00000", 0)
    assert status == -2 and value == b"!" and required == 1
    assert reader.find(b"")[0] == -1
    assert reader.find(b"x" * 65)[0] == -1
    assert reader.find(b"bad\0word")[0] == -1
    assert len(reader.suggest(b"word00000")) <= 8
    assert reader.suggest(b"word00000", 0) == []
    for byte in range(256):
        expected_lower = bytes([byte]).translate(buildlex.LOWER_TABLE)[0]
        assert library.olLower(byte) == expected_lower
        if byte != expected_lower:
            assert library.olUpper(expected_lower) == byte
        assert library.olLower(library.olUpper(expected_lower)) == expected_lower
    values = {b"a": b"x" * 96, b"b": b"y" * 97, b"c": b"z" * 4096}
    buildlex.build_file(2, "FR", values, path)
    reader = Reader(library, path.read_bytes(), 2)
    assert reader.status == 1
    for key, value in values.items():
        assert reader.find(key) == (1, value, len(value))
    assert reader.find(b"c", 4095)[0] == -2
    assert Reader(library, path.read_bytes(), 1).status == -1
    buildlex.build_file(3, "EN", {b"hyphenation": b"\x02\x06"}, path)
    assert Reader(library, path.read_bytes(), 3).find(b"hyphenation") == (1, b"\x02\x06", 2)
    buildlex.build_file(1, "EN", {}, path)
    reader = Reader(library, path.read_bytes(), 1)
    assert reader.status == 1 and reader.find(b"absent")[0] == 0


def check_damage(directory, library):
    """Reject adversarial byte offsets and structural corruption without crashes."""
    path = directory / "damage.dct"
    buildlex.build_file(1, "EN", {b"alpha": b"\x01", b"beta": b"\x02"}, path)
    original = path.read_bytes()
    data_offset = struct.unpack_from("<I", original, 24)[0]
    for offset, value in ((0, 0), (5, 2), (6, 65), (7, 1), (44, 1)):
        damaged = bytearray(original)
        damaged[offset] = value
        assert Reader(library, bytes(damaged), 1).status == -1
    for field in (16, 20, 24, 28, 32):
        damaged = bytearray(original)
        struct.pack_into("<I", damaged, field, 0xFFFFFFFF)
        assert Reader(library, bytes(damaged), 1).status == -1
    for length in (0, 63, 64, len(original) - 1):
        assert Reader(library, original[:length], 1).status == -1
    for offset, value in ((64, 0), (65, 0), (129, 1),
                          (data_offset, 0), (data_offset + 4, 1),
                          (data_offset + 5, 65), (data_offset + 6, 0xFF),
                          (data_offset + 8, 0), (data_offset + 13, 3),
                          (len(original) - 1, 1)):
        damaged = bytearray(original)
        damaged[offset] = value
        reader = Reader(library, bytes(damaged), 1)
        assert reader.status == -1 or reader.find(b"alpha")[0] == -1, offset
    buildlex.build_file(2, "EN", {b"alpha": b"x" * 97}, path)
    damaged = bytearray(path.read_bytes())
    data_offset = struct.unpack_from("<I", damaged, 24)[0]
    struct.pack_into("<I", damaged, data_offset + 4 + 4 + 5, 0xFFFFFFF0)
    reader = Reader(library, bytes(damaged), 2)
    assert reader.status == 1 and reader.find(b"alpha")[0] == -1
    # Deterministic single-byte corruption fuzzing checks bounded failure, not
    # that every mutation is invalid (many mutate a legitimate spelling).
    randomizer = random.Random(8128)
    for _ in range(1000):
        damaged = bytearray(original)
        damaged[randomizer.randrange(len(damaged))] = randomizer.randrange(256)
        reader = Reader(library, bytes(damaged), 1)
        if reader.status == 1:
            assert reader.find(b"alpha")[0] in (-1, 0, 1)


def check_cache(directory, library):
    """Check page-edge lookups, bounded allocation, reopen invalidation and I/O retry."""
    require_size = library.olContextBytes()
    assert require_size <= 3328, require_size
    entries = {("term%05d" % number).encode(): b"\x01" for number in range(10000)}
    path = directory / "cache.dct"
    buildlex.build_file(1, "EN", entries, path)
    content = path.read_bytes()
    reader = Reader(library, content, 1)
    # Reusing top-level records must substantially reduce repeated-query reads,
    # and a query on either side of a split index record must remain correct.
    for key in list(entries)[::37]:
        assert reader.find(key) == (1, b"\x01", 1)
    reads_before = reader.calls
    assert reader.find(b"term05000")[0] == 1
    first_reads = reader.calls - reads_before
    reads_before = reader.calls
    assert reader.find(b"term05000")[0] == 1
    assert reader.calls - reads_before <= first_reads
    reader = Reader(library, content, 1)
    reader.fail_at = 0
    assert reader.find(b"term00000")[0] == -1
    reader.fail_at = None
    assert reader.find(b"term00000")[0] == 1
    # Contexts cache immutable files. Reopening is the explicit boundary at
    # which changed bytes become visible and every cache must be discarded.
    damaged = bytearray(content)
    damaged[65] = ord("z")
    reader.content = bytes(damaged)
    assert library.olOpen(reader.context, reader.callback, None, 1) == 1
    assert reader.find(b"term00000")[0] == -1
    reader.content = content
    assert library.olOpen(reader.context, reader.callback, None, 1) == 1
    assert reader.find(b"term00000")[0] == 1


def check_distance(directory, library):
    """Compare banded native suggestions with a full reference distance matrix."""
    path = directory / "suggest.dct"
    words = [b"".join(chars) for length in range(1, 5)
             for chars in itertools.product((b"a", b"b"), repeat=length)]
    for candidate in words:
        buildlex.build_file(1, "EN", {candidate: b"\x01"}, path)
        reader = Reader(library, path.read_bytes(), 1)
        for query in words:
            expected = [candidate] if query != candidate and distance(query, candidate) <= 2 else []
            assert reader.suggest(query) == expected, (query, candidate)
    buildlex.build_file(1, "EN", {b"spelling": b"\x01"}, path)
    reader = Reader(library, path.read_bytes(), 1)
    assert reader.suggest(b"speling") == [b"spelling"]
    assert reader.suggest(b"spellign") == [b"spelling"]
    assert reader.suggest(b"xxelling") == [b"spelling"]
    assert reader.suggest(b"xxxlling") == []


def check_suggestion_policy(directory, library):
    """Verify ranking, best-tier filtering, accent probes and bounded workspace."""
    assert library.olSuggestBytes() <= 768
    path = directory / "ranked.dct"
    entries = {word: b"\x01" for word in
               (b"tart", b"task", b"taste", b"tasty", b"tat", b"tats", b"taut", b"tea",
                b"teas", b"teat", b"test", b"this", b"hallo", b"haag", b"haf", b"house")}
    entries[buildlex.encode_geos("\u00e4ddi")] = b"\x01"
    buildlex.build_file(1, "EN", entries, path)
    reader = Reader(library, path.read_bytes(), 1)
    assert reader.suggest(b"teast")[0] == b"test"
    assert reader.suggest(b"Tthis") == [b"this"]
    assert reader.suggest(b"Thjis") == [b"this"]
    assert reader.suggest(b"Halo")[0] == b"hallo"
    assert reader.suggest(b"Addi")[0] == buildlex.encode_geos("\u00e4ddi")
    assert reader.suggest(b"hous")[0] == b"house"
    for query in (b"teast", b"Thjis", b"abcdefghijklmnop" * 4):
        candidates = reader.suggest(query)
        distances = [distance(query.lower(), candidate.lower()) for candidate in candidates]
        assert len(set(distances)) <= 1, (query, candidates)
        assert library.olSuggestProbeCount(reader.suggestions) <= 48
    assert reader.suggest(b"teast", 1) == []
    assert reader.find(b"teas")[0] == 1
    calls = reader.calls
    assert reader.find(b"test")[0] == 1
    assert reader.calls == calls, "validated cached-leaf range should avoid repeated I/O"
    # A distant exact-case spelling must still be found by the later grouped
    # case pass when no lowercase dictionary entry exists for that word.
    exact_accent = buildlex.encode_geos("\u00c4ddi")
    buildlex.build_file(1, "LB", {exact_accent: b"\x02"}, path)
    reader = Reader(library, path.read_bytes(), 1)
    assert reader.suggest(b"Addi") == [exact_accent]
    assert reader.suggest(b"ADDI") == [exact_accent]


def check_release_suggestions(dictionary_directory, library):
    """Exercise reported failures against supplied real compact dictionaries.

    These are canonical core results; test_icgeos.test separately checks the
    adapter's Titlecase/ALLCAPS projection. Real-data tests reject fabricated
    Hallo output when that word is absent from the delivered Luxembourgish list.
    Callback counts measure requested reads, not elapsed time on a 286.
    """
    samples = {
        "EN_GB": [("Tthis", "this"), ("Thjis", "this"), ("teast", "test"), ("hous", "house")],
        "LB_LU": [("Addi", "\u00e4ddi")],
    }
    for language, queries in samples.items():
        content = (dictionary_directory / (language + ".DCT")).read_bytes()
        for query, expected in queries:
            reader = Reader(library, content, 1)
            assert reader.status == 1
            before = reader.calls
            candidates = reader.suggest(buildlex.encode_geos(query))
            reads = reader.calls - before
            folded = [candidate.translate(buildlex.LOWER_TABLE) for candidate in candidates]
            expected_key = buildlex.encode_geos(expected).translate(buildlex.LOWER_TABLE)
            assert folded.count(expected_key) == 1, (query, candidates)
            assert folded[0] == expected_key, (query, candidates)
            assert len(folded) == len(set(folded))
            assert library.olSuggestProbeCount(reader.suggestions) <= 48
            assert reads <= 160, (query, reads)
            for candidate in candidates:
                assert reader.find(candidate)[0] == 1
            print("REAL %s %s -> %s; %d reads, %d probes" %
                  (language, query, ", ".join(buildlex.decode_geos(word) for word in candidates),
                   reads, library.olSuggestProbeCount(reader.suggestions)))
    reader = Reader(library, (dictionary_directory / "LB_LU.DCT").read_bytes(), 1)
    assert reader.find(b"hallo")[0] == 0 and reader.find(b"Hallo")[0] == 0
    candidates = reader.suggest(b"Halo")
    assert all(word.translate(buildlex.LOWER_TABLE) != b"hallo" for word in candidates)
    print("REAL LB_LU Halo: Hallo absent from source dictionary; no invented suggestion")
    print("Memory: OLContext=%d, spelling-only workspace=%d host bytes" %
          (library.olContextBytes(), library.olSuggestBytes()))


def main():
    """Run the complete small regression suite and print a single clear result."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dicts", type=Path, help="also test the unchanged compact release DICTS")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="openlex-check-") as temporary:
        directory = Path(temporary)
        library = native_library(directory)
        check_sources(directory)
        check_runtime(directory, library)
        check_damage(directory, library)
        check_cache(directory, library)
        check_distance(directory, library)
        check_suggestion_policy(directory, library)
        if args.dicts is not None:
            check_release_suggestions(args.dicts, library)
    print("PASS: C89 reader, 4002 lookups, corruption, cache, charset, builders and suggestions")


if __name__ == "__main__":
    main()
