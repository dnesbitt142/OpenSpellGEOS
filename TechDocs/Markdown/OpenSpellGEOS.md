# OpenSpellGEOS for PC/GEOS Ensemble

OpenSpellGEOS replaces the unavailable proprietary implementation behind the
existing Spell library entry points. It supplies an on-disk lexical reader,
GEOS adapters, dictionary builders, and separately attributed language data.
The public Spell export order, buffer layouts and Preferences interface remain
intact. The thesaurus adds part-of-speech value 4 for unknown grammar; its UI
is updated accordingly. External clients must guard against that value before
indexing an old four-element grammar table.

The new source is Apache-2.0. Data retains the notices and permissive terms of
its sources; compatibility with an Apache-2.0 project does not erase those
notices or turn every upstream dataset into an Apache-2.0-licensed work.
See the delivered data provenance and license files before redistributing.

## Repository layout

Paths in these guides are relative to the OpenSpellGEOS repository root unless
a different working directory is stated.

- Library/Spell contains the library source; Library/Spell/Open contains the
  runtime C reader, adapters and spelling host fixture.
- Installed/Library/Spell contains the matching build overlay.
- Dictionaries contains six language ZIPs, each with one language folder and
  its DCT, THS, HYP and GDI files, plus BUILD.json, NOTICES.TXT and LICENSES.
- Dictionaries/BuildTools contains the Python builders and checks.
- Dictionaries/BuildTools/Sources contains acquisition and normalization scripts,
  provenance manifests and upstream notices.
- Dictionaries/BuildTools/Data.zip contains the normalized Data directory;
  extract it beside the archive before rebuilding the six-profile data set.
- TechDocs/Markdown contains these guides.

Copy the Library and Installed overlays to the matching PC/GEOS source root
when building the geode. Keep the data tools in their repository locations;
they are separate from Library/Spell/Open. The repository does not include
BUILD_STATUS.md, earlier build logs or runtime screenshots. Historical
evidence mentioned below refers to the earlier integration package.

## Read first

This is a replacement implementation requiring integration validation, not a
claim of completed testing on a physical 286. Historical build evidence is
separate from this repository. Host-side tests, target C compilation, a linked
geode, and a successful EC/NC boot are distinct checks and are reported
separately.

The 2026-09-30 corrective revision addresses the reported suggestion and
repeated-dialog failures with unchanged compact language files. It jointly
ranks candidate searches, probes likely typing errors and missing accents,
preserves display capitalization, and uses centered dialog placement to avoid
the shared UI's ratio-position reopen defect. The public Spell ABI and OLX1
file format are unchanged. See OpenSpellGEOSChanges.md for the complete delta
and OpenSpellGEOSDialogFix.md for the window's causal diagnosis.

Current build and runtime evidence records the baseline failures and revised
checks separately. Historical full-corpus and earlier compact smoke tests
retain their original binary/data identities. Read the accompanying current
BUILD_STATUS.md and runtime results for the precise verified scope. No emulator
check is presented as physical 286/386 timing or exhaustive language review.

Six filenames identify six independently selectable language profiles:
EN_US, EN_GB, DE_DE, SV_SE, LB_LU, and FR_FR. Each profile uses a .DCT, .THS,
and .HYP file with the same stem. Consult the coverage report for the size,
vintage and linguistic limitations of each supplied data source. Dictionary
coverage is finite; uncommon inflections and productive compounds absent from
the input list are not automatically accepted.

## Compact release policy

Every distributed .DCT, .THS and .HYP file must be at most 500000 bytes,
inclusive. This is 500,000 decimal bytes per file, not 500 KiB, and includes
the complete header, index, leaves, padding and external values. The ceiling
applies separately to each of the eighteen linguistic files. GDI records,
notices and build reports accompany them; they are not dictionary payloads.

The compact release selects vocabulary and thesaurus records before writing
the existing OLX1 format. The corrective runtime uses those same files without
a data migration or public binary ABI change.
.DCT remains the canonical spelling-dictionary extension, with .THS and .HYP
for the corresponding services. The Library/Spell/Open source directory and
the original Spell library exports retain their technical names.

