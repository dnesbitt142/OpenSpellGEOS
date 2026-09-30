#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Build OpenSpellGEOS OLX1 lexical files using Python 3 stdlib only.

Inputs are UTF-8, normalized to NFC, and explicitly encoded into GEOS SBCS.
No proprietary dictionary is read. Source licensing is the operator's
responsibility; see the accompanying language provenance and format documents.
The target stores word lookups and precomputed hyphenation, not Hunspell or
TeX interpreters. This deliberately moves expensive processing to the host.
"""

import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import sys
import tempfile
import unicodedata

BLOCK_SIZE = 1024
KEY_MAX = 64
VALUE_MAX = 4096
INLINE_MAX = 96
INDEX_SIZE = 65
KINDS = {"dictionary": 1, "thesaurus": 2, "hyphenation": 3}
POS = {"adjective": 0, "noun": 1, "adverb": 2, "verb": 3, "unknown": 255}
# GEOS largely follows Mac Roman; these code points differ. The private logo
# byte is excluded from all linguistic inputs instead of treating it as text.
GEOS_CHARS = list(bytes(range(256)).decode("mac_roman"))
for _byte, _codepoint in {0xB6: 0x03B4, 0xB7: 0x03A3, 0xB8: 0x03A0,
                           0xC6: 0x0394, 0xDB: 0x00A4, 0xDE: 0x00FD,
                           0xDF: 0x00DD, 0xF0: 0xE000}.items():
    GEOS_CHARS[_byte] = chr(_codepoint)
GEOS_ENCODE = {char: byte for byte, char in enumerate(GEOS_CHARS)
               if byte >= 32 and byte != 127 and byte != 0xF0}
CAPITALS = bytes.fromhex("80 81 82 83 84 85 86 ae af cb cc cd ce d9 df "
                         "e5 e6 e7 e8 e9 ea eb ec ed ee ef f1 f2 f3 f4")
LOWERCASE = bytes.fromhex("8a 8c 8d 8e 96 9a 9f be bf 88 8b 9b cf d8 de "
                          "89 90 87 91 8f 92 94 95 93 97 99 98 9c 9e 9d")
LOWER_TABLE = bytes.maketrans(bytes(range(65, 91)) + CAPITALS,
                             bytes(range(97, 123)) + LOWERCASE)


def encode_geos(text):
    """NFC-normalize text and encode only printable supported GEOS characters."""
    normalized = unicodedata.normalize("NFC", text)
    try:
        return bytes(GEOS_ENCODE[char] for char in normalized)
    except KeyError as error:
        raise ValueError("not representable in GEOS SBCS: U+%04X in %r" %
                         (ord(error.args[0]), text)) from None


def decode_geos(data):
    """Decode GEOS bytes for diagnostics and test output."""
    return "".join(GEOS_CHARS[byte] for byte in data)


def encode_key(text):
    """Validate an encoded lookup key, preserving spelling and letter case."""
    encoded = encode_geos(text)
    if not 1 <= len(encoded) <= KEY_MAX:
        raise ValueError("key must contain 1..64 GEOS bytes: %r" % text)
    return encoded


def read_words(path, skip_unencodable=False):
    """Read one surface form per UTF-8 line; report every skipped input class.

    Lowercase entries permit title/allcaps matches (flag 1); all other case
    forms are exact-only (flag 2). Blank lines and lines starting # are ignored.
    The skip option applies to unsupported characters or long words, never to
    malformed UTF-8. It is intended for large openly licensed source corpora.
    """
    entries = {}
    skipped = 0
    for number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        word = line.strip()
        if not word or word.startswith("#"):
            continue
        try:
            key = encode_key(word)
        except ValueError:
            if not skip_unencodable:
                raise ValueError("%s:%d: unsupported word %r" % (path, number, word))
            skipped += 1
            continue
        entries[key] = bytes([1 if key.translate(LOWER_TABLE) == key else 2])
    if skipped:
        print("%s: skipped %d unencodable or overlength entries" % (path, skipped),
              file=sys.stderr)
    return entries


def common_prefix(left, right):
    """Return the byte prefix length shared by two already encoded keys."""
    length = 0
    for old, new in zip(left, right):
        if old != new:
            break
        length += 1
    return length


def build_file(kind, language, entries, output, max_bytes=None):
    """Write OLX1 atomically and return counts, length, and SHA-256 metadata.

    Leaves contain prefix-compressed keys and inline values up to 96 bytes.
    Longer values are deduplicated in an immutable external blob arena. The
    sparse index has one fixed-width first-key record per leaf, so the 286
    can binary-search it without allocating the index in conventional memory.
    Public build commands supply max_bytes, which is checked against the real
    packed length before touching an existing output. None is reserved for
    low-level format experiments and internal reader fixtures.
    """
    if kind not in KINDS.values() or not re.fullmatch(r"[A-Z]{2}(?:_[A-Z]{2})?", language):
        raise ValueError("invalid kind or language (expected EN or EN_GB)")
    pages = []
    first_keys = []
    current = []
    used = 4
    previous = b""
    blob_values = {}
    blob_size = 0
    for key, value in sorted(entries.items()):
        if not isinstance(key, bytes) or not isinstance(value, bytes):
            raise ValueError("build_file requires bytes keys and values")
        if not 1 <= len(key) <= KEY_MAX or any(byte < 32 or byte == 127 for byte in key):
            raise ValueError("invalid encoded key")
        if len(value) > VALUE_MAX:
            raise ValueError("value exceeds 4096 bytes: %r" % key)
        if kind == 1 and value not in (b"\x01", b"\x02"):
            raise ValueError("dictionary flag must be 1 or 2")
        if kind == 3 and (list(value) != sorted(set(value)) or
                          any(point == 0 or point >= len(key) for point in value)):
            raise ValueError("invalid hyphenation boundaries")
        prefix = common_prefix(previous, key)
        stored_length = len(value) if len(value) <= INLINE_MAX else 4
        record_length = 4 + len(key) - prefix + stored_length
        if used + record_length > BLOCK_SIZE:
            pages.append(current)
            current = []
            used = 4
            prefix = 0
            record_length = 4 + len(key) + stored_length
        if not current:
            first_keys.append(key)
        if len(value) > INLINE_MAX and value not in blob_values:
            blob_values[value] = blob_size
            blob_size += len(value)
        current.append((prefix, key[prefix:], value))
        used += record_length
        previous = key
    if current:
        pages.append(current)
    data_offset = 64 + len(pages) * INDEX_SIZE
    blob_offset = data_offset + len(pages) * BLOCK_SIZE
    file_size = blob_offset + blob_size
    if file_size > 0x7FFFFFFF:
        raise ValueError("file exceeds signed 31-bit target seek limit")
    if max_bytes is not None:
        if type(max_bytes) is not int or not 64 <= max_bytes <= 500000:
            raise ValueError("max_bytes must be an integer in 64..500000")
        if file_size > max_bytes:
            raise ValueError("encoded file needs %d bytes, above the %d-byte limit; "
                             "reduce the input or use build_languages.py for compact selection" %
                             (file_size, max_bytes))
    header = bytearray(64)
    struct.pack_into("<4sBBBBHHIIIIII", header, 0, b"OLX1", kind, 1, KEY_MAX,
                     0, 64, BLOCK_SIZE, len(entries), len(pages), 64,
                     data_offset, blob_offset, file_size)
    header[36:36 + len(language)] = language.encode("ascii")
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", dir=output.parent,
                                         prefix="." + output.name + ".", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(header)
            for key in first_keys:
                stream.write(bytes([len(key)]) + key + bytes(KEY_MAX - len(key)))
            for records in pages:
                leaf = bytearray(4)
                for prefix, suffix, value in records:
                    leaf.extend(struct.pack("<BBH", prefix, len(suffix), len(value)))
                    leaf.extend(suffix)
                    if len(value) <= INLINE_MAX:
                        leaf.extend(value)
                    else:
                        leaf.extend(struct.pack("<I", blob_offset + blob_values[value]))
                struct.pack_into("<HH", leaf, 0, len(leaf), len(records))
                stream.write(leaf + bytes(BLOCK_SIZE - len(leaf)))
            for value in blob_values:
                stream.write(value)
        temporary.replace(output)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    return {"file": output.name, "language": language, "kind": kind,
            "entries": len(entries), "blocks": len(pages), "bytes": file_size,
            "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}


def encode_sense(sense):
    """Encode one sense after checking legacy grammar and synonym limits."""
    if (not isinstance(sense, dict) or
            not isinstance(sense.get("label"), str) or
            not isinstance(sense.get("synonyms"), list) or
            any(not isinstance(item, str) for item in sense["synonyms"])):
        raise ValueError("sense requires a text label and a list of text synonyms")
    pos = POS[sense["pos"]]
    label = encode_geos(sense["label"])
    synonyms = [encode_geos(item) for item in sense["synonyms"]]
    if not 1 <= len(label) <= 180 or not 1 <= len(synonyms) <= 80:
        raise ValueError("label/synonym count exceeds legacy limits")
    if any(not 1 <= len(item) <= 26 or b"." in item or b"," in item
           for item in synonyms):
        raise ValueError("synonym exceeds 26 bytes or contains . or ,")
    if sum(len(item) + 1 for item in synonyms) >= 1600:
        raise ValueError("synonym output exceeds legacy buffer")
    payload = bytearray(bytes([pos, len(label)]) + label + bytes([len(synonyms)]))
    for synonym in synonyms:
        payload.extend(bytes([len(synonym)]) + synonym)
    return bytes(payload), len(label) + 8


def read_thesaurus(path, skip_unencodable=False):
    """Encode JSON senses, merging case-fold aliases without losing valid senses.

    Strict mode rejects all unrepresentable or oversized data. With the skip
    flag, invalid senses and those beyond the legacy UI caps are omitted and
    counted on stderr; the first fitting distinct senses are retained. This
    explicit lossy mode is useful when importing large general dictionaries.
    """
    source = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(source, dict):
        raise ValueError("thesaurus input must be a JSON object")
    grouped = {}
    skipped = 0
    for word, senses in source.items():
        try:
            key = encode_key(word).translate(LOWER_TABLE)
            if not isinstance(senses, list) or not senses:
                raise ValueError("expected a nonempty list of senses")
        except (TypeError, ValueError) as error:
            if not skip_unencodable:
                raise ValueError("%s: %r: %s" % (path, word, error)) from None
            skipped += 1
            continue
        distinct = grouped.setdefault(key, [])
        for sense in senses:
            try:
                encoded = encode_sense(sense)
            except (KeyError, TypeError, ValueError) as error:
                if not skip_unencodable:
                    raise ValueError("%s: %r: %s" % (path, word, error)) from None
                skipped += 1
                continue
            if encoded not in distinct:
                distinct.append(encoded)
    entries = {}
    for key, senses in grouped.items():
        payload = bytearray([0])
        meaning_bytes = 1
        for encoded, label_bytes in senses:
            if (payload[0] == 26 or meaning_bytes + label_bytes >= 1600 or
                    len(payload) + len(encoded) > VALUE_MAX):
                if not skip_unencodable:
                    raise ValueError("thesaurus entry exceeds legacy buffer: %r" % key)
                skipped += 1
                continue
            payload.extend(encoded)
            payload[0] += 1
            meaning_bytes += label_bytes
        if payload[0]:
            entries[key] = bytes(payload)
    if skipped:
        print("%s: omitted %d unsupported/oversized entries or senses" %
              (path, skipped), file=sys.stderr)
    return entries


def parse_pattern(pattern):
    """Split one standard Liang pattern into GEOS letters and boundary weights.

    Extended libhyphen replacement rules containing slash or equals are not
    accepted: they change spelling at a break and cannot be represented by a
    list of byte boundaries. TeX control sequences must be decoded upstream.
    """
    if any(char in pattern for char in "\\/{},=\"%"):
        raise ValueError("unsupported pattern syntax: %r" % pattern)
    letters = []
    weights = [0]
    previous_digit = False
    for char in unicodedata.normalize("NFC", pattern):
        if "0" <= char <= "9":
            if previous_digit:
                raise ValueError("adjacent pattern digits are not single weights: %r" % pattern)
            weights[-1] = int(char)
            previous_digit = True
        else:
            letters.append(char)
            weights.append(0)
            previous_digit = False
    key = encode_geos("".join(letters)).translate(LOWER_TABLE)
    if not key or len(key) > KEY_MAX + 2:
        raise ValueError("invalid pattern length")
    return key, weights


def tex_bodies(content, command):
    """Extract literal unnested TeX command bodies without executing any TeX."""
    content = re.sub(r"(?m)%.*$", "", content)
    bodies = []
    for match in re.finditer(r"\\" + re.escape(command) + r"\s*\{", content):
        start = match.end()
        end = content.find("}", start)
        if end == -1 or "{" in content[start:end]:
            raise ValueError("nested or unterminated TeX %s block" % command)
        bodies.append(content[start:end])
    return bodies


def read_patterns(path, tex=False):
    """Build a host-only trie from plain UTF-8 Liang patterns.

    With tex=True, extract balanced \\patterns{...} bodies after stripping
    percent comments. No TeX macro expansion is attempted. Unexpected control
    sequences are errors, preventing plausible-looking but incorrect output.
    """
    content = Path(path).read_text(encoding="utf-8")
    content = re.sub(r"(?m)%.*$", "", content)
    if tex:
        bodies = tex_bodies(content, "patterns")
        if not bodies:
            raise ValueError("no literal TeX patterns block found")
        content = "\n".join(bodies)
    trie = {}
    for token in content.split():
        letters, weights = parse_pattern(token)
        node = trie
        for letter in letters:
            node = node.setdefault(letter, {})
        old = node.get(None, [0] * len(weights))
        node[None] = [max(left, right) for left, right in zip(old, weights)]
    return trie


def pattern_breaks(word, trie, left_min, right_min):
    """Evaluate Liang's maximum-overlay rule offline for one folded GEOS word."""
    decorated = b"." + word + b"."
    scores = [0] * (len(decorated) + 1)
    for start in range(len(decorated)):
        node = trie
        for end in range(start, len(decorated)):
            node = node.get(decorated[end])
            if node is None:
                break
            for offset, value in enumerate(node.get(None, ())):
                if value > scores[start + offset]:
                    scores[start + offset] = value
    return bytes(point for point in range(left_min, len(word) - right_min + 1)
                 if scores[point + 1] & 1)


