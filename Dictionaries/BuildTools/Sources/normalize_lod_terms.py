#!/usr/bin/env python3
"""Normalize CC0 LOD and Swedish National Term Bank data for PC/GEOS.

Copyright 2026 PC/GEOS contributors. SPDX-License-Identifier: Apache-2.0

This host-side importer reads only the public sources in the adjacent lod and
rikstermbanken directories. It never reads the uploaded proprietary resources.
LOD spelling includes reviewed search forms and explicitly recorded inflections.
LOD synonyms retain the source sense boundaries. Translations are never used
to infer synonyms: even one source sense can list translations of contrasting
secondary headwords. German/French data use explicit TE/SYTE term relations.

Rikstermbanken imports only TE (preferred term) and SYTE (explicit synonym).
UPTE, related terms, explanatory prose and deprecated terms are not synonyms.
The resulting Swedish thesaurus covers specialist terminology, not everyday
vocabulary comprehensively. Source licenses and hashes accompany this script.
"""

import argparse
import collections
import importlib.util
import json
from pathlib import Path
import re
import unicodedata
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "normalized"
STATS = collections.Counter()
POS = {"SUBST": "noun", "NP": "noun", "VRB": "verb",
       "ADJ": "adjective", "ADV": "adverb"}


def clean(text):
    """Return NFC text with source layout whitespace collapsed."""
    return unicodedata.normalize("NFC", " ".join((text or "").split()))


def term(text, phrase=True):
    """Accept a plain lexical term, rejecting editorial punctuation and markup."""
    text = clean(text)
    allowed = "-\'\u2019 " if phrase else "-\'\u2019"
    return bool(text and any(c.isalpha() for c in text)
                and all(c.isalpha() or c in allowed for c in text))


def xml_zip(name):
    """Load one declared XML source without extracting arbitrary archive paths."""
    with zipfile.ZipFile(ROOT / "lod" / (name + ".zip")) as archive:
        members = [n for n in archive.namelist() if n.endswith(".xml")]
        if len(members) != 1:
            raise ValueError("Expected exactly one XML member in " + name)
        return ET.fromstring(archive.read(members[0]))


def add_sense(result, headword, synonyms, label, pos, key):
    """Append a bounded source sense, preserving earlier senses deterministically.

    PC/GEOS's legacy UI limits a replacement word to 26 characters. The binary
    builder performs the final GEOS-code-page validation. This early filter and
    conservative 3,400-character record budget leave space for binary lengths,
    prefixes and terminators in the 4-KB reader buffer.
    """
    headword = clean(headword)
    if not term(headword) or len(headword) > 26:
        STATS[key + "_headword_rejected"] += 1
        return
    values = []
    for value in synonyms:
        value = clean(value)
        if (value != headword and term(value) and len(value) <= 26
                and value not in values):
            values.append(value)
    if not values:
        return
    values = values[:40]
    label = clean(label)
    if len(label) > 72:
        label = label[:69].rsplit(" ", 1)[0] + "..."
    sense = {"pos": pos, "label": label, "synonyms": values}
    existing = result.setdefault(headword, [])
    if sense in existing:
        return
    cost = lambda item: len(item["label"]) + sum(len(v) + 1 for v in item["synonyms"]) + 16
    if len(existing) >= 16 or sum(map(cost, existing)) + cost(sense) > 3400:
        STATS[key + "_senses_over_legacy_limit"] += 1
        return
    existing.append(sense)
    STATS[key + "_senses"] += 1


def filter_thesaurus(data, encode_geos, key):
    """Remove only unrepresentable terms, preserving each surviving source sense.

    This calls the binary builder's actual GEOS codec. A missing character is
    never transliterated into a potentially different lexical form. If only a
    label is unrepresentable, use its already verified headword as the label;
    the audit counts that loss of explanatory detail separately.
    """
    filtered = {}
    for headword, senses in data.items():
        try:
            encode_geos(headword)
        except ValueError:
            STATS[key + "_geos_headwords_omitted"] += 1
            continue
        kept = []
        for sense in senses:
            synonyms = []
            for value in sense["synonyms"]:
                try:
                    encode_geos(value)
                    synonyms.append(value)
                except ValueError:
                    STATS[key + "_geos_synonyms_omitted"] += 1
            if not synonyms:
                STATS[key + "_geos_empty_senses_omitted"] += 1
                continue
            label = sense["label"]
            try:
                encode_geos(label)
            except ValueError:
                label = headword
                STATS[key + "_geos_labels_replaced_by_headword"] += 1
            kept.append(dict(sense, label=label, synonyms=synonyms))
        if kept:
            filtered[headword] = kept
        else:
            STATS[key + "_geos_empty_headwords_omitted"] += 1
    return filtered


def write_json(name, value):
    """Write deterministic UTF-8 JSON for the independent binary builder."""
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    indent=2) + "\n", encoding="utf-8")


