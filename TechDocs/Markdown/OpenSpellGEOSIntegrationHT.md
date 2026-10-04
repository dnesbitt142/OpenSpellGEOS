# OpenSpellGEOS: hyphenation and thesaurus integration

This document describes the new code in Library/Spell/Open/openht.inc and the
essential edits to the existing IH, ET, and thesaurus controller assembly.
The implementation is licensed under Apache-2.0. It does not read, decode,
convert, or depend on the attached proprietary linguistic databases.

The corrective OpenSpellGEOS release keeps these adapters and their ABI unchanged.
The common reader gains one cached-key length byte; spelling-only candidate
workspace is not allocated by IH or ET.
Each shipped DCT, THS and HYP has a hard inclusive ceiling of 500000 decimal
bytes. Compact THS selection keeps at most two senses, four synonyms per sense
and 48-byte labels; the larger runtime validation limits documented below
remain the actual ABI limits. HYP generation is limited to selected DCT words
and can omit further records to fit. See OpenSpellGEOSData.md for selection
rules, retained counts and coverage losses. Historical full-corpus runtime
checks must not be described as new compact-data GUI checks.
The main guide separately records the fresh compact NC "good" thesaurus
lookup; compact GUI hyphenation remains untested.

The existing public HyphenOpen, Hyphenate, HyphenClose,
ThesaurusGetMeanings, ThesaurusGetSynonyms, and ThesaurusClose interfaces are
retained. The new private adapters replace the formerly disabled proprietary
IHhyp, SLcnv, et_load, et, and et_close entry points. The retained assembly
continues to own the UI, thread semaphores, public result blocks, and original
control blocks. These adapters support the SBCS build used by the supplied
Western European language data. They are not a DBCS implementation.

## Build organization and calling conventions

Library/Spell/Open/spellopen.c is the sole compiled C source in this module.
It includes the production .inc files. This is intentional: mkmf discovers C
files in immediate module directories. Host fixtures use a .test extension so
the geode build cannot accidentally include main or host libc code. The
earlier IH/ET tests/test_openht.test fixture is not present in this
repository; only the spelling test_icgeos.test fixture is supplied.

IHhyp and SLcnv use GEOS Pascal calling convention. Pascal arguments are
pushed left to right. IHhyp therefore declares the word pointer first and the
IH control block pointer second, matching the existing assembly push order.
SLcnv declares source, length including terminator, destination, and direction.
The historical comments saying IH arguments are reversed do not describe the
new C declaration. The actual pushes and declarations agree.

et_load, et, and et_close retain their historical cdecl interface. The
assembly removes their arguments. et takes word, option, output, grammar
array, and control block; its caller removes 18 argument bytes. et_load takes
preload size and control block; et_close takes a control block. No source
calling these public Spell functions needs to be rebuilt merely because the
private implementations changed.

The packed IH and ET control structures preserve the assembly offsets. The
16-bit compiler checks their complete sizes, 754 and 24 bytes respectively,
at compile time. The replacement uses the existing IH hctlbuff and ET hramdict
fields as GEOS memory handles. Unused proprietary fields are retained only to
preserve layout. New code is assigned to IHCODE, STDLIB, and ETCODE, matching
the existing external declarations and resource definitions.

All external C entry points called from assembly carry _export, which maps
to __export __loadds under Watcom. Assembly callers may have DS pointing at
a locked control block or a result heap. Loading the library data segment
is therefore mandatory before any C helper accesses literal strings or
constant tables. Internal helpers inherit that established data segment.

## Language selection and lifetime

All three services derive their filenames from the existing text/dictionary
preference. EN_GB.DCT selects EN_GB.THS and EN_GB.HYP, for example. The bridge
validates the selected basename and opens only beneath USERDATA/DICTS. The
legacy text/thesaurus, hyphenationLanguage, and hyphenationDictionary values
are not alternate sources of language selection for these adapters. This
prevents selecting a German spelling dictionary while silently continuing to
use an English thesaurus or hyphenator.

The retained IH initialization wrapper still populates its historical fields,
but the adapter deliberately opens the file derived by the shared bridge.
ThesaurusGetFilename calls the new OpenThesaurusFilename helper so the
availability check and actual open select the same THS file. Invalid
configuration produces an empty filename and a normal unavailable result.

