#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Derive reproducible OpenSpellGEOS vocabulary priorities from pinned sources.

This is an offline host tool. It never adds dictionary spellings: every ranked
word must already occur in a normalized input or authored supplement. Core words
come first; source attestations or reviewed headwords then guide selection.
These heterogeneous signals are NOT a multilingual corpus-frequency ranking.
The output files are ordinary UTF-8 ranked word lists, read by compactlex.py.
The full source licenses continue to apply to the derived selection material.
"""

import argparse
from collections import Counter
import hashlib
import io
import json
from pathlib import Path
import re
import tarfile
import unicodedata
import xml.etree.ElementTree as ET
import zipfile


def checksum(path):
    """Hash a pinned source incrementally without another full memory copy."""
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(65536), b""):
            result.update(block)
    return result.hexdigest()


def verified_sources(raw, source_directory):
    """Verify the three archives used here against the existing source manifests."""
    lexicons = json.loads((source_directory / "lexicon-provenance.json").read_text())
    other = json.loads((source_directory / "sources-hyphen-lod.json").read_text())
    expected = {"lexicons/" + item["file"]: item["sha256"]
                for item in lexicons["downloads"]}
    expected.update({item["path"]: item["sha256"] for item in other})
    selected = {}
    for name in ("lexicons/wn3.1.dict.tar.gz", "lexicons/sv.leksikon.tar.gz",
                 "lod/art.zip"):
        if checksum(raw / name) != expected[name]:
            raise ValueError("pinned source checksum mismatch: " + name)
        selected[name] = expected[name]
    return selected


def add_priority(ranks, candidates, word, score):
    """Keep the strongest attestation for an existing, exactly spelled word."""
    word = unicodedata.normalize("NFC", word)
    if word in candidates and (word not in ranks or score < ranks[word]):
        ranks[word] = score


def family_candidates(word, language):
    """Suggest priority relatives, never new lexical entries or spelling rules.

    ATTENTION: these are simple candidate probes, not morphological analysis.
    Only exact hits in the already validated source dictionary survive. Their
    purpose is to avoid displacing everyday inflections with rare headwords.
    Explicit WordNet exception forms are handled separately for English.
    """
    forms = set()
    if language == "EN":
        forms.update(word + suffix for suffix in ("s", "es", "ed", "ing", "er", "est", "'s"))
        if word.endswith("y"):
            forms.update(word[:-1] + suffix for suffix in ("ies", "ied", "ier", "iest"))
        if word.endswith("e"):
            forms.update(word + suffix for suffix in ("d", "r", "st"))
            forms.add(word[:-1] + "ing")
        if (len(word) > 2 and word[-1] not in "aeiouwxy" and
                word[-2] in "aeiou" and word[-3] not in "aeiou"):
            forms.update(word + word[-1] + suffix for suffix in ("ed", "ing", "er", "est"))
        if "ize" in word:
            forms.add(word.replace("ize", "ise"))
    elif language == "DE":
        forms.update(word + suffix for suffix in ("e", "en", "er", "es", "em", "n", "s"))
        if word.endswith("en"):
            forms.update(word[:-2] + suffix for suffix in ("e", "st", "t", "te", "ten"))
    elif language == "FR":
        forms.update(word + suffix for suffix in ("s", "e", "es", "x"))
        if word.endswith("er"):
            forms.update(word[:-2] + suffix for suffix in
                         ("e", "es", "ons", "ez", "ent", "ais", "ait", "aient", "era", "eront"))
    return forms


def core_priorities(words, candidates, ranks, language):
    """Prefer authored essentials and source-attested simple relatives; log misses."""
    missing = []
    for position, word in enumerate(words):
        # Existing lowercase entries permit capitalized runtime matches. Do
        # not invent an exact-case entry where that accepted form already fits.
        candidate = word if word in candidates else word.lower()
        if candidate not in candidates:
            missing.append(word)
        add_priority(ranks, candidates, candidate, (0, position, 0))
        for related in family_candidates(word, language):
            add_priority(ranks, candidates, related, (1, position, 1))
    return missing


def wordnet_priorities(raw):
    """Read historical semantic tag counts and explicit English inflection pairs."""
    counts = Counter()
    exceptions = {}
    with tarfile.open(raw / "lexicons/wn3.1.dict.tar.gz", "r:gz") as archive:
        with io.TextIOWrapper(archive.extractfile("dict/index.sense"), encoding="ascii") as stream:
            for line in stream:
                key, _offset, _sense, count = line.split()
                lemma = key.split("%", 1)[0].replace("_", " ")
                counts[lemma] += int(count)
        for part in ("noun", "verb", "adj", "adv"):
            with io.TextIOWrapper(archive.extractfile("dict/" + part + ".exc"),
                                  encoding="ascii") as stream:
                for line in stream:
                    fields = line.split()
                    for lemma in fields[1:]:
                        exceptions.setdefault(lemma, set()).add(fields[0])
    return counts, exceptions


def english_priorities(candidates, ranks, counts, exceptions):
    """Prefer tagged lemmas and their attested relatives, then untagged lemmas."""
    for word, count in counts.items():
        tier = 2 if count else 4
        add_priority(ranks, candidates, word, (tier, -count, 0))
        for related in family_candidates(word, "EN") | exceptions.get(word, set()):
            add_priority(ranks, candidates, related, (tier, -count, 1))


def swedish_priorities(raw, candidates, ranks):
    """Use NST source-set membership; its numeric frequency field is unused.

    enter_se is a frequency-selected reference set, not an ordered frequency
    list. Speech/dictation sets and LEX analyses precede generated-only forms.
    Proper-name datasets are deliberately left to the ordinary fallback.
    Field 31 is not a reliable BASE marker in this snapshot: source lexical
    entries can also say INFLECTED. Source-set and LEX flags are used instead.
    """
    member = "NST svensk leksikon/swe030224NST.pron/swe030224NST.pron"
    observed = {"dictatraining_se", "dictatest_se", "asrtraining_se", "spd_se", "spdnew_se"}
    with tarfile.open(raw / "lexicons/sv.leksikon.tar.gz", "r:gz") as archive:
        with io.TextIOWrapper(archive.extractfile(member), encoding="latin1") as stream:
            for line in stream:
                fields = line.rstrip("\r\n").split(";")
                if len(fields) != 51 or fields[7] == "GARB" or "PM" in fields[1].split("|"):
                    continue
                sets = set(fields[29].split("|"))
                if "enter_se" in sets:
                    tier = 2
                elif observed & sets:
                    tier = 3
                elif "teliabaseforms_se" in sets or "LEX" in fields[5].split("|"):
                    tier = 4
                else:
                    continue
                add_priority(ranks, candidates, fields[0], (tier, 0, 0))


def lod_signals(raw):
    """Read Luxembourgish example attestations and reviewed translation headwords.

    Only Luxembourgish example text supplies counts. German/French translation
    headwords are a coverage heuristic; neither translations nor their number
    are presented as native-language frequency measurements. Translations are
    used to rank existing dictionary spellings, never to create synonyms.
    """
    with zipfile.ZipFile(raw / "lod/art.zip") as archive:
        names = [name for name in archive.namelist() if name.endswith(".xml")]
        if len(names) != 1:
            raise ValueError("expected one LOD article XML member")
        root = ET.fromstring(archive.read(names[0]))
    counts = Counter()
    lemmas = set()
    translations = {"DE": set(), "FR": set()}
    for entry in root.findall("entry"):
        for lemma in entry.findall("lemma"):
            text = "".join(lemma.itertext()).strip()
            lemmas.add(text)
        for text in entry.findall(".//examples/example/text"):
            for token in text.iter():
                if token.tag not in ("word", "inflectedHeadword"):
                    continue
                value = "".join(token.itertext()).strip()
                value = re.sub(r"^[^\w]+|[^\w]+$", "", value)
                if value:
                    counts[value] += 1
        for target in entry.findall(".//targetLanguage"):
            language = target.get("lang", "").upper()
            if language in translations:
                for translation in target.findall("translation"):
                    translations[language].add(" ".join("".join(translation.itertext()).split()))
    return counts, lemmas, translations


def build_priorities(raw, data):
    """Write six ranked inputs and a transparent, reproducible selection report."""
    source_directory = Path(__file__).resolve().parent
    sources = verified_sources(raw, source_directory)
    seeds = json.loads((data / "compact-core-words.json").read_text(encoding="utf-8"))["words"]
    spec = json.loads((data / "buildset.json").read_text(encoding="utf-8"))
    counts, exceptions = wordnet_priorities(raw)
    lod_counts, lod_lemmas, translations = lod_signals(raw)
    descriptions = {
        "EN": "Authored essentials; historical WordNet semantic tag counts and attested inflection relatives; remaining WordNet lemmas.",
        "SV": "Authored essentials; NST enter_se membership; observed speech/dictation source sets; lexical source analyses. No numeric frequency ranking.",
        "LB": "Authored essentials; LOD dictionary-example token attestations; reviewed LOD lemmas. Examples are not a general-language corpus.",
        "DE": "Authored essentials and attested relatives; existing words also present as reviewed LOD German translation headwords, then attested relatives. Heuristic, not native corpus frequency.",
        "FR": "Authored essentials and attested relatives; existing words also present as reviewed LOD French translation headwords, then attested relatives. Heuristic, not native corpus frequency."
    }
    report = {"project": "OpenSpellGEOS", "version": 1, "sources": sources,
              "seed_sha256": checksum(data / "compact-core-words.json"), "profiles": []}
    for profile in spec["profiles"]:
        stem = profile["stem"]
        language = stem[:2]
        word_path = data / profile["words"]
        if checksum(word_path) != spec["sha256"][profile["words"]]:
            raise ValueError("normalized input checksum mismatch: " + word_path.name)
        candidates = set(word_path.read_text(encoding="utf-8").splitlines())
        if profile.get("word_supplement"):
            supplement = data / profile["word_supplement"]
            if checksum(supplement) != spec["sha256"][supplement.name]:
                raise ValueError("supplement checksum mismatch: " + supplement.name)
            candidates.update(line.strip() for line in supplement.read_text(encoding="utf-8").splitlines()
                              if line.strip() and not line.startswith("#"))
        ranks = {}
        missing = core_priorities(seeds[language], candidates, ranks, language)
        if language == "EN":
            english_priorities(candidates, ranks, counts, exceptions)
        elif language == "SV":
            swedish_priorities(raw, candidates, ranks)
        elif language == "LB":
            for word, count in lod_counts.items():
                add_priority(ranks, candidates, word, (2, -count, 0))
            for word in lod_lemmas:
                add_priority(ranks, candidates, word, (3, 0, 0))
        else:
            for word in translations[language]:
                add_priority(ranks, candidates, word, (3, 0, 0))
                for related in family_candidates(word, language):
                    add_priority(ranks, candidates, related, (3, 0, 1))
        ranked = sorted(ranks, key=lambda word: (ranks[word], len(word), word.casefold(), word))
        output = data / (stem + ".priority.txt")
        output.write_text("\n".join(ranked) + "\n", encoding="utf-8")
        report["profiles"].append({"stem": stem, "priority": output.name,
                                   "priority_kind": "source-guided-heuristic",
                                   "priority_source": descriptions[language],
                                   "ranked_words": len(ranked), "sha256": checksum(output),
                                   "missing_core_seeds": missing})
        print(stem + ": " + str(len(ranked)) + " priorities; " + str(len(missing)) + " absent seeds")
    (data / "compact-priority-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="ascii")
    return report


def main():
    """Require explicit raw/data locations and report input errors without downloads."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--data", type=Path, required=True)
    args = parser.parse_args()
    try:
        build_priorities(args.raw.resolve(), args.data.resolve())
    except (OSError, KeyError, ValueError) as error:
        parser.exit(2, "make_priorities: %s\n" % error)


if __name__ == "__main__":
    main()
