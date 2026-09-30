# OpenSpellGEOS lexical files, version 1

SPDX-License-Identifier: Apache-2.0

This document specifies the replacement lexical file format and the stdlib-only
host builder in Library/Spell/Open/buildlex.py. The format is independent of the
retired proprietary dictionary files. Their contents are neither inputs nor
conversion sources. Licensing and coverage of each distributed language dataset
are documented separately in the language provenance report.

OpenSpellGEOS compact releases impose a separate hard ceiling of 500000
decimal bytes on each complete DCT, THS and HYP file. This selection policy
does not change OLX1, its field widths, the reader ABI or .DCT as the canonical
spelling extension. The format's larger representable file-size limit below
is not the compact release allowance. See OpenSpellGEOSData.md for the ranking
inputs, omission policy, narrower THS selection limits and measured counts.

## Design and resource bounds

DCT, THS and HYP use the same immutable, sorted key/value container. A small
fixed-width index remains on disk. Its entries identify 1024-byte leaves that
hold front-coded keys. Values up to 96 bytes remain in the leaf; longer values
are stored in a separate blob area. Common prefixes are shared only within a
leaf, so every leaf can be decoded independently.

The target does not expand affix rules or interpret TeX patterns. Dictionary
inputs contain surface forms. Hyphenation patterns are applied offline to those
forms. A target query performs a disk lookup and bounded decoding work. There
is no malloc, recursive traversal, Unicode conversion, index-sized allocation,
or dependency on the host byte order. Target code is C89 and requires no 386
instructions. It is intended for the SBCS GEOS configuration; a DBCS port must
supply a different encoding and position contract rather than reinterpret these
bytes as wide characters.

An OLContext owns a 1024-byte leaf, a 1024-byte sparse-index page cache, seven
cached records for the first three binary-search levels, a 65-byte index scratch
record, two 65-byte key buffers, three 65-byte edit-distance rows, and metadata.
Its exact sizeof depends on compiler pointer widths and alignment. A compile-time
assertion limits it to 3328 bytes; the verified host size is 3072 bytes and the
16-bit Watcom size is 2969 bytes. The caller allocates contexts outside
the small target stack. All larger payload buffers belong to the adapters.
The largest format value is 4096 bytes, and no individual buffer exceeds 8 KiB.
Measured packed Watcom allocations are 2971 bytes for an IH file context,
4996 bytes for an IC context, and 7132 bytes for an ET context including its
value buffer. The personal dictionary allocation is 4096 bytes. Compile-time
assertions guard the context and adapter allocation ceilings.
Disk files may be much larger than conventional memory; they are never loaded
as a whole by the runtime. Their maximum supported length is 2147483647 bytes.

An exact query examines O(log B) sparse-index records and reads at most one
leaf, where B is the number of leaves. Index access first reuses the seven
fixed top-level records, then the index-page cache. Records crossing a page
boundary are copied in two bounded pieces. The last page stops at the index
boundary. Caches are populated lazily; no whole-index load occurs at open.
A cached leaf avoids rereading and revalidating that leaf. All caches belong
to one immutable open file; olOpen invalidates every cache before reopening.
I/O failure never marks a partial page or an unvalidated top-level record as
cached.

In the historical full-corpus benchmark, on 200 reproducibly sampled real
words per language and excluding open calls,
warm-context read callbacks fell from 11.69 to 4.955 per British English query
and from 16.04 to 10.01 per German query. With a fresh context for each query,
the respective counts fell to 8.285 and 13.01. Larger page reads trade extra
bytes for fewer seeks: warm English queries read about 5 KiB and German queries
about 10 KiB, compared with approximately 2 KiB before caching. These figures
measure the reader's I/O requests, not elapsed time on hardware or operating
system disk-cache behavior. The full method and counts are recorded in the
index-cache-benchmark.log build log. They are not proof that the complete
Ensemble installation runs in 640 KiB; runtime verification remains required.

