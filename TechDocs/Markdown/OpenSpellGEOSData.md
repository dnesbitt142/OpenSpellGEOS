# OpenSpellGEOS language data

OpenSpellGEOS provides six spelling dictionaries, six thesaurus files and six
hyphenation files for the OpenSpellGEOS backend. It does not provide equally broad
linguistic coverage in every language. Luxembourgish automatic hyphenation is
unavailable. Swedish hyphenation covers verified compound boundaries only.
The German, French and Swedish thesauri cover specialist terminology. French
spelling uses an older public-domain vocabulary source. These limitations are
recorded in Data/buildset.json and the generated DICTS/BUILD.json.

The original replacement code is Apache-2.0. The linguistic inputs have the
separate permissive licenses or public-domain dedications described below.
Their conversion to a binary format does not remove upstream notices or change
upstream authorship. No word, synonym, definition or hyphenation point was taken
from the supplied proprietary language resources.

The 2026-09-30 corrective release changes runtime suggestion behavior and the
spelling dialog, while retaining every DCT/THS/HYP byte and every pinned input.
The complete data audit was repeated against the revised C reader; its current
log is corrective-data-audit.log. Existing installations need only the matching
updated Spell geode to obtain these fixes. Data build instructions below remain
valid without a format conversion.

# Compact selection and the 500000-byte limit

Each installed .DCT, .THS and .HYP must occupy no more than 500000 decimal
bytes, inclusive, counting its complete OLX1 container. The limit is per file,
not per language, and is not 500 KiB. .DCT remains the canonical spelling
extension. The format, runtime entry points and Library/Spell/Open directory
are unchanged by compact selection.

The large vocabulary and sense counts in the provenance sections below
describe the normalized source snapshots before compact selection. They are
not retained counts for the compact binaries. The new BUILD.json records
measured final sizes, hashes, retained records and omissions; only those
results establish the released compact coverage.

## Ranking inputs

Pinned UTF-8 priority files order candidates for each profile. The same
profile priority is used across its DCT, THS and HYP selection. Manually chosen
common/function words come first, followed by these source-specific signals:

- English uses historical WordNet tagged-occurrence counts, then untagged
  lemmas. Explicit exception forms and simple candidate relatives receive
  priority only when their exact spelling already exists in the wordlist.
- Swedish prioritizes enter_se membership, then observed speech/dictation
  sets, then teliabaseforms_se or LEX analyses. The source numeric frequency
  field is unused, and its field 31 is not treated as a reliable BASE marker.
- Luxembourgish uses token occurrence counts in LOD dictionary examples,
  then lemmas. Dictionary examples are not a general-language frequency corpus.
- German and French prioritize eligible LOD translation headwords and simple
  candidate relatives attested in the existing wordlists, then use length
  ordering. These are heuristic rankings, not measured German or French
  general-corpus frequencies. Candidate suffix probes never add new spellings
  and are not a morphological analysis engine.

The ordering only prioritizes candidates already admitted by the relevant
linguistic source, the explicitly authored supplement and encoding rules.
It does not invent accepted dictionary
entries or synonym relationships. In particular, using a translation headword
as a ranking signal does not make translations into thesaurus synonyms.
Data/buildset.json records each profile's priority file, priority_kind and
priority_source. Generated BUILD.json exposes these as ranking.file,
ranking.kind and ranking.source, with the priority SHA-256, ranked-key count
and fallback rule. The ranking source, license and SHA-256 must be retained
with the other pinned inputs.

If a profile has no priority file, the fallback prefers simple alphabetic
forms, then uses length and case ordering. That deterministic fallback is not
described as frequency data. Neither the pinned signals nor the fallback
substitute for native-language review of spelling, register, inflections,
modern usage or the consequences of the omissions.

## Selection and thesaurus compaction

The selector considers candidates in priority order and uses the exact OLX1
size estimator with a bounded binary search to choose a prefix that fits.
Front coding and block boundaries can make successive sizes nonmonotonic;
this is a bounded selection procedure, not a proof of the globally largest
possible record set. The final written file's measured size must agree with
the estimate and remain at or below the ceiling before the completed output
directory is published.