def read_exceptions(path):
    """Read explicit exceptions as JSON positions or hyphen-separated words.

    JSON boundaries refer to NFC Unicode character positions. Every supported
    character has one GEOS byte, so these positions also index target strings.
    A JSON empty list deliberately suppresses every pattern-derived break.
    """
    path = Path(path)
    if path.suffix.lower() == ".json":
        source = json.loads(path.read_text(encoding="utf-8"))
    else:
        source = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            line = unicodedata.normalize("NFC", line.strip())
            if not line or line.startswith("#"):
                continue
            parts = line.split("-")
            if any(not part for part in parts):
                raise ValueError("empty exception syllable: %r" % line)
            source["".join(parts)] = [sum(map(len, parts[:index]))
                                      for index in range(1, len(parts))]
    if not isinstance(source, dict):
        raise ValueError("exception input must map words to position lists")
    entries = {}
    for word, positions in source.items():
        key = encode_key(word).translate(LOWER_TABLE)
        if (not isinstance(positions, list) or
                any(type(point) is not int or not 1 <= point < len(key)
                    for point in positions) or positions != sorted(set(positions))):
            raise ValueError("invalid exception positions for %r" % word)
        if key in entries and entries[key] != bytes(positions):
            raise ValueError("case-fold exception collision: %r" % word)
        entries[key] = bytes(positions)
    return entries


