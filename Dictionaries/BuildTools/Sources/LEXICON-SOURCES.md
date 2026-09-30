# OpenSpellGEOS dictionary and English thesaurus sources

The Apache-2.0 host tools produce data from the separately licensed sources
below. Keep all corresponding notices in the distribution. "Compatible" means
these permissive grants allow use and redistribution alongside Apache-2.0
code; it does not mean the upstream works have been relicensed Apache-2.0.
No attached proprietary language file supplied any word, synonym, affix,
pattern, definition or pronunciation used here.

# Rebuild

These are full normalized input inventories. Compact release selection and
its hard per-file limit are described in SOURCES.md and OpenSpellGEOSData.md.

Use Python 3 on the build host. To download byte-identical input snapshots:

    python3 fetch_lexicons.py

The manifest lexicon-provenance.json specifies URL, size, SHA-256 and license
for every required download. Downloads fail if upstream bytes change. The
English list URLs are pinned to a specific Git commit. Keep a verified local
source cache to rebuild if an upstream archive disappears. Existing verified
files are reused without network access.

The German source uses 7-Zip. Install a host 7z, 7zz or bsdtar executable, or
manually extract exactly german.dic into lexicons/. The fetch helper verifies
its extracted SHA-256 too. The Swedish and WordNet .tar.gz archives are read
directly by Python; extraction to disk is not required.

Then run:

    python3 normalize_lexicons.py

This writes UTF-8, LF, sorted unique normalized/EN_US.words.txt,
EN_GB.words.txt, DE.words.txt, FR.words.txt and SV.words.txt. It also writes
EN.thesaurus.json, SV.hyp-exceptions.json, and a JSON normalization audit.
Pass these normalized inputs to the Spell project's binary-format builder.
No hosted service, Python package, morphology library or GEOS SDK is needed
for source normalization. The GEOS build itself has separate required steps.

# English US and UK spelling

Source: English Speller Database (formerly SCOWLv2), Kevin Atkinson.
The selected public spelling lists are en_US.txt and en_GB-ise.txt from
https://github.com/en-wl/wordlist-diff . Exact commit and hashes are in the
manifest. The British list follows -ise spelling; the American list keeps
American spelling. These are the regular lists, not the larger dictionaries.
SCOWL-Copyright is the complete upstream notice. Both selected spelling lists
are non-Australian official speller outputs, so the initial permission notice
applies without the additional Australian and advanced-cryptics conditions;
the complete notice is preserved nonetheless.

The snapshot contains 109140 US and 108778 UK unique entries. Original
capitalization and apostrophes remain. The list includes proper nouns and
abbreviations. This build does not infer additional suffixes.

# German spelling

Source: Jan Schreiber's Free German Dictionary, german.7z, released
2021-10-01, https://sourceforge.net/projects/germandict/ . The author's project
page declares Public Domain; German-Public-Domain.txt records that declaration,
and germandict-source.html preserves the retrieved page. The downloaded
readme describes the source methodology and exact Latin-1 text format.

Exactly german.dic is used, containing 2152638 source entries including inflections
and many compounds. The optional variants.dic is excluded because it includes
nonstandard forms. Capitalization is preserved. German compounds are not
invented or guessed. There are 20289 source words longer than 26 characters,
and one longer than 64. The normalizer omits that 65-character form and reports
it explicitly, producing 2152637 German words accepted by the strict builder. This extensive source yields a larger disk
file than a small stem dictionary; the runtime should page it, not load it all.

# French spelling

Source: Grady Ward's Moby Language II French list, 138257 original rows.
The author's January 2001 public-domain grant is recorded in
Moby-Public-Domain.txt and the retrieved moby-source.html. The source is
https://www.gutenberg.org/files/3206/files/french.txt .

This historical source uses postfix ASCII diacritics. The normalizer converts
e' to acute e; a`/e`/u` to grave vowels; a^/e^/i^/o^/u^ to circumflex vowels;
a/e/i/o/u/y followed by doublequote to diaeresis; and c/ to cedilla.
Consonant apostrophes in words such as aujourd'hui remain apostrophes.
The source's oe spelling is preserved; no global oe-to-ligature conversion is
performed because it would corrupt words whose two letters are separate.
The included assertions check representative conversions and apostrophes.
Unrecognized markup is rejected rather than stripped.