The compact thesaurus keeps at most two senses per headword and four synonyms
per retained sense. Labels are shortened at whole-word boundaries to at most
48 GEOS bytes, including a GEOS ellipsis when shortened. If the first complete
token cannot fit, the first retained original synonym supplies the heading;
the tool does not invent a definition. Senses are prioritized using their best
retained synonym, with source order breaking ties. The selection prefers a
known, different part of speech for the second sense when available. These
are release selection rules, narrower than the unchanged runtime format
limits. No new synonym is constructed to fill a shorter record.

HYP generation starts only from the folded selected DCT vocabulary. It drops
rows with no accepted break and applies the same per-file budget selection.
A selected DCT word can therefore still have no HYP result because its source
defines no break or because its HYP row was omitted to fit. The unavailable
Luxembourgish HYP source remains unavailable; the size limit does not address
that gap.

The compact corpus loses rare vocabulary, specialist terms, inflections and
senses compared with the full normalized sources. A correct omitted spelling
can be reported as unknown. An omitted THS headword has no lookup result, and
an omitted HYP record supplies no automatic line break. The ranking is a
practical prioritization within a fixed disk budget, not an assurance that
every common word or important sense has been retained.

## Verified compact measurements

These values come from the released compact BUILD.json. The independent
release audit decoded all 611,367 records, checked all eighteen file hashes
and payloads, confirmed the inclusive 500000-byte ceiling and queried the
actual data through the C reader. It also reproduced compact EN_GB.DCT
byte-for-byte from the pinned inputs. The evidence is recorded in
compact-data-validation.log; these are host data checks, not GUI acceptance
checks or native-language editorial review.

<!-- COMPACT_METRICS_BEGIN -->

| File | Candidate records | Retained records | Omitted records | Complete bytes |
| --- | ---: | ---: | ---: | ---: |
| EN_US.DCT | 109,140 | 61,720 | 47,420 | 499,915 |
| EN_US.THS | 60,165 | 4,518 | 55,647 | 499,094 |
| EN_US.HYP | 43,330 | 43,330 | 0 | 407,350 |
| EN_GB.DCT | 108,778 | 61,763 | 47,015 | 499,915 |
| EN_GB.THS | 60,165 | 4,525 | 55,640 | 499,983 |
| EN_GB.HYP | 41,924 | 41,924 | 0 | 395,371 |
| DE_DE.DCT | 2,152,637 | 61,535 | 2,091,102 | 499,915 |
| DE_DE.THS | 3,744 | 3,744 | 0 | 258,145 |
| DE_DE.HYP | 58,563 | 53,942 | 4,621 | 499,915 |
| SV_SE.DCT | 816,350 | 59,881 | 756,469 | 499,915 |
| SV_SE.THS | 8,922 | 6,364 | 2,558 | 498,933 |
| SV_SE.HYP | 17,696 | 17,696 | 0 | 168,859 |
| LB_LU.DCT | 116,235 | 54,530 | 61,705 | 499,915 |
| LB_LU.THS | 7,250 | 7,250 | 0 | 337,014 |
| LB_LU.HYP | 0 | 0 | 0 | 64 |
| FR_FR.DCT | 138,188 | 67,335 | 70,853 | 499,915 |
| FR_FR.THS | 2,443 | 2,443 | 0 | 183,831 |
| FR_FR.HYP | 58,867 | 58,867 | 0 | 486,847 |

<!-- COMPACT_METRICS_END -->

The eighteen linguistic files total 7,234,896 decimal bytes. Candidate counts
are the encoded, canonicalized records presented to each file selector, not
the larger raw-source line counts. THS candidates have already passed sense
compaction; HYP candidates already belong to the selected DCT vocabulary and
have at least one legal break. Zero HYP budget omissions therefore does not
mean every source dictionary word can be hyphenated.

The retained thesaurus totals are:

