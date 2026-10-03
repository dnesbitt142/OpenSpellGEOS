# OpenSpellGEOS: change record

This records the delta against the user's supplied pcgeos-CI-latest source
archive. The repository contains the source overlay, generated linguistic
data, Python build tools and technical guides. Earlier build/runtime evidence
referenced here is not included in this GitHub layout. The overlay does not
contain proprietary language databases or replace unrelated applications,
drivers, SDK tools or build rules.

The compact release is branded OpenSpellGEOS and renames these six documents
from SpellOpen*.md to OpenSpellGEOS*.md. Technical identifiers such as OLX1,
OpenLexCode, Spell export names, OPENUSER.USR and Library/Spell/Open remain
unchanged. .DCT remains the canonical spelling extension.

## Personal dictionary errors and project layout, 2026-10-01

The technical guides now follow the GitHub repository layout. Python builders
and checks live in Dictionaries/BuildTools, acquisition and normalization
helpers in its Sources directory, and the normalized snapshot is packaged as
Data.zip. Library/Spell/Open retains the runtime sources. Data-building
commands extract that snapshot and write a separate output directory. Reader
checks use temporary copies beside the scripts, preserving the supplied folder
structure.

Personal-dictionary failures now select the existing localized SP-11 through
SP-14 notifications. Save errors retain the previous live list; load errors
separate damaged/inaccessible files, an unsupported OSU version and failure to
allocate the shared personal table. Notifications occur after releasing locks
and the semaphore. Existing OPEN_ERROR, SIF_USER_DICT_ERR and UR_SER results
let the UI suppress duplicate generic messages without changing the public
ABI. A missing USR and BAK still starts an empty list without an error. Host
adapter checks cover these failure results, notification timing and failed-
save rollback. See OpenSpellGEOSIntegrationIC.md for the detailed conditions
and recovery rules.

The supplied dictionary, hyphenation, thesaurus, GDI and build-input files are
unchanged. Unreferenced compatibility entry points and compiler support
symbols are independent of the previously unreferenced SP-11 through SP-14
strings.

Verification for this revision passed the host spelling fault checks and six
real-data correction checks against the unchanged English UK and Luxembourgish
dictionaries. The staged portable-reader selfcheck and compact-selection
checks also passed. A clean build against an exact copy of this source overlay
passed mkmf, pmake depend and pmake -L 4 full, producing both NC and EC geodes
with the supplied Open Watcom compiler and locally built Linux SDK tools.
The SP-11 through SP-14 Strings warnings and GEOSNOTIFY warning are gone; the
retained compatibility-symbol warnings remain. Interactive GEOS dialogs were
not exercised in this run.

## Corrective revision, 2026-09-30

This revision repairs spelling suggestions and the repeated-use dialog defect
reported against the compact release. All eighteen DCT/THS/HYP files remain
byte-identical to that release: 611,367 records, 7,234,896 bytes in total, and
499,983 bytes for the largest file. The format, six language profiles, GDI
records, dictionary-selection preference and public Spell ABI are unchanged.
No linguistic content is taken from the proprietary reference files.

The old suggestion reader stopped after the first eight nearby matches. The
adapter then appended lowercase-search results only if space remained. Thus
an early poor list could exclude a closer correction, and lowercase dictionary
spellings lost the user's initial capital. The revised reader jointly ranks
candidates across the typed and folded neighborhoods and bounded exact probes
for common typing errors and accent substitutions. The adapter projects title
case or all capitals only onto foldable dictionary entries; exact-case entries
retain their canonical spelling. The private C suggestion API takes a separate
workspace so the thesaurus and hyphenation contexts do not carry spelling-only
candidate storage. Public GEOS interfaces do not change.

Open/icgeos.inc also checks that an alternate's terminating NUL lies inside
the remaining alternate-list tail before copying it. This is defensive bounds
hardening, not the claimed cause of the oversized window. Its regression check
covers every possible tail offset, maximum valid words, context relocation and
repeated initialization/exit.

UI/uiSpell.asm replaces the GPC_SPELL dialog's persistent 90-percent position
hint with the native center-window hint. The source and emulator reproduction
identify a shared CommonUI close/reopen conversion which treats old absolute
right/bottom coordinates as dimensions. Centering avoids that conversion with
one Spell-local change. The dialog now uses centered placement and retains
content-derived sizing; no shared UI binary is replaced. The complete causal
trace, baseline and fixed-run evidence are in OpenSpellGEOSDialogFix.md.