## Character encoding and ordering

Encoding number 1 is printable PC/GEOS SBCS, as defined by CInclude/char.h.
Input text is UTF-8 and NFC-normalized before encoding. Every supported Unicode
character produces one byte. Unsupported characters, ASCII control characters,
DEL, and the proprietary logo glyph are rejected. The optional lossy import
mode reports omissions; it never substitutes question marks into words.

GEOS resembles Mac Roman but is not identical. The builder starts with Python's
Mac Roman map and overrides byte B6 to U+03B4, B7 to U+03A3, B8 to U+03A0,
C6 to U+0394, DB to U+00A4, DE to U+00FD, DF to U+00DD. Byte F0 is excluded.
ASCII bytes 20 through 7E retain their meanings. These overrides particularly
matter for currency and accented y; using an unmodified Mac Roman encoder would
silently produce incorrect GEOS text.

Keys contain 1 through 64 bytes and sort lexicographically by unsigned byte
value. A shorter exact prefix sorts before its extension. No trailing NUL is
stored in a key or text field. GEOS bytes are not UTF-8, Latin-1 or a DOS code
page. Tools must not locale-sort the index.

The runtime and builder share one-byte case mappings: ASCII A through Z and
30 GEOS accented Latin capitals map to their lowercase partners. Sharp s is
not expanded to ss. Canonically equivalent Unicode input is normalized before
encoding, but punctuation is not silently replaced. Straight and typographic
apostrophes remain distinct. The two implementations' complete 256-byte lower
mapping is checked by selfcheck.py.

## Container layout

All multi-byte integers are unsigned little-endian and stored without compiler
padding. A file is exactly the header, sparse index, leaf array and blob arena.
All offsets are absolute byte offsets from the beginning of the file.

The 64-byte header has these fields:

- Offset 0, four bytes: ASCII OLX1, the magic and format version.
- Offset 4, one byte: kind, 1 for DCT, 2 for THS, 3 for HYP.
- Offset 5, one byte: encoding, exactly 1.
- Offset 6, one byte: maximum key length, exactly 64.
- Offset 7, one byte: flags, exactly zero in this version.
- Offset 8, two bytes: header length, exactly 64.
- Offset 10, two bytes: leaf size, exactly 1024.
- Offset 12, four bytes: number of distinct key/value records.
- Offset 16, four bytes: number B of leaves and sparse-index entries.
- Offset 20, four bytes: index offset, exactly 64.
- Offset 24, four bytes: leaf-array offset, exactly 64 + 65 * B.
- Offset 28, four bytes: blob-arena offset, leaf-array offset + 1024 * B.
- Offset 32, four bytes: exact file length, at most 2147483647.
- Offset 36, eight bytes: ASCII language identifier, NUL-padded, for example
  EN_GB, EN_US, DE, SV, LB or FR. This is metadata, not the preference setting.
- Offset 44, twenty bytes: reserved, all zero.

The empty container has zero records and leaves, all three region offsets 64,
and length 64. It is valid and answers every lookup with no match.

Each 65-byte sparse-index entry contains one byte of key length followed by the
first key of its corresponding leaf. The remaining bytes are zero. Index entry
number i describes the leaf at leaf-array offset + 1024 * i; no separate pointer
is necessary. Index entries and all records across leaves are strictly sorted.

Each leaf begins with a two-byte used length, including its four-byte header,
and a two-byte record count. The remainder contains exactly that many records,
followed by zero padding to 1024 bytes. Records never span leaves.

A record contains, in order:

- One byte of shared-prefix length relative to the preceding key in this leaf.
- One byte of suffix length, at least one.
- Two bytes of value length, from zero through 4096.
- The suffix bytes, which reconstruct the key after the shared prefix.
- If value length is at most 96: exactly that many inline value bytes.
- Otherwise: a four-byte absolute pointer to the value in the blob arena.

