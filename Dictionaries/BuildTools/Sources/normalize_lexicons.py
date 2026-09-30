#!/usr/bin/env python3
"""Normalize selected permissive linguistic sources for the PC/GEOS builder.

Copyright 2026. Licensed under the Apache License, Version 2.0.
Source databases retain their own notices, provided in lexicons/ and provenance.

This host-side Python 3 tool uses only the standard library. It never reads the
attached proprietary dictionaries. Inputs are downloaded originals under
lexicons/. Extract exactly german.dic from german.7z with 7-Zip before running.
Outputs are UTF-8 in normalized/; lexical case is preserved. No inflections,
synonyms or syllabification are invented. Source-specific omissions are counted.
"""

import collections
import io
import json
from pathlib import Path
import re
import tarfile
import unicodedata

ROOT = Path(__file__).resolve().parent
RAW = ROOT / 'lexicons'
OUT = ROOT / 'normalized'


def lexical_word(word):
    """Accept letters and internal apostrophes/hyphens, preserving spelling case.

    Normalization is Unicode NFC. Reject numbers, whitespace, control characters,
    leading/trailing punctuation and unconverted source markup. This deliberately
    omits standalone abbreviations with periods and numeric product names.
    """
    word = unicodedata.normalize('NFC', word.strip())
    if not word or not word[0].isalpha() or not word[-1].isalpha():
        return None
    if not all(char.isalpha() or char in "'-" for char in word):
        return None
    return word


def write_words(locale, words, counts):
    """Write a deterministic unique word list and record length distributions."""
    counts['overlength_words_omitted'] = sum(len(word) > 64 for word in words)
    ordered = sorted(word for word in words if len(word) <= 64)
    (OUT / (locale + '.words.txt')).write_text(
        ''.join(word + '\n' for word in ordered), encoding='utf-8')
    counts['unique_words'] = len(ordered)
    counts['words_longer_than_26_characters'] = sum(len(w) > 26 for w in ordered)
    counts['words_longer_than_63_characters'] = sum(len(w) > 63 for w in ordered)
    return dict(counts)


def normalize_plain(locale, source, encoding, transform=None):
    """Normalize one-word-per-line sources without adding unobserved forms."""
    words = set()
    counts = collections.Counter()
    with source.open(encoding=encoding) as stream:
        for line in stream:
            counts['input_rows'] += 1
            source_word = line.strip()
            if transform is not None:
                source_word = transform(source_word)
            word = lexical_word(source_word)
            if word is None:
                counts['invalid_rows'] += 1
                continue
            words.add(word)
    return write_words(locale, words, counts)


def decode_moby_french(word):
    """Decode Moby French's explicit postfix diacritics, not phonetic guesses.

    The French list consistently writes acute as e', grave as a`/e`/u`,
    circumflex as vowel^, diaeresis as vowel-doublequote, and cedilla as c/.
    Apostrophes after consonants remain apostrophes. Unrecognised markup remains
    visible and is rejected by lexical_word, rather than silently discarded.
    Ligature spellings such as 'oeuvre' remain exactly as supplied upstream.
    """
    marks = {'e\'': '\u00e9', 'a`': '\u00e0', 'e`': '\u00e8',
             'u`': '\u00f9', 'a^': '\u00e2', 'e^': '\u00ea',
             'i^': '\u00ee', 'o^': '\u00f4', 'u^': '\u00fb',
             'a"': '\u00e4', 'e"': '\u00eb', 'i"': '\u00ef',
             'o"': '\u00f6', 'u"': '\u00fc', 'y"': '\u00ff',
             'c/': '\u00e7'}
    return re.sub(r"[aeiouyc]['`^\"/]", lambda match: marks.get(
        match.group(0), match.group(0)), word)