Selection follows pinned language-specific rankings, prioritizing manually
chosen common/function words and then the documented source signals. These
signals differ by language and are not equivalent to a modern general-purpose
frequency corpus. See OpenSpellGEOSData.md for the ranking rules, retained
counts and measured output sizes.

Fitting a fixed byte budget loses rare vocabulary, inflections, specialist
terms and some senses. An omitted correct spelling can be flagged as unknown,
an omitted thesaurus headword has no result, and a word absent from the HYP
file has no automatic break. Smaller files do not remove the need for native
language review or correct gaps in the underlying sources.

The compact release audit verified all 611,367 retained records and all
eighteen complete file sizes. They total 7,234,896 decimal bytes, with each
file at or below the ceiling. Per-file counts, omissions and exact sizes are
in OpenSpellGEOSData.md and BUILD.json.

## Design and memory

The reader uses sorted, front-compressed leaves and a sparse disk index. It
never loads a complete dictionary into conventional memory. Each reader caches
one 1024-byte leaf, one 1024-byte index page, and seven index records for the
top three binary-search levels. All caches are bounded independently of file
size. All file integers are decoded explicitly;
compiler structure packing and native byte order cannot change the format.

The GEOS adapters own contexts in movable GEOS memory blocks. Locks cover the
operation that uses a far pointer. The common reader has no heap allocator
and performs I/O through a supplied callback. There is no recursion in target
lookup, and no requirement for a flat address space, DOS extender, floating
point, malloc, or a 386 instruction set.

Actual Watcom 16-bit, packed, large-model allocation sizes are:

| Object | Bytes | Lifetime |
| --- | ---: | --- |
| Reader context, included in each engine below | 2969 | One open file |
| Spelling state, including reader and ignore list | 4996 | One ICBuff client |
| Hyphenation file state, including reader | 2971 | One hyphenation client |
| Thesaurus state, including reader and payload buffer | 7132 | One thesaurus client |
| Shared personal dictionary | 4096 | Spell library session |
| Personal dictionary edit copy | 4096 | One synchronous edit |

Existing public control buffers and GEOS file/heap bookkeeping are additional.
The largest new state allocation is below 8 KiB. States are library-owned and
sharable where required, and are unlocked outside active operations. The read
callback occupies fixed code because its pointer persists across operations.

The final link separates the common reader (OpenLexCode), correction routines
(OpenSuggestCode) and spelling adapter (CODE). NC sizes are 3354, 3492 and
4683 bytes respectively; EC sizes are 5522, 4932 and 6771 bytes. All code
resources are below 8 KiB. The fixed read callback is 89 bytes in NC and 139
in EC. The complete library's reported fixed resource payload is 930 bytes NC
and 980 bytes EC, including pre-existing fixed resources. Shared immutable
case/accent tables remove 87 duplicate source data bytes; DGROUP occupies
224 bytes after target linking. Resource measurements are distinct from heap
allocations and physical memory use including GEOS bookkeeping.

The final NC geode is 42034 bytes and EC is 50074 bytes. Both compile with zero
C warnings or errors; the two reported Spell assembler short-jump warnings
are resolved with explicit LONG annotations. Actual target disassembly checks
DS save/load/restore and the Pascal cleanup widths, including GetAlternate's
12-byte parameter frame. Detailed resource tables, hashes and size probes are
in the current build evidence.

A historical full-corpus callback-count experiment over 200 random real words reduced
warm English reads from 11.69 to 4.955 per query and German reads from 16.04 to
10.01. It trades more transferred bytes for fewer seek/read calls. These are
I/O call counts, not timings on a 286; see the format document and build log.

The platform build normally selects -3. Spell/local.mk sets the final EC and
NC optimization options to include -0, so the target compiler emits the 8086
instruction baseline. This is compatible with a 286. CPU compatibility alone
does not prove adequate free RAM: an Ensemble installation, desktop, text
application, fonts, document and drivers also compete for the 640 KB address
space. Measure free handles, free conventional memory and latency on the
intended installation before release.