69 rows containing abbreviated words with periods or dangling punctuation
are excluded. The result is 138188 unique words. This list includes many
inflections but reflects historical vocabulary and orthography, not a current
normative French dictionary or a complete morphology model. It needs native
speaker review before claiming modern editorial-quality coverage.

# Swedish spelling and conservative compound breaks

Source: NST Pronunciation Lexicon for Swedish, National Library of Norway,
https://www.nb.no/sprakbanken/ressurskatalog/en/oai-nb-no-sbr-22/ . The rights
holder declares CC0. NST-CC0-NOTICE.txt, CC0-1.0.txt and the retrieved
NST-Swedish-source.html preserve that provenance. The source archive contains
927167 semicolon-separated, Latin-1 records, with 51 fields per row.

Field 1 is the written form, field 4 is the compound structure and field 8
marks garbage entries. The normalizer rejects 1979 GARB rows and 4293 rows
with unsupported spelling punctuation/numbers, producing 816336 unique words
including inflections, compounds and names. The lexical source contains some
automatically generated material; it is not a hand-proofread spell dictionary.

For hyphenation, only '+' boundaries between components of at least two letters
are considered. Concatenating the components must reproduce the surface word
exactly apart from case. Leading/trailing '+' markers, linking letters of one
character, overlapping/geminated letters and alternations are skipped. Breaks
must leave at least two letters on each side. Duplicate analyses intersect
their accepted boundaries. This produces 321017 explicit compound exceptions.
They support safe compound boundaries only; they do not provide general
Swedish syllabic hyphenation. Pronunciation/SAMPA syllables are never mistaken
for written-word break positions. The exception JSON maps lowercase words to
zero-based boundary positions measured as the number of preceding characters.

# English thesaurus

Source: Princeton WordNet 3.1, https://wordnetcode.princeton.edu/wn3.1.dict.tar.gz .
WordNet-3.1-LICENSE.txt is the complete license copied from the noun data header,
removing only the display line numbers. Keep this notice with every copy of
WordNet-derived data and documentation. The license is permissive with notice
and non-endorsement obligations. WordNet remains copyrighted by Princeton.

The normalizer reads noun, verb, adjective and adverb synsets. Only words in
the same synset are alternatives: antonyms, hypernyms and other relations are
never repurposed as synonyms. index files preserve WordNet's sense ordering
within each part of speech. Query keys are lowercase and merge case collisions;
alternative spelling case is preserved. The queried headword itself is omitted.
The same English thesaurus can be built for both locales; it reflects WordNet's
primarily American vocabulary and does not convert alternatives between US/UK.

The UTF-8 JSON object maps headword to an ordered array of sense objects with
pos, label and synonyms fields. pos is noun, verb, adjective or adverb. label is
the source gloss with trailing usage examples removed; long definitions are
shortened at a word boundary to at most 180 ASCII bytes. The source's positional
adjective markers (a), (p), (ip) are removed and underscores become spaces.
Only alternatives up to 26 ASCII bytes without comma/period are included.
A result contains at most 26 senses and 80 alternatives per sense; labels and
records are additionally bounded for the legacy UI. The JSON audit reports
shortened definitions, omitted alternatives and omitted senses. These limits
make the thesaurus useful in the existing UI without silently overrunning it.

# Shared normalization and verification

NFC normalization preserves spelling case. A word must start and end with a
letter, with only letters or internal ASCII apostrophe/hyphen in between.
Numbers, whitespace, punctuation-only strings, periods and control characters
are rejected. Lists are deduplicated and sorted by Unicode code point. The
binary builder subsequently performs GEOS character conversion and byte sort;
these text files do not claim to already be in the target byte order.

Words longer than the format's 64-character ceiling are omitted with explicit
counts. All other canonical spellings are retained; the binary builder rejects
unencodable words instead of silently transliterating them.
The normalizer's embedded assertions exercise conversion and boundary cases.
All output sizes, counts, and skipped-source metrics are reproducible from the
source hashes. A successful source build is not a linguistic quality evaluation
or an actual 286/386 runtime benchmark.