def normalize_swedish():
    """Stream NST's Latin-1 lexicon and retain usable, non-GARB surface forms.

    Field 1 is the written form, field 4 contains '+' compound boundaries, and
    field 8 marks unusable material GARB. Only exact concatenations of components
    of at least two letters contribute hyphenation exceptions; linking-letter,
    overlap, alternation and uncertain cases are omitted. SAMPA pronunciation is
    never treated as orthographic hyphenation. Duplicate analyses intersect their
    nonempty break sets, avoiding contradictory compound boundaries.
    """
    words = set()
    compounds = {}
    counts = collections.Counter()
    member = 'NST svensk leksikon/swe030224NST.pron/swe030224NST.pron'
    with tarfile.open(RAW / 'sv.leksikon.tar.gz', 'r:gz') as archive:
        with io.TextIOWrapper(archive.extractfile(member), encoding='latin1') as stream:
            for line in stream:
                counts['input_rows'] += 1
                fields = line.rstrip('\r\n').split(';')
                if len(fields) != 51:
                    counts['malformed_rows'] += 1
                    continue
                if fields[7] == 'GARB':
                    counts['garbage_rows'] += 1
                    continue
                word = lexical_word(fields[0])
                if word is None:
                    counts['invalid_rows'] += 1
                    continue
                words.add(word)
                parts = fields[3].split('+')
                if len(parts) < 2 or not all(p.isalpha() and len(p) >= 2 for p in parts):
                    continue
                if ''.join(parts).lower() != word.lower():
                    counts['nonconcatenating_compounds'] += 1
                    continue
                boundaries = set()
                offset = 0
                for part in parts[:-1]:
                    offset += len(part)
                    if offset >= 2 and len(word) - offset >= 2:
                        boundaries.add(offset)
                key = word.lower()
                if key in compounds:
                    compounds[key] &= boundaries
                else:
                    compounds[key] = boundaries
    hyphens = {word: sorted(points) for word, points in sorted(compounds.items()) if points}
    (OUT / 'SV.hyp-exceptions.json').write_text(
        json.dumps(hyphens, ensure_ascii=False, separators=(',', ':')) + '\n',
        encoding='utf-8')
    counts['compound_exception_words'] = len(hyphens)
    return write_words('SV', words, counts)


def synonym_text(source_word):
    """Decode WordNet lexical tokens and enforce the legacy synonym slot size."""
    word = re.sub(r'\((?:a|p|ip)\)$', '', source_word).replace('_', ' ')
    if not word or len(word) > 26 or any(c in word for c in '.,'):
        return None
    if not all(c.isalpha() or c in " '-" for c in word):
        return None
    return word