Suggestions rank bounded typed/folded neighborhoods and at most 48 exact
probes for likely typing errors and missing accents. They emit only the closest
edit-distance tier found. This bounds work and scratch memory but is not an
exhaustive search of every word. A correction outside the examined regions and
probes may receive no suggestion. The dictionary format does not
discard words to meet this runtime suggestion bound. The separate compact
selection can omit words to meet the on-disk byte ceiling.

Hyphenation runs by exact lookup of precomputed legal break positions. The
host builder can apply permissively licensed Liang patterns to the selected
spelling vocabulary; the 286 does not run the pattern matcher. Exceptions can
supply or override positions. Unknown words receive no discretionary break.
This intentionally favors avoiding a wrong line break over guessing one.
No language inherits English patterns merely because its own patterns are
unavailable.

The SBCS GEOS character set is the target encoding. Builders accept Unicode
UTF-8 input and reject or explicitly report unrepresentable input. This is
not a DBCS implementation. Case conversion is a one-byte mapping, not Unicode
case folding with character expansion. See the format document for exact
encoding and flag semantics.

## Installing data and selecting a language

Back up the existing Spell geode, geos.ini, and DICTS directory. Close Ensemble
before replacing a loaded library. Test EC and NC separately with their
matching library builds. Do not install a host object file as a .geo file.

Unpack the selected language ZIP from Dictionaries into a temporary location.
Each archive contains a language folder, such as English_UK or Luxembourgish.
Copy that folder's .DCT, .THS, .HYP and .GDI files directly into
Ensemble/USERDATA/DICTS. Multiple profiles may coexist. Each profile's three
compact linguistic files together use at most 1500000 decimal bytes, plus its
small GDI record and accompanying notices. Install only the profiles needed.
Retain NOTICES.TXT and LICENSES with copies. The build helper includes those
notices automatically. The lookup path uses SP_USER_DATA (the same standard
path as SP_PUBLIC_DATA).

Select a supplied dictionary through Preferences. The .GDI parser writes the
existing [text] language, dialect, languageName, and dictionary keys and asks
for a restart. For example, an American English selection is:

    [text]
    language = 16
    dialect = 128
    languageName = American English (OpenSpellGEOS)
    dictionary = EN_US.DCT

The common bridge derives .THS and .HYP filenames from that selected dictionary
stem. Restart after changing languages so all cached engine contexts close.
The new engines do not use the old proprietary thesaurus or hyphenation
filenames as an alternate data source. If no dictionary key exists, the
new default is EN_US.DCT. A stale explicit .DAT dictionary setting must be
changed through Preferences; it is not silently interpreted as an OLX file.

British English uses the -ise spelling profile. EN_US.HYP and EN_GB.HYP remain
separate because the chosen pattern sets and spelling vocabularies differ.
French, German and Swedish use the existing language codes 5, 6 and 7.
Luxembourgish uses SL_UNIVERSAL (0) for the legacy language byte because this
source tree has no Luxembourgish language identifier. LB_LU.DCT is the actual
language selector; no unrelated system enumeration is changed.

GDI is the existing five-line record format: dictionary filename, display
name, description, decimal language code, decimal dialect code. Files use
CRLF. Text is Latin-1 as required by PrefMgr's GDI reader. Each supplied
record fits its existing 64-character name and 256-character description
limits, and each GDI remains below the reader's 8000-byte file limit.

## Building and validating data

See OpenSpellGEOSFormat.md for the byte-accurate DCT/THS/HYP format, strict
source schemas, builder commands, and portable reader tests. The normalized
source snapshots are packaged in Dictionaries/BuildTools/Data.zip. See
OpenSpellGEOSData.md for extraction and commands from this repository root;
ordinary data rebuilding requires no network access.