def read_tex_exceptions(path):
    """Decode literal TeX hyphenation exceptions, including no-break words."""
    content = Path(path).read_text(encoding="utf-8")
    entries = {}
    for body in tex_bodies(content, "hyphenation"):
        for token in body.split():
            if any(char in token for char in "\\{},=%"):
                raise ValueError("unsupported TeX exception syntax: %r" % token)
            parts = unicodedata.normalize("NFC", token).split("-")
            if any(not part for part in parts):
                raise ValueError("empty TeX exception syllable: %r" % token)
            key = encode_key("".join(parts)).translate(LOWER_TABLE)
            positions = bytes(sum(map(len, parts[:index]))
                              for index in range(1, len(parts)))
            if key in entries and entries[key] != positions:
                raise ValueError("conflicting TeX exception: %r" % token)
            entries[key] = positions
    return entries


def build_hyphenation(words, patterns=None, exceptions=None, left_min=2,
                      right_min=2, tex=False, skip_unencodable=False):
    """Precompute boundaries for known words; explicit exceptions override rules.

    Unknown words receive no automatic breaks on the target. Only entries
    with at least one legal break need storage, because missing means no break.
    This conservative policy avoids incorrect heuristic syllabification.
    """
    if not 1 <= left_min <= KEY_MAX or not 1 <= right_min <= KEY_MAX:
        raise ValueError("hyphenation minima must be within 1..64")
    trie = read_patterns(patterns, tex) if patterns else {}
    entries = {}
    for key in read_words(words, skip_unencodable):
        key = key.translate(LOWER_TABLE)
        value = pattern_breaks(key, trie, left_min, right_min)
        if value:
            entries[key] = value
    overrides = read_tex_exceptions(patterns) if tex and patterns else {}
    if exceptions:
        overrides.update(read_exceptions(exceptions))
    for key, value in overrides.items():
        value = bytes(point for point in value
                      if left_min <= point <= len(key) - right_min)
        if value:
            entries[key] = value
        else:
            entries.pop(key, None)
    return entries