def wordnet_thesaurus():
    """Extract true synonym sets and definitions in WordNet's sense order.

    Antonyms, hypernyms, related words and cross-POS pointers are not synonyms.
    Keep same-synset alternatives only. Omit the queried word itself. Preserve
    case in alternatives, fold query keys to lowercase, and bound each result for the legacy
    Spell UI: <=26 senses, <=80 alternatives/sense, <=26 bytes/alternative,
    <=180 bytes/definition, <1500 definition-list bytes, and <4000 record bytes.
    Definitions are shortened at a word boundary; omitted senses are counted.
    """
    result = {}
    counts = collections.Counter()
    pos_names = {'noun': 'noun', 'verb': 'verb', 'adj': 'adjective', 'adv': 'adverb'}
    with tarfile.open(RAW / 'wn3.1.dict.tar.gz', 'r:gz') as archive:
        for part, name in pos_names.items():
            synsets = {}
            data = archive.extractfile('dict/data.' + part).read().decode('ascii')
            if part == 'noun':
                notice = '\n'.join(re.sub(r'^\s*\d+ ?', '', line).rstrip()
                                   for line in data.splitlines() if line.startswith('  '))
                (RAW / 'WordNet-3.1-LICENSE.txt').write_text(notice + '\n', encoding='ascii')
            for line in data.splitlines():
                if not line or line.startswith(' '):
                    continue
                counts['input_synsets'] += 1
                raw, gloss = line.split('|', 1)
                fields = raw.split()
                word_count = int(fields[3], 16)
                words = []
                for index in range(word_count):
                    word = synonym_text(fields[4 + index * 2])
                    if word and word not in words:
                        words.append(word)
                    elif word is None:
                        counts['unsupported_synonym_tokens'] += 1
                if len(words) < 2:
                    continue
                label = gloss.strip().split('; "', 1)[0]
                if len(label) > 180:
                    label = label[:177].rsplit(' ', 1)[0] + '...'
                    counts['shortened_definitions'] += 1
                synsets[fields[0]] = (words, label)
            index_data = archive.extractfile('dict/index.' + part).read().decode('ascii')
            for line in index_data.splitlines():
                if not line or line.startswith(' '):
                    continue
                fields = line.split()
                head = synonym_text(fields[0])
                if not head or lexical_word(head) is None:
                    continue
                head = head.lower()
                offsets = fields[6 + int(fields[3]):]
                senses = result.setdefault(head, [])
                label_bytes = sum(len(sense['label']) + 15 for sense in senses)
                record_bytes = sum(len(sense['label']) + sum(len(w) + 1 for w in sense['synonyms']) + 20
                                   for sense in senses)
                for offset in offsets:
                    entry = synsets.get(offset)
                    if entry is None:
                        continue
                    words, label = entry
                    synonyms = [word for word in words if word.lower() != head][:80]
                    while sum(len(w) + 1 for w in synonyms) >= 1500:
                        synonyms.pop()
                    if not synonyms:
                        continue
                    sense_bytes = len(label) + sum(len(w) + 1 for w in synonyms) + 20
                    if len(senses) >= 26 or label_bytes + len(label) + 15 >= 1500 or record_bytes + sense_bytes >= 4000:
                        counts['omitted_senses_for_ui_limits'] += 1
                        continue
                    senses.append({'pos': name, 'label': label, 'synonyms': synonyms})
                    label_bytes += len(label) + 15
                    record_bytes += sense_bytes
    result = {head: senses for head, senses in sorted(result.items()) if senses}
    (OUT / 'EN.thesaurus.json').write_text(
        json.dumps(result, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
    counts['headwords'] = len(result)
    counts['senses'] = sum(len(senses) for senses in result.values())
    return dict(counts)


def self_check():
    """Check source transformations and rejection rules before generating files."""
    assert decode_moby_french("e'le`ve") == '\u00e9l\u00e8ve'
    assert decode_moby_french("garc/on") == 'gar\u00e7on'
    assert decode_moby_french("aujourd'hui") == "aujourd'hui"
    assert decode_moby_french("l'e'te'") == "l'\u00e9t\u00e9"
    assert decode_moby_french('aigue"') == 'aigu\u00eb'
    assert lexical_word('Stra\u00dfe') == 'Stra\u00dfe'
    assert lexical_word('3m') is None
    assert lexical_word('word.') is None
    assert synonym_text('ready_to_hand(p)') == 'ready to hand'
    assert synonym_text('Mr._Smith') is None


def main():
    """Build all normalized lexicons and a reproducible, machine-readable audit."""
    self_check()
    OUT.mkdir(parents=True, exist_ok=True)
    report = {}
    for locale, filename, encoding, transform in [
            ('EN_US', 'SCOWL-en_US.txt', 'utf-8', None),
            ('EN_GB', 'SCOWL-en_GB-ise.txt', 'utf-8', None),
            ('DE', 'german.dic', 'latin1', None),
            ('FR', 'moby-french.txt', 'ascii', decode_moby_french)]:
        report[locale] = normalize_plain(locale, RAW / filename, encoding, transform)
        print(locale, report[locale], flush=True)
    report['SV'] = normalize_swedish()
    print('SV', report['SV'], flush=True)
    report['EN_THS'] = wordnet_thesaurus()
    print('EN_THS', report['EN_THS'], flush=True)
    (OUT / 'lexicon-normalization-report.json').write_text(
        json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='ascii')


if __name__ == '__main__':
    main()