Open sessions keep their selected files until the existing close/reopen cycle.
Changing preferences during an active session does not mutate an open file.
Close the relevant application session and reopen it after switching language.
If a selected data file is missing or invalid, the operation fails; there is
no fallback to another language.

Persistent IH and ET state is allocated with MemAllocSetOwner using
GeodeGetCodeProcessHandle, HF_SWAPABLE, HF_SHARABLE, and HAF_ZERO_INIT. This
makes the shared state owned by spell.geo rather than whichever application
first called it. It can therefore be locked by another client and survive
the first client's termination. The bridge similarly assigns persistent file
handles to the library owner.

No pointer into a movable context survives its unlock. Each lookup locks the
handle and resets the OpenLex callback's user pointer before reading. The
existing semaphores serialize normal public lookup calls. No new mutable
global state or malloc/free calls are introduced in production code.

## Hyphenation behavior

HYP values are ascending byte positions between characters, with no count
prefix. The OpenLex value length supplies the count. A position must be
greater than zero and less than the key length. Every position must be
greater than the preceding position. The adapter validates the entire value
before setting any output bits. Maximum key length is 64 GEOS bytes; the
largest possible position is therefore 63.

The runtime looks up the case-folded complete word. Any pattern application
or exception processing happens in the host builder. There is no runtime
pattern trie, affix expansion, dictionary-sized allocation, or heuristic
hyphenation of an unknown word. A missing word succeeds with no breaks.
This trades coverage outside the generated vocabulary for small, predictable
runtime work and conservative line breaking on a 286.

The original interface stores breaks MSB first in each little-endian dword.
The retained DwordsToWords routine exchanges each dword's two physical words
before BitsToBytes enumerates their bits. This is why position 1 is bit 31
in the first C dword, not bit 15. The host regression check covers positions
1, 16, 17, 32, 33, 48, and 63 through both transformations.

SLcnv now copies GEOS SBCS bytes without converting to the old proprietary
character set. It accepts the caller's length including its terminator and
limits the operation to its documented 66-byte destination. IHhyp returns
zero on success and the historical failure value 8 on an invalid task,
bad input, malformed value, I/O failure, or unavailable database. Close is
safe when the internal handle is already zero.

## Thesaurus values and UI limits

The THS payload is a byte meaning count followed by each meaning's part of
speech, byte label length, label bytes, byte synonym count, and repeated
byte synonym length plus synonym bytes. Consult OpenSpellGEOSFormat.md for the
complete common container and payload specification. The adapter enforces
these limits before producing any string for the original parser:

- A payload occupies at most 4096 bytes and contains 1 to 26 meanings.
- Parts of speech are 0 adjective, 1 noun, 2 adverb, 3 verb, or 255 unknown.
- A label contains 1 to 180 bytes and no character below byte 32.
- Each meaning contains 1 to 80 synonyms, each 1 to 26 bytes long.
- A synonym cannot contain a comma, period, or character below byte 32,
  and cannot start or end with a space.
- The complete meaning output, including prefixes, delimiters, and its
  terminator, must fit the existing 1600-byte buffer.
- Each meaning's complete synonym output, including delimiters and its
  terminator, must fit the same buffer.
- Trailing bytes and every truncated field are rejected.

Each meaning is rendered as "Sense: " followed by its label and a period.
The last meaning is followed by another period and a zero byte. Interior
label periods become semicolons. This preserves the existing parser's rule
that a period followed by an ASCII capital starts the next meaning; the
prefix works equally with French or German labels beginning with an accented
letter. ThesaurusMeaningsParse removes this exact leading prefix before storing
each definition in the chunk array. The list and selected-definition text
therefore display the label without "Sense: ". Synonyms are comma separated and end with a period and zero byte.

Unknown part of speech is preserved rather than invented. Disk value 255
becomes grammar-array value 4. The built-in controller has a fifth "(?) "
entry. Its existing length calculation already handles this four-character
prefix. Third-party callers which directly index the old four-entry grammar
table must also handle value 4. The values 0 through 3 retain their old
meaning and binary representation.

The adapter returns the meaning or synonym count, zero for an absent word or
sense, -1 for state allocation failure, -2 for an unavailable database, and
-3 for corrupt data or failed lookup I/O. The old 20 KB preload argument is
accepted but ignored. Word lookup is repeated for a synonym request rather
than trusting a stale proprietary Lookup structure.

## Why edits beyond uncommenting calls were necessary