| Profile | Retained senses | Retained synonym occurrences |
| --- | ---: | ---: |
| EN_US | 7,425 | 16,489 |
| EN_GB | 7,448 | 16,512 |
| DE_DE | 3,974 | 4,667 |
| SV_SE | 7,144 | 8,417 |
| LB_LU | 8,327 | 10,957 |
| FR_FR | 2,587 | 3,028 |

Synonym occurrences count alternatives within retained senses, not distinct
words across the file. BUILD.json supplies each final SHA-256, source and
candidate sense/synonym counts, priority coverage, and DCT/HYP vocabulary
metadata. File.selection records policy, candidate_records,
ranking_considered, selected_records, omitted_records, priority_hit_records,
max_bytes and estimated_bytes. The report also identifies the OpenSpellGEOS
project, max_file_bytes, profile ranking metadata and THS compaction rules.

Compact source checks include the Swedish basic-word supplement. A current
Swedish THS audit sample is arbete, with the source sense mekaniskt arbete.
The earlier full-corpus A-bock sample was omitted by compact selection; hus
is absent from the underlying THS source and is not claimed as supported.

# Release layout

Paths below are relative to the OpenSpellGEOS repository root unless another
working directory is stated. Dictionaries contains six language ZIPs, each
holding a language folder with its DCT, THS, HYP and GDI files. BUILD.json,
NOTICES.TXT and LICENSES accompany the archives. Keep the supplied archives
and notices intact when rebuilding into a separate output directory.

Dictionaries/BuildTools/Data.zip contains a top-level Data directory. After
extraction beside the archive, Dictionaries/BuildTools/Data contains the
normalized UTF-8 source snapshots, six priority lists, compact-priority-
report.json, the authored compact-core-words.json and SV.core-supplement.txt,
and buildset.json. Every consumed input has a SHA-256 entry in that manifest.
Dictionaries/BuildTools/build_languages.py verifies all recorded inputs before
building. A changed input is an error; the build never silently accepts it.

Dictionaries/BuildTools/Sources contains the acquisition and normalization
helpers, the three upstream provenance manifests, source documentation, full
notices in licenses/ and lexicons/, and the source-boundary regression checks.
Large raw upstream archives are excluded from the release. The helpers fetch
those exact archives when reproducing the normalized snapshots. Ordinary
binary rebuilding uses Data and the bundled Sources notices and does not
require network access.

All installed DCT, THS, HYP and GDI files belong in USERDATA/DICTS. GDI records
register the profiles in Preferences. The file-format and integration details
are in OpenSpellGEOS.md. Keep the source notices with every redistributed linguistic
data set, including a distribution that contains only the compiled DICTS files.
Use a LICENSES directory alongside that set or an equivalent accompanying
license document; do not distribute the notice-bearing binaries alone.

# Source provenance before compact selection

EN_US.DCT uses the English Speller Database, formerly SCOWL, American list.
EN_GB.DCT uses its separate British -ise list. Both are pinned to commit
7f2f4078354752045ee16a041605686561122185 in en-wl/wordlist-diff. The normalized
inputs contain 109,140 and 108,778 forms respectively. Preserve
Sources/lexicons/SCOWL-Copyright. Its explicit permission covers generated
speller wordlists. Neither Australian data nor the larger advanced-cryptics
wordlists are selected. The complete upstream notice is retained.

EN_US.THS and EN_GB.THS use the same Princeton WordNet 3.1 synsets. Only members
of one synset become alternatives; antonyms, hypernyms and other relations are
excluded. The normalized input contains 60,165 headwords and 90,196 senses.
WordNet is primarily American English; the shared thesaurus does not rewrite
alternatives into regional spellings. Preserve the complete
Sources/lexicons/WordNet-3.1-LICENSE.txt, including Princeton's copyright,
disclaimer and restriction on promotional use of its name.

EN_US.HYP uses Gerard D.C. Kuiken's American English patterns and explicit
exceptions. Its grant permits copying, distribution and modification with the
copyright and permission notices retained. Preserve Sources/licenses/hyph-en-us.txt.
EN_GB.HYP uses the MIT-licensed British patterns of Dominik Wujastyk and Graham
Toal; preserve Sources/licenses/hyph-en-gb.txt. The original OUP training
wordlist mentioned in that notice is not downloaded, used or distributed.
Only the separately permissively licensed published patterns are imported.
Both English profiles require two letters before and three after a break.
British and American patterns remain distinct.