The first record has shared-prefix length zero. A reconstructed key must have
1 through 64 bytes. The prefix cannot exceed the previous key's length. Blob
values may be shared by multiple records; the builder deduplicates identical
large values. Blobs are immutable and have no internal allocation headers.
A pointer plus value length must fit entirely inside the declared file.

The reader validates arithmetic, bounds, keys, the selected index entry, every
record and padding byte of every loaded leaf, key ordering within each leaf,
and DCT/HYP value structure. It checks a leaf's first key against its index.
The GEOS bridge also compares declared file length with actual FileSize.
It does not rescan the complete index or all unused blobs at open time, and it
cannot detect a syntactically valid alteration to a word. SHA-256 hashes in the
distribution/build metadata provide whole-file integrity checking on the host.
The format is not authenticated; a trusted hash or trusted distribution is
needed to distinguish intentional replacement from valid-looking corruption.

## Dictionary value schema

A DCT value is exactly one byte. Value 1 means that the stored spelling is
lowercase under the specified one-byte mapping, and title/all-capital matches
are permitted by the adapter. Value 2 means that the spelling must match exact
case. The exact spelling is tried first. For example, lowercase common words
can match their sentence-initial form, while a proper noun entered only as
London does not make lowercase london a correct spelling.

The builder stores each input surface form as a distinct exact key. Duplicate
identical forms collapse. It assigns flag 1 to lowercase forms and flag 2 to
other forms. It does not generate morphology, decompose German compounds,
recognize arbitrary concatenations, or infer proper nouns. Those capabilities
require an upstream lexical source containing the desired forms.

## Bounded spelling suggestions

The corrective runtime retains the OLX1 dictionary schema. It changes the
private C olSuggest interface by adding a caller-owned OLSuggestWorkspace;
that structure is not stored on disk and is not part of the public GEOS ABI.
Only spelling allocates it. IH/ET continue to allocate the common reader only.
The workspace holds eight 65-byte candidate slots, their lengths and scores,
three 65-byte query/mutation buffers and bounded counters. Its compile-time
ceiling is 768 bytes; the actual packed Watcom target size is 734 bytes.

One query scans at most four leaves around the typed spelling and, when it
differs, four around its lowercase spelling. It also performs at most 48 exact
dictionary probes for deletion, adjacent transposition, doubled-letter
insertion and single-byte accent substitutions. The eight-leaf bound applies
to neighborhood scanning, not to all physical reads: exact probes can load
additional leaves and index pages. All probes are ordinary indexed lookups.
They never generate an output word without a real selected-dictionary hit.

Probe case forms are grouped into lowercase, typed and title-case passes to
avoid repeatedly seeking between distant case regions. Redundant case forms
are skipped. Exact lookup reuses a validated leaf when the query lies between
its first and last keys, including absent keys within that range. A single
cached last-key length supports this fast path; cache validity and reopening
rules remain unchanged. No extra file, index, allocation or startup scan is
required. ASCII case conversion returns immediately; high-byte case conversion
uses the bounded 30-pair GEOS mapping in each direction.

Every candidate is scored with folded optimal string alignment distance at
most two; a neighboring transposition counts as one edit. A three-row,
width-five band bounds distance computation to approximately five cells per
input character. Better candidates displace weaker entries in the best-eight
list, even when that list is full. Fold-equivalent candidates share one slot:
a better score replaces its stored canonical form; an equal score retains the
form already found. Only the closest edit-distance tier found is emitted, so a one-edit correction
does not arrive with a list of weaker two-edit alternatives.

Within one distance tier, ties prefer accent substitutions, then doubled-letter
corrections or a one-character prefix extension, then interior-vowel deletion,
other deletion, transposition and the ordinary neighborhood fallback. Remaining
ties use unsigned-byte lexical order. These small generic typing heuristics do
not encode linguistic frequency, and no reported word is hardcoded as a special
case. The adapter subsequently applies title/all-cap display case only to
foldable entries and preserves exact-case dictionary spellings.