IH/ihCalls.asm had an unconditional jump disabling HyphenOpen. Removing that
jump also requires removing its redundant directory push: HyphenSetPath
already pushes the directory, and the exit path pops it once. The three IHhyp
calls and SLcnv call are restored.

The same file had the following correctness defects on the newly reachable
paths. They are corrected without redesigning the public interface:

- A failed IH initialization now frees its outer ABI block.
- The saved DI and BX registers are restored in the same list order as the
  push, following ESP's multiple-register convention.
- The converted word buffer now includes space for its zero terminator.
- The locked IH buffer segment in ES is saved across IHhyp, because the
  GEOS Pascal calling convention permits the C callee to modify ES.
- Hyphenation result allocation permits ordinary failure rather than using
  HAF_NO_ERR; failure unlocks the already locked IH control block.
- HyphenClose checks the success status in the correct direction, clears its
  stored handle, and returns zero for a successful or no-op close.
- BitsToBytes visits all 16 bits of every word. Previously it skipped each
  sixteenth bit and advanced the position counter only 15 times per word.
- Result storage includes an explicit terminator byte, and the converter
  writes the terminator even when the map is empty.
- The obsolete default filename is replaced by EN_US.HYP. Actual selection
  still comes from the shared dictionary preference as described above.

ET/thes.asm also had an unconditional failure jump; that jump is removed and
all et_load, et, and et_close calls are restored. Allocation failure receives
an explicit ET error code. A failed et_load releases the outer control block
instead of retaining an unreachable allocation. Early lookup exits initialize
their result handles and offsets to zero. A synonym result allocation failure
frees its text buffer without attempting to unlock a control block that has
not yet been locked. The corresponding definitionless-thesaurus cleanup path
also avoids that invalid unlock. ThesaurusGetFilename uses the new helper,
preserving AX because ThesaurusOpen still needs the allocated block segment.
ET/etManager.asm declares that helper in ETCODE.

UI/thesCtrl.asm adds the unknown grammar entry, frees temporary result blocks
that were not installed because a lookup returned no result or an error, and
changes the obsolete COM_THES.DIS error text to refer to the selected THS file
in DICTS. These cleanup edits matter on low-memory machines: unsuccessful
lookups must not accumulate abandoned chunk-array blocks.

All existing edited assembly files retain their original CRLF line endings.
No proprietary resource, original public function name, or public parameter
layout is replaced.

## Memory and verification

With the supplied Watcom build flags, the IH reader state is 2971 bytes plus
the original 754-byte control block. The ET state is 7132 bytes, including its
4096-byte payload buffer, plus the small original control/Lookup block. These
sizes were checked by the actual 16-bit compiler. They include
the fixed 1024-byte index-page cache and seven cached binary-search nodes;
they do not grow with the dictionary. A compile-time assertion limits the
complete ET state to 8192 bytes. Each individual new allocation stays within
8 KB. Existing public lookup code additionally creates
temporary text and result blocks; UI code, loaded resources, stack borrowing,
and expanded chunk arrays also consume memory. These figures are not a claim
that an entire Ensemble installation fits in conventional memory without its
normal swap configuration.

The earlier integration package's independent IH/ET adapter regression
fixture, tests/test_openht.test, is not included in this repository. The
following results describe that historical check and cannot be reproduced with
the supplied files alone. For the available reader and data audits, use the
commands in OpenSpellGEOSFormat.md.

The historical test deliberately moves every fake heap allocation after
unlock, checks library ownership and sharable allocation, verifies bitmap
boundaries and the two text representations, tests unknown grammar, rejects
every prefix truncation of a valid THS record, rejects unsafe delimiters and
grammar bytes, checks output canaries, and verifies that all allocated handles
are freed. The same test also passes with the host compiler's undefined-
behavior sanitizer. A LeakSanitizer attempt could not run in this environment
because its process inspection via /proc was unavailable; it is not reported
as a successful address/leak-sanitized run.

The supplied 16-bit OpenWatcom compiler accepted the initial adapter in both
EC and NC modes with 8086-compatible code generation and no diagnostics.
Consult the main build report for the authoritative final full-geode build
and any remaining limitations. Host tests do not execute GEOS file services,
segmented register preservation, UI messages, or thread scheduling. A real
Ensemble smoke test should open, look up, close, and reopen all six languages,
try missing and corrupt files, switch languages, and repeat lookups from two
applications while closing the first one.