DE_DE.DCT uses Jan Schreiber's Free German Dictionary, german.dic from the
2021-10-01 german.7z archive. The maintainer declares the project public domain.
The source contains 2,152,638 entries; the normalizer omits one 65-character word
that exceeds the binary format's 64-character limit, leaving 2,152,637 entries.
The deliberately nonstandard variants.dic is excluded. Preserve the source
attribution in Sources/lexicons/German-Public-Domain.txt. The large explicit-form
list takes more disk space than a compact stem dictionary; it is not loaded
wholesale into target RAM and does not generate new compounds at runtime.

DE_DE.THS uses the German TE/SYTE terminology records in the CC0 portion of
Sweden's National Term Bank. It contains 3,768 normalized headwords before the
builder's GEOS case-fold collision merging. It is a specialist thesaurus.
DE_DE.HYP uses the MIT-licensed German reformed-orthography patterns dated
2024-02-28, by the Deutschsprachige Trennmustermannschaft. Preserve
Sources/licenses/hyph-de-1996.txt. The minimum on each side is two letters.

SV_SE.DCT uses the National Library of Norway's CC0 Swedish NST pronunciation
lexicon, produced in 2003. Written forms are extracted without using phonetic
transcriptions to infer spellings. Explicit GARB rows and malformed lexical
forms are removed, leaving 816,336 distinct forms. The upstream lexicon includes
some automatically generated material and is not a hand-proofread modern
spelling dictionary. Preserve Sources/lexicons/NST-CC0-NOTICE.txt and the CC0 text.

SV.core-supplement.txt separately contributes 14 manually reviewed basic words
absent from that NST snapshot: det, i, som, på, den, av, de, efter, alla,
någon, detta, där, få and bra. This small authored supplement is Apache-2.0;
it is not attributed to NST. The profile's word_supplement field merges it
before ranking and compact selection, with its own pinned SHA-256. No
hyphenation is inferred for these added words. The original NST source count
above excludes the supplement.

SV_SE.THS uses the Swedish TE/SYTE records in the same CC0 National Term Bank
release, with 8,963 normalized headwords after strict GEOS character filtering.
It is a specialist thesaurus. One unsupported synonym containing U+010D is
omitted, its now-empty sense/headword is removed, and the reverse unsupported
headword is removed. Other senses and alternatives are retained.

SV_SE.HYP uses 321,017 exact compound-boundary exception records from NST.
All orthographic components must have at least two letters and concatenate to
the surface spelling apart from case. Duplicate analyses intersect accepted
breaks. Linking letters, spelling alternations, overlapping letters and SAMPA
syllables are not guessed into break positions. The minimum on each side is two
letters. ATTENTION: simple-word syllable breaks and breaks within compound
components are unavailable. A reviewed permissive pattern corpus is needed to
provide general Swedish hyphenation.

LB_LU.DCT uses the CC0 LOD articles, search index and inflection tables from the
Zenter fir d'Letzebuerger Sprooch, snapshot 2026-07-27. It contains 116,235
normalized forms. The importer accepts reviewed suggest=true spellings,
headwords, explicit inflections and recorded nRuleForm alternatives. It excludes
automatically generated suggest=false search aliases and does not split phrases
into guessed words. The resulting spelling checker cannot decide whether an
accepted n-rule form is grammatically appropriate in the surrounding sentence.

LB_LU.THS uses explicit LOD synonym elements attached to one source meaning,
with 7,282 normalized headwords before GEOS case-fold collision merging. It does
not infer links through a common translation or transitive synonym chain. The
legacy UI cannot expose every original lexical-register annotation.