spell.gp declares the movable OpenSuggestCode resource, keeping correction code
separate from the reader loaded by IH/ET and from the spelling adapter. New
comments and runnable regressions cover the changed code. Immutable case and
accent tables are shared to remove 87 duplicate data bytes. The two out-of-range
branches reported by ESP in IH/ihCalls.asm and UI/thesCtrl.asm have explicit
LONG annotations, as required by the supplied programming rules; their control
flow is unchanged. Detailed current
build, resource measurements and runtime results accompany the archive;
historical logs remain explicitly historical rather than being reused as proof
of the revised binaries. The supplied SWAT status 189 alone is not treated as
a demonstrated crash; the existing lazy spell-worker lifecycle is unchanged.

The prior compact selection still enforces a hard inclusive ceiling of 500000
decimal bytes per complete linguistic file. It prioritizes source-guided common
vocabulary and narrows thesaurus payloads before writing OLX1. Its exact counts,
omissions, licenses, tools and reproducible recipes remain documented in
OpenSpellGEOSData.md and BUILD.json.

## Scope of existing-source changes

Nine existing Spell files change. Existing files retain CRLF, their export
order is unchanged, and generated Makefile/dependencies.mk files are not
distributed. Most entry-point changes enable calls already present in the
source. A few correctness repairs are necessary because merely uncommenting
those calls would expose incorrect stack restoration, failure-path leaks,
disabled initialization and dropped hyphenation bits. Those repairs are
listed individually below rather than hidden as incidental cleanup.

### ICS/icsThread.asm

Enable eleven existing calls/macros for initialization, shutdown, spelling,
alternates, personal-word add/delete/list/save, and ignore/reset. Deleting a
personal word now uses the same AX:DX return convention as adding a word,
so the existing UI receives both the word-list result and error status.
No message number, method signature or public ICBuff layout changes.

### ICS/spell.asm

Enable the library-exit call and both existing alternate-retrieval calls.
These are the only three changed source lines in this file.

### ET/etManager.asm

Declare the private far OPENTHESAURUSFILENAME helper. It is used by the existing
wrapper and is not added to the public export table.

### ET/thes.asm

Remove the forced failure immediately after changing to DICTS, then enable
the pre-existing load, lookup and close calls. Return the correct allocation
error and release the outer control block when adapter initialization fails.
Initialize result handles before early exits, return initialized handles in
the documented registers, and avoid unlocking a control block that has not
yet been locked on allocation failure. Derive the .THS name from the same
[text] dictionary stem as spelling and hyphenation. Preserve AX around that
filename helper because its caller still needs the allocated block segment.

The old nine-word cdecl ET call frame remains nine words. The wrapper still
removes its arguments; the replacement C function does not pop them twice.

### IH/ihCalls.asm

Remove the unconditional failure and duplicate directory push. Enable the
existing IHhyp and SLcnv calls, and change the visible default to EN_US.HYP.
Free the outer ABI buffer if initialization fails. Restore DI and BX in the
order matching their saved stack positions. Add room for a converted-word
terminator and a result terminator. Handle allocation failure by unlocking
the already locked IH buffer instead of leaking its lock. Preserve ES across
the C hyphenation call because the wrapper needs that segment afterward.

Correct the inverted status test in HyphenClose, clear its released handle,
and return success after normal close. Visit all sixteen bits in every bitmap
word and explicitly terminate the result array: the prior loop skipped each
sixteenth bit. The existing DwordsToWords transformation is retained. The
corrective revision marks HyphenOpen's allocation-failure branch LONG after ESP
reported that its displacement exceeded the short-jump range. Tests
cover positions 1, 16, 17, 32, 33, 48 and 63 through this complete convention.

### UI/thesCtrl.asm

Add an unknown-grammar display string for data with no part-of-speech field.
Release temporary result blocks on not-found/error paths when they were not
installed in the controller. Replace the obsolete COM_THES.DIS error text
with the selected .THS file in DICTS. The corrective revision adds LONG to
ThesControlFormatLookupWord's getOneWord branch to resolve its assembler warning
without changing the punctuation-handling logic.

ATTENTION: Part-of-speech value 4 now means unknown. The bundled controller
handles it. Third-party clients must not use it as an unchecked index into
a legacy four-element table. Public function signatures and export order
are unchanged, but this semantic extension must be considered by clients.

### UI/uiSpell.asm

In SpellControlGenerateUI, replace the ratio-of-parent position hint and its
coordinate payload with HINT_CENTER_WINDOW and a zero-length payload. Keep the
existing geometry scan. This surgical change prevents cumulative outer-frame
growth on subsequent spell-check sessions; see the corrective revision above.

### local.mk

Set final NC flags to -ox -0 and EC flags to -0. The platform defaults include
-3; the final CPU selector must override that setting to support a 286.
No compiler executable, generated dependency file, or platform-wide flag is
modified by the source overlay.

### spell.gp