The output contains at most eight NUL-terminated words and respects the caller's
byte capacity. A candidate which cannot fit is not partially written. The GEOS
adapter's output capacity is 200 bytes. ATTENTION: long words can exhaust the
48-probe allowance before later mutations or case forms are tried. Corrections
outside both scanned neighborhoods and the attempted probes can be missed.
A separate compact correction index is the documented upgrade path for broader
recall. The current implementation is deliberately not a whole-dictionary
nearest-neighbor search or an exact replica of the proprietary engine.

With the unchanged compact files and fresh host reader contexts, measured
callback reads excluding open are 49 for Tthis, 80 for Thjis, 90 for teast,
65 for hous and 92 for Addi. Their exact-probe counts are 31, 38, 48, 40 and
38 respectively. These measure requested reader I/O, not DOS cache misses or
elapsed time on physical hardware. Case-flag lookups performed afterward by
the adapter are additional. The runnable selfcheck prints these measurements
and verifies that the requested correction is first and unique.

## Thesaurus value schema

A THS key is the folded headword. A value starts with a one-byte sense count,
from 1 through 26. Each sense contains:

- One byte of part of speech: 0 adjective, 1 noun, 2 adverb, 3 verb, or 255
  unknown. The adapter displays unknown with the explicit unknown UI marker.
- One byte of label length, 1 through 180.
- Label bytes in GEOS encoding.
- One byte of synonym count, 1 through 80.
- For each synonym, one byte of length and that many GEOS text bytes.

Each synonym contains 1 through 26 bytes and no period or comma, because the
existing Spell UI uses those characters as delimiters. Spaces and hyphens are
allowed. The sum of synonym lengths plus one separator byte per synonym must
be below 1600 for each sense. The sum over all labels of label length plus
8, plus one final byte, must be below 1600. The entire binary value must not
exceed 4096 bytes. These limits preserve the existing UI buffers.

The adapter prefixes each meaning with Sense: and replaces interior periods
as required by the old parser. This is display framing, not new semantic data.
Unknown POS is retained truthfully; it is not assigned to the noun class.
Case-fold aliases are merged, and identical encoded senses are deduplicated.

## Hyphenation value schema

A HYP key is the folded complete word. Its value is a sequence of strictly
increasing one-byte break positions. A position p means a break after the first
p original characters, before character p + 1. Every position is greater than
zero and less than the encoded word length. There is no count byte; value
length is the number of positions. GEOS SBCS has one byte per character, so no
byte/character conversion is needed on the target. A value can be empty.

The builder stores only words with at least one permitted break. A missing
word means no automatic break, including words absent from the finite source
word list. This conservative behavior is deliberate. Minimum left and right
fragments are applied offline, and the caller's margins are additionally
respected by the adapter. An exception with no positions suppresses all
pattern-derived positions for that word.

TeX/Liang patterns are evaluated only by the host builder. It decorates the
folded word with boundary periods, overlays the maximum digit weight at each
boundary, and retains odd weights within the requested minima. For TeX input,
literal hyphenation exceptions override pattern results; a separately supplied
exception file overrides both. Extended libhyphen replacement rules, TeX macro
expansion, spelling changes at a break, and unsupported Unicode letters are
rejected rather than approximated. Distinct US and British rules can produce
distinct HYP files even though they share a language family.

## Building data files

Python 3 is sufficient; there are no pip dependencies. Run commands from the
source tree. Output names are explicitly chosen by the caller and should use
DOS-compatible language stems. Copy the resulting files, together with the
matching GDI descriptors, into Ensemble/USERDATA/DICTS. The preference descriptor
and geos.ini selection are covered by the integration guide.