LB_LU.HYP is an empty, valid no-break file. ATTENTION: no suitably licensed
Luxembourgish orthographic hyphenation corpus was acquired. LOD pronunciation
is not a source of written hyphenation positions. This profile does not silently
reuse German patterns or claim complete Luxembourgish hyphenation. Adding a
reviewed permissive exception lexicon or pattern set is the remaining data work.
The empty generated container contains no third-party linguistic content.

FR_FR.DCT uses Grady Ward's Moby Language II French list, dedicated to the public
domain by its author in January 2001. Explicit postfix accent notation is decoded
into Unicode; consonant apostrophes are preserved. Invalid punctuation rows are
reported and excluded, leaving 138,188 forms. The source is historical and needs
native-language review before being represented as current editorial-quality
French coverage. Preserve Sources/lexicons/Moby-Public-Domain.txt. Project
Gutenberg's branding is not part of the lexical binary output.

FR_FR.THS uses French TE/SYTE records in the CC0 National Term Bank release,
with 2,443 normalized headwords. It is a specialist thesaurus. FR_FR.HYP uses the
MIT-licensed French V2.13 patterns dated 2016-05-12, by Daniel Flipo, Bernard
Gaulle and Arthur Reutenauer. Preserve Sources/licenses/hyph-fr.txt. The minimum
on each side is two letters.

# Shared source-selection rules

The National Term Bank release combines its public-administration, TNC and
Swedish computer-terminology archives. Only preferred terms (TE) and explicit
synonyms (SYTE) in the same language and concept record become alternatives.
UPTE aliases, discouraged terms, related terms and cross-language translations
are excluded. Many records are technical or historical; abbreviations and
expanded forms are valid term equivalents within their source concept.

LOD translations were considered and rejected as thesaurus input: a single
meaning can contain translations of contrasting secondary headwords, such as
Old Testament and New Testament. Sharing that container does not make them
synonyms. A regression check prevents reintroducing that error.

All HYP lookup files precompute the accepted break positions for words in the
profile's selected dictionary, subject to the HYP file's own budget. The target
does not execute the pattern-matching algorithm.
An absent word returns no break even if the upstream pattern set could hyphenate
it. Rebuild HYP after changing DCT vocabulary. This bounded lookup trades disk
space and host build time for a small, predictable target implementation.

No GPL, LGPL, EUPL, CC-BY-SA, CC-BY, MPL or LPPL linguistic data is selected.
The Apache Software Foundation's third-party policy lists permissive MIT/BSD
and public-domain/CC0 material as acceptable categories. Each actual input was
checked separately; a converter's or repository's top-level license was not
assumed to cover every included language resource.

Primary source and licensing references:

- https://github.com/en-wl/wordlist-diff/blob/7f2f4078354752045ee16a041605686561122185/Copyright
- https://wordnet.princeton.edu/license-and-commercial-use
- https://sourceforge.net/projects/germandict/
- https://www.gutenberg.org/cache/epub/3206/pg3206-images.html
- https://www.nb.no/sprakbanken/ressurskatalog/en/oai-nb-no-sbr-22/
- https://data.public.lu/en/datasets/letzebuerger-online-dictionnaire-lod-linguistesch-daten/
- https://data.public.lu/en/datasets/letzebuerger-online-dictionnaire-lod-index-vun-der-sich-funktioun/
- https://data.public.lu/en/datasets/letzebuerger-online-dictionnaire-lod-flexiounstabellen/
- https://researchdata.se/en/catalogue/dataset/2026-140
- https://github.com/hyphenation/tex-hyphen/tree/master/hyph-utf8/tex/generic/hyph-utf8/patterns/tex
- https://www.apache.org/legal/resolved.html

The manifests record exact archive URLs, byte sizes, SHA-256 fingerprints and
license evidence. Website evidence pages are not themselves asserted to be
CC0 merely because they describe a CC0 dataset. Bulky unrelated website markup
and large raw upstream archives are excluded from the release.

# Rebuilding installed files offline

From the OpenSpellGEOS repository root, extract the bundled snapshot once:

    python3 -m zipfile -e Dictionaries/BuildTools/Data.zip Dictionaries/BuildTools