def main(argv=None):
    """Parse a build command, emit one file and print machine-readable statistics."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=KINDS)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--language", required=True)
    parser.add_argument("--skip-unencodable", action="store_true")
    parser.add_argument("--patterns", type=Path)
    parser.add_argument("--exceptions", type=Path)
    parser.add_argument("--left-min", type=int, default=2)
    parser.add_argument("--right-min", type=int, default=2)
    parser.add_argument("--tex", action="store_true")
    parser.add_argument("--max-bytes", type=int, default=500000,
                        help="hard encoded-file ceiling, 64..500000 (default: 500000)")
    args = parser.parse_args(argv)
    try:
        if not 64 <= args.max_bytes <= 500000:
            raise ValueError("--max-bytes must be within 64..500000")
        if any(source is not None and source.resolve() == args.output.resolve()
               for source in (args.input, args.patterns, args.exceptions)):
            raise ValueError("output must not replace an input source file")
        if args.kind == "dictionary":
            entries = read_words(args.input, args.skip_unencodable)
        elif args.kind == "thesaurus":
            entries = read_thesaurus(args.input, args.skip_unencodable)
        else:
            entries = build_hyphenation(args.input, args.patterns, args.exceptions,
                                         args.left_min, args.right_min, args.tex,
                                         args.skip_unencodable)
        result = build_file(KINDS[args.kind], args.language, entries, args.output,
                            max_bytes=args.max_bytes)
    except (OSError, ValueError, UnicodeError) as error:
        parser.exit(2, "buildlex: %s\n" % error)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