The individual buildlex.py examples below specify the low-level conversion
interfaces. They do not perform compact corpus selection: the caller must
supply candidates that fit. Their --max-bytes option defaults to 500000 and
accepts 64 through 500000 inclusive. A larger encoded result fails atomically
without replacing an existing output. Build the six-profile compact release
through the wrapper, which chooses fitting candidates:

    python3 Library/Spell/Open/build_languages.py --output build/OpenSpellGEOS/DICTS --max-bytes 500000

The default --max-bytes value is 500000, inclusive. The wrapper accepts a lower
limit from 64 bytes upward and rejects values above 500000. It uses
compactlex.py to select candidates and independently checks the actual final
file sizes before publishing the completed output directory. Smaller budgets
can remove substantial coverage. The binary layout and runtime value limits
described here remain unchanged.

A dictionary source is UTF-8 text with one complete surface form per line.
Leading/trailing whitespace is stripped; blank lines and lines starting # are
ignored. Preserve source capitalization. For example:

    python3 Library/Spell/Open/buildlex.py dictionary words.txt EN_GB.DCT --language EN_GB

A thesaurus source is a UTF-8 JSON object. For example:

    {
      "rapid": [
        {"pos": "adjective", "label": "Moving quickly", "synonyms": ["fast", "swift"]}
      ]
    }

Supported POS strings are adjective, noun, adverb, verb and unknown. Build it
with:

    python3 Library/Spell/Open/buildlex.py thesaurus synonyms.json EN_GB.THS --language EN_GB

Plain pattern input contains whitespace-separated UTF-8 Liang patterns with
embedded ASCII digits. Percent comments are stripped. To extract literal
patterns and hyphenation blocks from a UTF-8 TeX file, add --tex. The builder
never runs TeX and rejects nested/control-sequence pattern syntax. A source
using TeX escapes or macros must first be converted into reviewed UTF-8 plain
patterns by a source-specific importer.

An explicit HYP exception source may be a UTF-8 JSON object mapping words to
lists of positions, for example {"hyphenation": [2, 6], "unbroken": []}.
Alternatively, a non-JSON file contains one hyphen-separated word per line,
for example hy-phen-ation. JSON positions refer to NFC-normalized characters.
They must already be unique, ordered integers within the word.

For English rules with left minimum 2 and right minimum 3:

    python3 Library/Spell/Open/buildlex.py hyphenation words.txt EN_GB.HYP --language EN_GB --patterns hyph-en-gb.tex --tex --left-min 2 --right-min 3

For explicit exceptions only:

    python3 Library/Spell/Open/buildlex.py hyphenation words.txt SV.HYP --language SV --exceptions sv-exceptions.json --left-min 2 --right-min 2

The CLI default minima are 2 and 2. Use the actual minima prescribed by the
chosen language source; do not assume that the default applies to English.
TeX exceptions are read automatically with --tex. --exceptions has final
precedence, including explicit suppression of all breaks for a word.

Strict mode aborts on malformed UTF-8, unsupported characters, overlength words,
invalid values, and legacy thesaurus size violations. For large reviewed
sources, --skip-unencodable omits unencodable or overlength dictionary forms;
for thesaurus imports it also omits malformed/oversized senses and those that
would exceed the legacy aggregate caps, while retaining fitting distinct
senses. Every such invocation reports its omission count on stderr. This flag
is intentionally a lossy mode and should be accompanied by the conversion
report. Exception and pattern syntax remain strict. No builder can establish
that a lexical source has an Apache-compatible license; verify and preserve
the actual source license and attribution before distribution.

Each successful build prints JSON containing filename, language, kind, record
count, leaf count, exact file size and SHA-256 hash. Writes use a same-directory
temporary file followed by replacement, so a failed build does not truncate a
previous output. Rebuilding identical encoded entries produces identical bytes;
there are no timestamps in the format. The builder may need substantial host
RAM when sorting millions of surface forms. This cost does not occur on GEOS.