This creates Dictionaries/BuildTools/Data. If that directory already exists,
keep it intact and omit extraction. Choose an output directory that does not
exist; use a separate directory rather than the supplied Dictionaries folder:

    python3 Dictionaries/BuildTools/build_languages.py --output build/OpenSpellGEOS/DICTS --max-bytes 500000

The command uses Dictionaries/BuildTools/Data by default. It verifies every
input, builds into staging, then exposes the completed set. It refuses to
overwrite an existing output directory. --max-bytes defaults to 500000; values
from 64 through 500000 are accepted, and values above the ceiling are
rejected. A lower limit selects a smaller corpus; it does not change the
format or improve coverage. The resulting BUILD.json records installed counts,
file sizes, file hashes, input hashes and coverage declarations. Use these
installed counts when describing the binary release; source counts can differ
because canonical keys merge during case folding and the compact selector
omits records to satisfy the per-file byte budget.

# Reproducing normalized snapshots from upstream

The host needs Python 3 and 7z, 7zz or bsdtar for the German source archive.
The other archives are read with Python's standard library. This work can use
hundreds of megabytes of host memory and is not intended for a 286.

From Dictionaries/BuildTools/Sources run:

    python3 fetch_lexicons.py
    python3 fetch_sources.py
    python3 normalize_lexicons.py
    python3 normalize_lod_terms.py --builder ../buildlex.py
    python3 check_normalization.py

The fetch helpers reuse matching cached files and reject changed bytes. Place a
trusted, hash-matching archive at its recorded path if an upstream URL disappears.
The source-specific omission counts are written alongside the normalized files.
The THS filter uses the actual release builder's GEOS codec. It removes only an
unsupported alternative, then any sense or headword left empty. If only a label
is unsupported, its already-validated headword becomes the label and this loss
of explanatory detail is counted. No replacement spelling is invented.

To reproduce both normalization and ranking into a separate Data directory,
return to Dictionaries/BuildTools and run the following. Normalized files come
from Sources/normalized. Authored priority seeds and the Swedish supplement
come from the shipped Data snapshot; they are maintained source inputs, not
outputs of an upstream normalizer. Derived priority lists and their report are
rebuilt in the next step. All copied inputs are checked before any copy is
made, and the shipped buildset.json is preserved exactly:

    python3 - <<'PY'
    import hashlib
    import json
    from pathlib import Path
    import shutil

    original = Path('Data')
    generated = Path('Sources/normalized')
    destination = Path('Data-reproduced')
    spec = json.loads((original / 'buildset.json').read_text())
    authored = {'compact-core-words.json', 'SV.core-supplement.txt'}
    copied = {}
    for name, expected in spec['sha256'].items():
        if name.endswith('.priority.txt') or name == 'compact-priority-report.json':
            continue
        source = (original if name in authored else generated) / name
        actual = hashlib.sha256(source.read_bytes()).hexdigest()
        if actual != expected:
            raise SystemExit('Reproduction differs: ' + name)
        copied[name] = source
    destination.mkdir()
    for name, source in copied.items():
        shutil.copyfile(source, destination / name)
    shutil.copyfile(original / 'buildset.json', destination / 'buildset.json')
    PY

Build the six ranked UTF-8 lists and compact-priority-report.json from the
already normalized words and verified upstream archives:

    python3 Sources/make_priorities.py --raw Sources --data Data-reproduced

The standard fetch helpers place lexicons/ and lod/ beneath Sources, so that
directory is the raw root in this example. An independently stored raw root
can be supplied instead; it must preserve those subdirectories and contain
the exact archives named in the provenance manifests. The priority generator
verifies WordNet, NST and LOD archive hashes and the normalized word/supplement
hashes. It reports absent seed words instead of inventing dictionary entries.
Its report records the ranking source, ranked words, missing seeds and hashes.