Enable eight existing code-resource declarations: ETCODE, IPCODE, INIT, EXIT,
IPPRINT, CODE, IHCODE and STDLIB. Add an explicit fixed OpenReadCode resource
for the saved read callback. A C segment named FixedCode did not merge with
the assembly segment of that name in the actual linker, so a unique resource
and explicit fixed attribute are required. Replace the obsolete proprietary dictionary
usernotes with attribution pointing to the supplied data notices. Add a shared
movable OpenLexCode resource for the common reader: this separates it from
the spelling adapter, avoids loading spelling-only code for IH/ET, and removes
the large-resource warning produced by the unsplit EC CODE segment. Preserve
the library name, token, protocol and public export sequence. The corrective
revision additionally declares OpenSuggestCode for bounded correction code.

## New production source

Open/spellopen.c is the sole new C translation unit. It includes the four
implementation fragments in a deliberate order. Its initial segment pragma
places the reader in OpenLexCode; the bridge's own pragma then restores CODE
for the adapters. The Spell project contains
assembly module directories; its existing mkmf discovery requires the C unit
inside Open. Keeping implementation fragments as .inc and host fixtures as
.test prevents the build from compiling them as independent production units.

Open/openlex.h and openlex.inc define and decode OLX1. They implement bounded
header/index/leaf/blob validation, exact lookup, fixed-size index and leaf
caches, a GEOS byte-case map, and limited edit-distance suggestions. The code
uses explicit little-endian reads and does not map an on-disk structure onto
a compiler-dependent C structure. Contexts contain all mutable state; no
runtime heap allocator or libc file I/O is required by the core.

Open/geosbridge.h and geosbridge.inc connect the reader to GEOS file APIs,
confine names to valid 8.3 basenames in USERDATA/DICTS, restore current paths,
check short reads and file lengths, and transfer file ownership to the
library. The saved read callback is in the explicit fixed OpenReadCode resource;
an ordinary saved far pointer into movable code would not be safe across
resource movement. Context self-pointers are rebound after each MemLock.

Open/icgeos.inc implements the old spelling entry points over the reader:
case-sensitive dictionary flags, title/all-cap acceptance, bounded spelling
alternatives, punctuation maps, smart-apostrophe normalization, duplicate-word
tracking, ignore/reset, and a shared persistent personal dictionary. It uses
the existing packed ICBuff header with compile-time ABI assertions. Personal
edits use a temporary file, commit, backup/rename and rollback paths. A failed
save does not publish a new in-memory personal list. Proprietary personal
dictionary bytes are never imported or overwritten by the new format.

Open/openht.inc implements the packed IH and ET interfaces. It reads exact
precomputed hyphen positions and renders bounded thesaurus meanings/synonyms
into the legacy buffers. It validates the complete payload before output,
preserves explicit unknown grammar, and allocates library-owned sharable
state. Compile-time checks enforce ABI sizes and sub-8-KiB state blocks.

All assembly-callable C entry points use the required calling convention and
Watcom _export DS setup. Pascal wrappers pop their arguments; ET retains
cdecl. These conventions were checked in actual 16-bit compiler output.
Uniquely prefixed helper functions intentionally have external C linkage:
the supplied glue linker could not resolve Watcom's local Pascal symbols.
They remain private to the geode because no helper is added to .gp exports.
Static constant data retains its original storage class.

## New host tools and data

Dictionaries/BuildTools/compactlex.py applies pinned profile rankings, bounded
byte-budget selection and the compact THS policy before the existing OLX1
writer runs. Its exact size estimator is checked against the final file;
selection does not claim a globally maximal record count because front coding
and block boundaries make successive prefix sizes nonmonotonic. Compact THS
values keep at most two senses and four synonyms per sense, with whole-word
labels limited to 48 GEOS bytes. HYP candidates come only from selected DCT
words and retain only nonempty legal-break records before their own file-
budget selection.

The per-profile priority metadata states whether ranking comes from source
counts, attested sets or heuristics. Manually chosen common/function words
are prioritized first. These source signals are not interchangeable with a
general-language frequency corpus, and native-language review remains needed.
OpenSpellGEOSData.md records the language-specific rules and omissions.

Dictionaries/BuildTools/Sources/make_priorities.py regenerates six ranked
UTF-8 lists and their report from pinned WordNet, NST and LOD archives. It
verifies archive and normalized input hashes, retains only already accepted
spellings, and records missing authored seeds. Data/compact-core-words.json
provides manually chosen essentials. Data/SV.core-supplement.txt separately
supplies 14 reviewed basic Swedish words missing from NST under Apache-2.0; no
new hyphenation positions are inferred for them. These authored inputs and
generated priority outputs are pinned in buildset.json and documented
separately from upstream data.