The importable build_file(kind, language, entries, output, max_bytes=None)
accepts a mapping of bytes keys to bytes values and returns the same statistics.
The optional None limit exists for internal format fixtures; it does not waive
the release ceiling. Public command-line tools enforce a numeric limit, and
the six-profile wrapper passes its checked ceiling to the writer. read_words,
read_thesaurus and build_hyphenation implement the input conversion rules.
The build_file layer checks container bounds and DCT/HYP values; callers using
it directly are responsible for constructing a valid THS schema. The CLI's
thesaurus path performs that schema validation.

## Reader API and checks

openlex.h exposes OLRead, OLContext, olOpen, olFind, olSuggest and olLower.
OLRead must read exactly the requested count from an absolute offset and return
1 on success, 0 on failure. olOpen initializes the context and returns 1 or -1.
Callers must not concurrently use one context or alias input/output with its
internal buffers. A context may be reused after closing its underlying file
only by calling olOpen again with the new callback state.

olFind returns 1 for a found value, 0 for absence, -1 for invalid input,
malformed data or I/O failure, and -2 if the output capacity is insufficient.
Its length output is zero initially and gives the full value length for a hit
or short-buffer result. It does not append NUL to values. On -1, ignore output
buffer contents. Do not treat -1 as a spelling error or as a valid empty file.
olSuggest returns 1 or -1 and writes complete NUL-terminated alternatives only;
its length counts the bytes including those terminators.

Run the host regression check with:

    python3 Library/Spell/Open/selfcheck.py

It compiles the identical reader with a C compiler in strict C89 mode and uses
Python stdlib ctypes to exercise it. It checks 4002 dictionary entries across
many leaves, maximum key/value sizes, inline/external value boundaries,
short-buffer handling, missing keys, damaged headers/records/indexes/blobs,
1000 deterministic byte mutations, all 256 case-map entries, index-page
boundaries, bounded context size, cache invalidation on reopen, I/O retry after
cache-fill failure, source parsing, NFC conversion, TeX exception precedence,
reproducibility, and suggestion
results against an independent full edit-distance calculation. It writes only
temporary files. It does not replace the required GEOS NC/EC build or an
interactive Ensemble verification on the intended hardware or emulator.

Run the compact-selection checks with:

    python3 Library/Spell/Open/compactcheck.py

These check priority ordering, exact estimated versus written sizes, the
inclusive ceiling, THS sense/synonym/label policy, GEOS ellipsis encoding,
HYP membership in selected DCT words, the authored-supplement union and
failure without publishing partial outputs. They use temporary synthetic
data; the release audit below checks the actual selected language files.

For a completed six-language build, run the release audit separately:

    python3 Library/Spell/Open/audit_release.py /path/to/DICTS

Add --sources /path/to/Data if the normalized inputs are stored elsewhere.
This audit walks every record and payload in all eighteen linguistic files,
checks whole-file hashes against BUILD.json, verifies global ordering and blob
coverage, queries real language samples through the compiled C reader, checks
US/GB hyphenation exceptions, and repeats compact English dictionary selection
and building from the pinned inputs to check byte-identical output. It also
checks the per-file byte ceiling, compact THS limits and selection counts
against the manifest. Its explicit empty-file
check for an unavailable hyphenation source is not a claim of that language's
hyphenation coverage.

The production translation unit is Open/spellopen.c. Its implementation
fragments use the .inc suffix because this source tree's mkmf discovers direct
subdirectory .c files as independent modules. openlex.inc is ordinary C89 and
is compiled unchanged with the host compiler's -x c option by the checks.
Host fixtures must not be placed as extra .c files directly in Open, where
mkmf would incorrectly include them in the GEOS library.

Implementation helpers intentionally use external object-file linkage with
unique ol/Open prefixes. In the supplied toolchain, Watcom's LPUBDEF records
for static Pascal helpers are not resolved by glue during the real geode link.
Removing the function storage class resolves those references; it does not
add entries to spell.gp or change the library's exported API. Data that needs
private storage remains static. The aggregator records this compatibility
requirement so a future cleanup does not restore the link failure.