Check every reproduced input, including those new ranking outputs, against
the unchanged release manifest before building:

    python3 - <<'PY'
    import hashlib
    import json
    from pathlib import Path

    data = Path('Data-reproduced')
    spec = json.loads((data / 'buildset.json').read_text())
    for name, expected in spec['sha256'].items():
        actual = hashlib.sha256((data / name).read_bytes()).hexdigest()
        if actual != expected:
            raise SystemExit('Reproduction differs: ' + name)
    print('All normalized and ranking inputs match the release manifest.')
    PY

Then build the verified reproduction into another new directory:

    python3 build_languages.py --data Data-reproduced --output DICTS-reproduced

Do not fix an unexpected mismatch by overwriting the stored checksum. First
identify whether the source, normalizer, encoding rules or omission policy
changed. The original Data snapshot remains sufficient for offline rebuilding.

# Maintaining an intentionally changed source release

Run this maintenance workflow from Dictionaries/BuildTools, with the shipped
Data snapshot already extracted and Sources/normalized already regenerated. It
describes an optional future data update, not a requirement to rebuild the
current release.

Updating source data is a deliberate maintenance change, not a checksum repair.
Before accepting new input, review its authoritative license and provenance,
retain any changed notices, inspect vocabulary/sense differences and omission
reports, and repeat the source-boundary and binary checks. Record that review in
the change log. A data update must not change a profile's coverage declaration
without evidence that the claimed gap has actually been addressed.

After the maintainer has reviewed and accepted the new source licenses and the
normalization changes, regenerate Sources/normalized as above. Update the
explicit upstream provenance manifests when intentionally changing an archive;
the priority generator must still verify the selected raw sources. The
following command copies the already reviewed normalized candidates and the
current authored inputs to Data-review. It writes an isolated draft buildset
with the new normalized hashes so the priority generator can validate its
inputs. It does not alter active Data/buildset.json or publish a release:

    python3 - <<'PY'
    import hashlib
    import json
    from pathlib import Path
    import shutil

    original = Path('Data')
    generated = Path('Sources/normalized')
    candidate = Path('Data-review')
    spec = json.loads((original / 'buildset.json').read_text())
    authored = {'compact-core-words.json', 'SV.core-supplement.txt'}
    candidate.mkdir()
    for name, previous in list(spec['sha256'].items()):
        if name.endswith('.priority.txt') or name == 'compact-priority-report.json':
            continue
        source = (original if name in authored else generated) / name
        current = hashlib.sha256(source.read_bytes()).hexdigest()
        shutil.copyfile(source, candidate / name)
        spec['sha256'][name] = current
        if current != previous:
            print(name, previous, '->', current)
    (candidate / 'buildset.json').write_text(
        json.dumps(spec, indent=2, sort_keys=True) + '\n')
    PY

If changing authored seeds or the Swedish supplement, review those exact edits
separately, apply them only in Data-review at this stage, and update their
explicit draft hashes. Regenerate ranking from the reviewed raw sources:

    python3 Sources/make_priorities.py --raw Sources --data Data-review

Record all regenerated hashes in a proposed manifest, leaving the draft and
active release manifests unchanged:

    python3 - <<'PY'
    import hashlib
    import json
    from pathlib import Path

    candidate = Path('Data-review')
    spec = json.loads((candidate / 'buildset.json').read_text())
    for name, previous in list(spec['sha256'].items()):
        current = hashlib.sha256((candidate / name).read_bytes()).hexdigest()
        spec['sha256'][name] = current
        if current != previous:
            print(name, previous, '->', current)
    (candidate / 'buildset.proposed.json').write_text(
        json.dumps(spec, indent=2, sort_keys=True) + '\n')
    PY

Inspect the explicit manifest diff and the corresponding source/report changes:

    diff -u Data/buildset.json Data-review/buildset.proposed.json

Only after that maintenance review, activate the proposed manifest in the
isolated candidate directory and build it:

    mv Data-review/buildset.proposed.json Data-review/buildset.json
    python3 build_languages.py --data Data-review --output DICTS-review

Replacing active release snapshots and binaries is a separate reviewed change.
If a new source requires additional inputs or changed profile metadata, update
those specific manifest entries and documentation explicitly; the snippet above
preserves the current input list and does not guess new files or language IDs.