Changing a source dataset requires reviewing its license again, preserving
notices, recording the source version and checksum, rebuilding the files,
and running the verifier. Do not feed GPL, LGPL, share-alike, noncommercial,
or otherwise incompatible lexical data to a distributable Apache-compatible
build merely because the conversion tool itself is Apache-2.0.

## Building the library on Linux

Follow the supplied README's toolchain sequence. Expand the provided
OpenWatcom archive at the chosen WATCOM root and the supplied PC/GEOS source
at ROOT_DIR. The normal paths are /opt/open-watcom-v2 and ~/Geos/pcgeos.
Set WATCOM, ROOT_DIR, LOCAL_ROOT=$ROOT_DIR/Local, BASEBOX=basebox, and prepend
$WATCOM/binl:$ROOT_DIR/bin to PATH. Preserve existing environment variables;
do not repurpose HOME.

Run these steps in order:

    cd "$ROOT_DIR/Tools/pmake/pmake"
    wmake install
    cd "$ROOT_DIR/Installed/Tools"
    pmake install
    cd "$ROOT_DIR/Installed"
    pmake
    cd "$ROOT_DIR/Tools/build/product/bbxensem/Scripts"
    perl -I. buildbbx.pl

Use the documented buildbbx answers: nt, y for EC, n for DBCS, y for geodes,
n for VM files, and the absolute LOCAL_ROOT path. Keep the errors as well as
the exit status: this script can report completion despite missing geodes.
Set up xdotool and DOSBox or pcgeos-basebox as instructed in the supplied
README before attempting debugger/target validation.

Copy this repository's Library and Installed folders into ROOT_DIR, merging
with the existing PC/GEOS tree. The runtime source stays in
Library/Spell/Open; the Python tools and linguistic files do not belong in the
Installed build. After applying this overlay, regenerate the Spell build in
the matching Installed folder because a C translation unit and dependencies
were added:

    cd "$ROOT_DIR/Installed/Library/Spell"
    yes | clean
    mkmf
    pmake depend
    pmake -L 4 full

Do not hand-edit Makefile or dependencies.mk. Keep EC and NC outputs separate.
No prebuilt SDK Spell binary demonstrates compilation of these changes.
The build logs document any host architecture and path adaptations made in
this workspace and state precisely which stages actually completed.

## Required target acceptance checks

Boot an EC installation with the new EC geode. Check words and suggestions
with each profile, including accents, German initial capitals, British versus
American variants, empty strings, a 64-character word and longer input.
Exercise punctuation and repeated-word behavior through a text application.
Repeat the normal user flow with NC after EC is clean.

Add a word to the user dictionary, close/reopen the document, restart Ensemble,
and confirm persistence. Delete it and verify persistence again. Test a full
user list, a write-protected DICTS directory, a failed save and a malformed
user file. Failure must not overwrite valid saved data.

Look up multiple meanings and synonyms in succession, including a missing
word and a long word. Hyphenate known source examples and long words spanning
bitmap positions 16, 32 and 48. Verify no break for an absent word. Confirm
that returned hyphenation positions agree with the text engine's contract.

Rename or truncate one data file, try an incorrect-kind file under the right
extension, and verify a clean error rather than stale results or a crash.
Repeated open/close and language changes should not leak handles. Measure
cold and warm lookup latency and peak memory on a 286 and low-end 386 with
640 KB configured; host timings are not substitutes for those measurements.

## Proprietary reference inputs

The proprietary dictionary and hyphenation files were used only for their
ZIP directory sizes: IENC9123.DAT is 218112 bytes and HECDP301.DAT is 107520
bytes. No lexical content, binary structures, extracted words or derived
patterns from those files are used. COM_THES.DIS was described as 302848
bytes by the supplied report; that file is not in Archive.zip, so its size
is a reported comparison rather than a measured attachment value.

ENGLISH.GDI was read to understand the existing public Preferences record
format and codes. The supplied German web page could not be fetched (HTTP
502); no implementation claim relies on unseen contents. The existing source
and supplied interface headers are the ABI authority.
