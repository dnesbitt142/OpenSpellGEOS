#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Select useful OpenSpellGEOS lexical data under a strict per-file byte budget.

The OLX1 ABI is unchanged. Selection uses pinned language priority inputs when
provided and an explicitly described deterministic heuristic otherwise. Exact
front-coded sizes are estimated before writing and checked against real output.
The fitting prefix is not claimed to be a globally optimal maximum: adding a
key can change page boundaries or blob sharing, so size need not be monotonic.
"""

import heapq
from pathlib import Path

import buildlex

MAX_FILE_BYTES = 500000
FALLBACK_POLICY = (
    "Unranked entries follow ranked entries; alphabetic words before simple "
    "hyphen/apostrophe forms, then other text; shorter forms first, then "
    "lowercase/title/other case and unsigned GEOS byte order. This is a "
    "deterministic heuristic, not measured corpus frequency."
)
SELECTION_POLICY = "priority-prefix-bounded-size-search-v1"
SENSE_LIMIT = 2
SYNONYM_LIMIT = 4
LABEL_LIMIT = 48
LETTER_BYTES = frozenset(index for index, character in enumerate(buildlex.GEOS_CHARS)
                         if character.isalpha())
SIMPLE_BYTES = LETTER_BYTES | frozenset((ord("-"), ord("'"), 0xD5))


class Priority:
    """Share one folded-word ranking across spelling, synonyms and hyphenation."""

    def __init__(self, priority_path=None, metadata=None):
        """Read a strict UTF-8 highest-priority-first list; retain first aliases.

        Duplicate case-folded words share their first rank. Metadata describes
        the upstream evidence but never changes selection. Blank lines and #
        comments are ignored; unsupported characters and overlength keys fail.
        """
        self.ranks = {}
        self.metadata = dict(metadata or {})
        if priority_path is not None:
            for number, line in enumerate(Path(priority_path).read_text(encoding="utf-8").splitlines(), 1):
                word = line.strip()
                if not word or word.startswith("#"):
                    continue
                try:
                    key = buildlex.encode_key(word).translate(buildlex.LOWER_TABLE)
                except ValueError as error:
                    raise ValueError("%s:%d: %s" % (priority_path, number, error)) from None
                if key not in self.ranks:
                    self.ranks[key] = len(self.ranks)
        self.metadata["ranked_keys"] = len(self.ranks)
        self.metadata["fallback"] = FALLBACK_POLICY

    def key(self, word):
        """Return a total deterministic priority key without locale dependence."""
        folded = word.translate(buildlex.LOWER_TABLE)
        case = 0 if word == folded else (1 if word[1:] == folded[1:] else 2)
        if folded in self.ranks:
            return (0, self.ranks[folded], 0, 0, case, folded, word)
        if all(character in LETTER_BYTES for character in word):
            category = 0
        elif (all(character in SIMPLE_BYTES for character in word) and
              any(character in LETTER_BYTES for character in word)):
            category = 1
        else:
            category = 2
        return (1, 0, category, len(word), case, folded, word)

    def contains(self, word):
        """Tell whether a spelling has an explicit source-priority rank."""
        return word.translate(buildlex.LOWER_TABLE) in self.ranks


def check_budget(max_bytes):
    """Accept an inclusive ceiling from the empty-file size through 500000."""
    if type(max_bytes) is not int or not 64 <= max_bytes <= MAX_FILE_BYTES:
        raise ValueError("max_bytes must be an integer in 64..500000")


def estimate_size(entries):
    """Calculate exact OLX1 length, including sparse index, padding and blobs.

    The estimate follows the specified record layout and greedy page packing.
    It never estimates from average word size. Long duplicate payloads share
    one blob, exactly as in buildlex.build_file. The writer result must still
    be checked; this helper is a selection aid, not an authorization to exceed
    the user's ceiling if a future format change makes the estimate obsolete.
    """
    blocks = 0
    used = 4
    previous = b""
    blobs = set()
    for key, value in sorted(entries.items()):
        prefix = buildlex.common_prefix(previous, key)
        stored = len(value) if len(value) <= buildlex.INLINE_MAX else 4
        size = 4 + len(key) - prefix + stored
        if blocks == 0 or used + size > buildlex.BLOCK_SIZE:
            blocks += 1
            used = 4
            size = 4 + len(key) + stored
        used += size
        previous = key
        if len(value) > buildlex.INLINE_MAX:
            blobs.add(value)
    return 64 + blocks * (buildlex.BLOCK_SIZE + buildlex.INDEX_SIZE) + sum(map(len, blobs))


def select_entries(entries, priority, max_bytes=MAX_FILE_BYTES):
    """Keep a fitting prefix of shared language priority with an exact ceiling.

    At most 204 records fit a leaf even with zero-length values. This format
    bound limits the ranked candidate heap before sorting a multi-million-word
    source. A bounded binary search chooses the largest *tested* fitting prefix;
    it does not assume or promise global size monotonicity or maximum coverage.
    Every retained entry outranks every omitted entry in that priority order.
    """
    check_budget(max_bytes)
    max_blocks = (max_bytes - 64) // (buildlex.BLOCK_SIZE + buildlex.INDEX_SIZE)
    candidate_limit = min(len(entries), max_blocks * 204)
    ranked = heapq.nsmallest(candidate_limit, entries, key=priority.key)
    lower = 0
    upper = len(ranked)
    best_count = 0
    best_bytes = 64
    while lower <= upper:
        count = lower + (upper - lower) // 2
        trial = {key: entries[key] for key in ranked[:count]}
        size = estimate_size(trial)
        if size <= max_bytes:
            best_count = count
            best_bytes = size
            lower = count + 1
        else:
            upper = count - 1
    selected = {key: entries[key] for key in ranked[:best_count]}
    report = {
        "policy": SELECTION_POLICY,
        "candidate_records": len(entries),
        "ranking_considered": len(ranked),
        "selected_records": len(selected),
        "omitted_records": len(entries) - len(selected),
        "priority_hit_records": sum(priority.contains(key) for key in selected),
        "max_bytes": max_bytes,
        "estimated_bytes": best_bytes,
        "optimality": "largest fitting tested prefix; not a global maximum claim",
    }
    return selected, report


def decode_senses(value):
    """Read already validated builder THS bytes while checking local bounds."""
    if not value:
        raise ValueError("empty thesaurus value")
    position = 1
    senses = []
    for _ in range(value[0]):
        if position + 2 > len(value):
            raise ValueError("truncated thesaurus sense")
        pos, length = value[position:position + 2]
        position += 2
        if position + length >= len(value):
            raise ValueError("truncated thesaurus label")
        label = value[position:position + length]
        position += length
        count = value[position]
        position += 1
        synonyms = []
        for _ in range(count):
            if position >= len(value):
                raise ValueError("truncated thesaurus synonym length")
            length = value[position]
            position += 1
            if position + length > len(value):
                raise ValueError("truncated thesaurus synonym")
            synonyms.append(value[position:position + length])
            position += length
        senses.append((pos, label, synonyms))
    if position != len(value):
        raise ValueError("trailing thesaurus payload bytes")
    return senses


def short_label(label, fallback):
    """Mark a whole-word shortened label with the GEOS ellipsis glyph.

    Literal ASCII periods are legacy UI delimiters, so byte C9 is the existing
    GEOS ellipsis character. It occupies one byte within the 48-byte limit.
    If no complete first token fits, an original retained synonym supplies an
    honest complete heading instead; no invented definition is introduced.
    """
    if len(label) <= LABEL_LIMIT:
        return label
    content_limit = LABEL_LIMIT - 1
    if label[content_limit:content_limit + 1] == b" ":
        prefix = label[:content_limit].rstrip()
    else:
        boundary = label.rfind(b" ", 0, content_limit + 1)
        prefix = label[:boundary].rstrip() if boundary > 0 else b""
    return prefix + b"\xc9" if prefix else fallback


def encode_compact_senses(senses):
    """Serialize a small list of retained original senses in the unchanged ABI."""
    value = bytearray([len(senses)])
    for pos, label, synonyms in senses:
        value.extend(bytes([pos, len(label)]) + label + bytes([len(synonyms)]))
        for synonym in synonyms:
            value.extend(bytes([len(synonym)]) + synonym)
    return bytes(value)


def compact_thesaurus(path, priority):
    """Trim valid source senses transparently before budgeted headword selection.

    Synonyms follow the shared language ranking. Senses follow their best
    retained synonym's rank, with source sense order as the tie-break. Keep the
    best sense and prefer a second known, different POS when one exists;
    otherwise keep the next best sense. Original POS and source terms survive.
    """
    original = buildlex.read_thesaurus(path)
    compact = {}
    source_senses = 0
    retained_senses = 0
    source_synonyms = 0
    retained_synonyms = 0
    labels_shortened = 0
    for key, value in original.items():
        choices = []
        for index, (pos, label, synonyms) in enumerate(decode_senses(value)):
            source_senses += 1
            source_synonyms += len(synonyms)
            distinct = {}
            for synonym in sorted(synonyms, key=priority.key):
                folded = synonym.translate(buildlex.LOWER_TABLE)
                if folded != key and folded not in distinct:
                    distinct[folded] = synonym
            selected_synonyms = list(distinct.values())[:SYNONYM_LIMIT]
            if not selected_synonyms:
                continue
            shortened = short_label(label, selected_synonyms[0])
            choices.append((priority.key(selected_synonyms[0]), index,
                            (pos, shortened, selected_synonyms), shortened != label))
        choices.sort(key=lambda item: (item[0], item[1]))
        retained = choices[:1]
        if len(choices) > 1:
            first_pos = choices[0][2][0]
            alternative = next((item for item in choices[1:]
                                if first_pos != 255 and item[2][0] != 255 and
                                item[2][0] != first_pos), choices[1])
            retained.append(alternative)
        if retained:
            compact[key] = encode_compact_senses([item[2] for item in retained])
            retained_senses += len(retained)
            retained_synonyms += sum(len(item[2][2]) for item in retained)
            labels_shortened += sum(item[3] for item in retained)
    report = {
        "sense_limit": SENSE_LIMIT,
        "synonyms_per_sense": SYNONYM_LIMIT,
        "label_byte_limit": LABEL_LIMIT,
        "source_headwords": len(original),
        "candidate_headwords": len(compact),
        "source_senses": source_senses,
        "candidate_senses": retained_senses,
        "source_synonyms": source_synonyms,
        "candidate_synonyms": retained_synonyms,
        "candidate_labels_shortened": labels_shortened,
        "sense_order": "best retained synonym priority, then original sense order",
        "second_sense": "prefer a different known POS; otherwise next best sense",
        "synonym_order": "shared language priority; folded duplicates and self terms removed",
        "label_rule": "whole-word prefix plus GEOS ellipsis within 48 bytes; original retained synonym if first token does not fit",
    }
    return compact, report


def hyphenation_entries(dictionary, patterns=None, exceptions=None, left_min=2, right_min=2):
    """Compute breaks only for selected dictionary words; omit every no-break row.

    Missing keys already mean no break in OLX1, so empty values provide no
    functionality. Exceptions override patterns only for the selected spelling
    vocabulary, preventing a large exception source from bypassing selection.
    """
    if not 1 <= left_min <= buildlex.KEY_MAX or not 1 <= right_min <= buildlex.KEY_MAX:
        raise ValueError("hyphenation minima must be within 1..64")
    trie = buildlex.read_patterns(patterns) if patterns else {}
    overrides = buildlex.read_exceptions(exceptions) if exceptions else {}
    vocabulary = {key.translate(buildlex.LOWER_TABLE) for key in dictionary}
    entries = {}
    for word in vocabulary:
        if word in overrides:
            value = bytes(point for point in overrides[word]
                          if left_min <= point <= len(word) - right_min)
        else:
            value = buildlex.pattern_breaks(word, trie, left_min, right_min)
        if value:
            entries[word] = value
    return entries