Dictionaries/BuildTools/buildlex.py builds an individual dictionary, thesaurus
or precomputed hyphenation file from documented UTF-8 source schemas. It
handles GEOS encoding, deterministic sorting/front coding, shared large
values, Liang patterns, literal TeX pattern/exception blocks and explicit no-
break exceptions. It rejects invalid input, writes atomically, and refuses to
overwrite the input file itself. Its public CLI now checks the complete
encoded output against --max-bytes (default 500000, accepted range 64 through
500000) before replacement. It rejects oversized inputs rather than choosing a
smaller vocabulary; use the six-profile wrapper when priority-based compact
selection is required.

Dictionaries/BuildTools/build_languages.py checks every pinned input hash in
Data/buildset.json, builds six profiles in a temporary directory under the
default 500000-byte per-file ceiling, writes compatible OpenSpellGEOS .GDI
records and BUILD.json, and publishes only a completed new output directory.
It also copies full redistribution notices into DOS-compatible LICENSES
filenames and NOTICES.TXT. It explicitly reports the empty Luxembourgish
hyphenation file.

Dictionaries/BuildTools/Sources contains pinned URL/size/SHA-256 manifests,
permissive license texts, full provenance/limitation documents, download
helpers, lexical and LOD/terminology normalizers, and a normalization check.
Dictionaries/BuildTools/Data.zip packages the Data directory; after extraction
beside the archive, Data contains the normalized UTF-8 snapshots,
pattern/exception inputs, omission reports, authored compact inputs, ranked
word lists and their provenance report. Ordinary data builds are offline and
require only Python's standard library. Refreshing from original upstream
archives has separate documented download and extraction requirements. No
proprietary lexical source is present.

The supplied Dictionaries folder contains six language ZIPs, each with a
language folder holding its .DCT, .THS, .HYP and .GDI files. The build
manifest and redistribution notices accompany the archives. English US/UK
spelling and hyphenation stay distinct. Thesaurus data preserves real source
synonym relations; translations or related terms are not invented as synonyms.

## Verification source and documentation

Dictionaries/BuildTools/selfcheck.py compiles the actual portable C core in
strict C89 mode and tests lookup, edit distance, malformed data, cache
boundaries, failed reads, reopen invalidation, encoding and builder behavior.
Dictionaries/BuildTools/audit_release.py independently walks every shipped
record, checks hashes and payload schemas, and exercises native-C lookups
against actual multilingual samples. Dictionaries/BuildTools/compactcheck.py
checks ranking, exact byte estimation, the inclusive ceiling, THS/HYP
selection policy, supplement merging and atomic publication.

Library/Spell/Open/test_icgeos.test provides host GEOS shims for the actual
spelling adapter. It forces relocation after unlock and exercises ownership,
buffer bounds, failure cleanup, ABI-facing results and personal-file
persistence failures. The historical tests/test_openht.test fixture is not
included in this repository. Test malloc/free is confined to host fixtures. No
test framework or host binary is a target dependency. See
OpenSpellGEOSFormat.md for staging the reader checks alongside the Python
scripts in this layout.

OpenSpellGEOS.md explains integration, build order, memory and installation.
OpenSpellGEOSFormat.md specifies the byte-level format and individual
builders. OpenSpellGEOSData.md covers all six sources, coverage, licenses and
full rebuilds. OpenSpellGEOSIntegrationIC.md documents the spelling ABI and
OPENUSER.USR format. OpenSpellGEOSIntegrationHT.md documents the IH/ET ABI and
wrapper repairs. This file gives the overall change record. Historical
BUILD_STATUS.md and selected logs distinguished passes from blocked checks in
the earlier evidence package; those files are not present in this repository.

## Deliberate limits

Suggestions scan at most four leaves per typed/folded neighborhood, eight in
total, and perform at most 48 exact correction probes. They retain a bounded
ranked list rather than the first matches. This is not a whole-dictionary
nearest-neighbor search. No runtime affix engine guesses
unlisted inflections or compounds. Words are limited to 64 GEOS SBCS bytes.
Thesaurus replacement strings retain the old UI's 26-byte limit. DBCS,
wildcard/anagram enumeration and proprietary grammar heuristics are outside
this replacement's implemented scope.

The compact byte ceiling additionally removes rare words, inflections and
senses. Correct omitted spellings can be flagged as unknown; missing THS/HYP
records provide no result. The ranking cannot guarantee retention of every
common word or sense. The full normalized source counts are not compact
binary counts.

Luxembourgish automatic hyphenation is still unavailable. Swedish breaks
cover compounds only. German, French and Swedish thesauri are specialist
terminology resources. The historical French wordlist and generated Swedish
forms require native-language editorial review. Those are data-quality and
coverage limits, not silently successful substitutes for complete language
support. See the data document for counts, vintages and the upgrade path.

The implementation is designed for segmented 16-bit systems and bounded
memory. Compiler checks, host tests and read-call counts do not prove physical
286/386 latency, an EC/NC UI pass, or an entire 640-KB Ensemble workload.