def lod(encode_geos):
    """Build Luxembourgish forms and explicit source-sense synonym relations."""
    words = set()
    search = xml_zip("search")
    for spelling in search.iter("spelling"):
        if spelling.get("suggest") == "true" and term(spelling.text, False):
            words.add(clean(spelling.text))
        else:
            STATS["lb_unreviewed_or_phrase_search_forms_skipped"] += 1
    # Inflection tables deliberately contain multiword verb tenses. Keep only
    # explicitly written single forms; do not split phrases into guessed words.
    tables = xml_zip("tab")
    for element in tables.iter():
        if len(element) == 0 and term(element.text, False):
            words.add(clean(element.text))
    articles = xml_zip("art")
    result = {"LB": {}}
    for entry in articles.findall("entry"):
        lemma = clean(entry.findtext("lemma"))
        if term(lemma, False):
            words.add(lemma)
        for form in entry.findall(".//inflection/form"):
            for value in [form.text, form.get("nRuleForm")]:
                if term(value, False):
                    words.add(clean(value))
        for micro in entry.findall("microStructure"):
            pos = POS.get(micro.findtext("partOfSpeech"), "unknown")
            for meaning in micro.findall(".//meaning"):
                # Secondary headwords are idioms or subsenses. Do not attach
                # their alternatives to the bare entry's unrelated headword.
                head = clean(meaning.findtext("secondaryHeadword") or lemma)
                syns = [clean(v.text) for v in meaning.findall("synonyms/synonym")]
                number = meaning.findtext("number") or ""
                label = head + ((" (" + number + ")") if number else "")
                add_sense(result["LB"], head, syns, label, pos, "lb_thesaurus")
    (OUT / "LB.words.txt").write_text("\n".join(sorted(words)) + "\n", encoding="utf-8")
    STATS["lb_words"] = len(words)
    for language, senses in result.items():
        senses = filter_thesaurus(senses, encode_geos, language.lower() + "_thesaurus")
        write_json(language + ".thesaurus.json", senses)
        STATS[language.lower() + "_thesaurus_headwords"] = len(senses)
        STATS[language.lower() + "_thesaurus_output_senses"] = sum(map(len, senses.values()))


def rikstermbanken(encode_geos):
    """Import explicit Swedish/German/French term equivalents with source senses.

    A blank line separates NTRF records. Multiple TE/SYTE lines in one record
    name the same concept. UPTE can include discouraged terms or non-synonymous
    search aliases and is intentionally excluded. Translations from another
    language and related-term links never become synonyms.
    """
    result = {"sv": {}, "de": {}, "fr": {}}
    for path in sorted((ROOT / "rikstermbanken").glob("*.zip")):
        with zipfile.ZipFile(path) as archive:
            for name in sorted(archive.namelist()):
                if not name.endswith(".txt"):
                    continue
                text = archive.read(name).decode("utf-8-sig")
                for block in re.split(r"\r?\n\s*\r?\n", text):
                    fields = collections.defaultdict(list)
                    for line in block.splitlines():
                        match = re.match(r"^((?:sv|de|fr)(?:TE|SYTE|DF|SA|OKGR)) (.+)$", line)
                        if match:
                            fields[match.group(1)].append(clean(match.group(2)))
                    for language in result:
                        values = fields[language + "TE"] + fields[language + "SYTE"]
                        if len(set(values)) < 2:
                            continue
                        label = " / ".join(fields[language + "SA"] + fields[language + "DF"])
                        if not label:
                            label = " / ".join(values)
                        pos = "unknown"
                        grammar = " ".join(fields[language + "OKGR"]).lower()
                        for token, mapped in [("substantiv", "noun"), ("adjektiv", "adjective"),
                                              ("adverb", "adverb"), ("verb", "verb")]:
                            if token in grammar:
                                pos = mapped
                                break
                        for value in values:
                            add_sense(result[language], value, values, label, pos,
                                      language + "_thesaurus")
    for language, senses in result.items():
        senses = filter_thesaurus(senses, encode_geos, language + "_thesaurus")
        write_json(language.upper() + ".thesaurus.json", senses)
        STATS[language + "_thesaurus_headwords"] = len(senses)
        STATS[language + "_thesaurus_output_senses"] = sum(map(len, senses.values()))


def hyphenation():
    """Strip TeX comments/macros while retaining all literal Liang patterns.

    Only the four independently checked permissive files are read. US and UK
    English use separate data and the source-specified 2/3 minima. French and
    German use 2/2. Explicit TeX exception words remain separate JSON entries.
    """
    for source, output in [("en-us", "EN_US"), ("en-gb", "EN_GB"),
                           ("de-1996", "DE"), ("fr", "FR")]:
        text = (ROOT / "hyphen" / ("hyph-" + source + ".tex")).read_text(encoding="utf-8")
        text = re.sub(r"%[^\n]*", "", text)
        groups = re.findall(r"\\patterns\s*\{([^}]*)\}", text, flags=re.S)
        if not groups:
            raise ValueError("No literal pattern block: " + source)
        patterns = sorted(set(" ".join(groups).split()))
        if any("\\" in value or "{" in value for value in patterns):
            raise ValueError("Unsupported macro in patterns: " + source)
        (OUT / (output + ".patterns.txt")).write_text("\n".join(patterns) + "\n", encoding="utf-8")
        exceptions = {}
        for group in re.findall(r"\\hyphenation\s*\{([^}]*)\}", text, flags=re.S):
            for value in group.split():
                if "\\" in value:
                    raise ValueError("Unsupported macro in exceptions: " + source)
                parts = value.split("-")
                offsets = []
                offset = 0
                for part in parts[:-1]:
                    offset += len(part)
                    offsets.append(offset)
                exceptions["".join(parts)] = offsets
        write_json(output + ".hyp-exceptions.json", exceptions)
        STATS[output.lower() + "_patterns"] = len(patterns)
        STATS[output.lower() + "_hyp_exceptions"] = len(exceptions)


def main():
    """Create reproducible normalized inputs and machine-readable audit counts."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--builder", type=Path, default=ROOT.parent / "buildlex.py",
                        help="path to the release buildlex.py for strict GEOS encoding")
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location("spell_buildlex", args.builder)
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    OUT.mkdir(exist_ok=True)
    lod(builder.encode_geos)
    rikstermbanken(builder.encode_geos)
    hyphenation()
    write_json("lod-terms-normalization.json", dict(STATS))
    print(json.dumps(dict(STATS), sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
