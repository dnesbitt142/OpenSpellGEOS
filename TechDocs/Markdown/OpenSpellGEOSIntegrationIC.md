# OpenSpellGEOS: GEOS spelling integration

This document describes the replacement spelling adapter and the personal
and ignore dictionaries. The shared OpenLex file specification and builder
instructions are documented separately. The new implementation is Apache-2.0
licensed. Existing GEOS source retains its existing copyright notices.

The 2026-09-30 corrective revision changes suggestion ranking, capitalization
and alternate bounds checks while preserving the public spelling ABI. The
language files remain byte-identical to the compact release and at most 500000
decimal bytes each. Omitted valid source words can still be unknown; see
OpenSpellGEOSData.md for retained counts and source limits. Current runtime
evidence is separate from the historical compact and full-corpus checks.

## Files and scope

Library/Spell/Open/icgeos.inc implements the private C entrypoints formerly
provided by the proprietary spelling engine. Library/Spell/Open/geosbridge.inc
and geosbridge.h implement GEOS file operations shared with the thesaurus and
hyphenation adapters. The portable reader is openlex.inc and openlex.h.

The .inc modules are ordinary C89 source included by Open/spellopen.c. This
single production .c file is intentional: the existing mkmf discovery would
otherwise compile both the aggregator and each module and introduce duplicate
symbols. Host-only tests use the .test suffix for the same reason.

The public spell geode export order, public assembly interfaces, ICBuff
allocation size and spelling-thread model are unchanged. The adapter uses the
existing CInclude/Internal/icbuff.h declaration with byte packing. Watcom
compile-time assertions check the important assembly-visible offsets:
ICB_word is 101, ICB_numAlts is 362, ICB_hctlBuff is 612 when anagrams are
compiled in, and ICBuff is 636 bytes in that configuration. The corresponding
values without the optional anagram word are 610 and 634. A mismatched layout
fails compilation instead of corrupting neighboring fields.

Each assembly-facing C entrypoint is _pascal _export. The _export macro maps
to __export __loadds in the supplied Watcom environment, loading the library's
DGROUP on entry and restoring the caller's DS before return. This is essential:
several assembly callers enter with DS pointing to a text buffer, and C code
uses library constants and shared state. Plain _pascal does not load DS under
the actual -ml -zdp build options. Generated 16-bit disassembly was checked for
DS setup and restoration and the 6-byte ICGEOSpl and 12-byte
ICGEOGetAlternate argument cleanup. Internal helpers retain ordinary _pascal.

## Existing assembly changes

Only previously disabled calls are enabled in ICS/spell.asm and
ICS/icsThread.asm. They connect initialization, cleanup, spelling, alternate
retrieval, personal-list add/delete/build/update, and ignore/reset to the new
code. Existing CRLF line endings are preserved.

One additional correction changes the delete-user CallCSpell return convention
from ax to axdx. The public API returns SpellResult in AX and UserResult in DX;
the former declaration incorrectly preserved DX in the DBCS wrapper. Add and
delete now both preserve the documented two-register result. No public ABI
changes are involved.

The pre-existing SLFUN optimized assembly routine remains unchanged. It is not
part of the new dictionary decoder and does not interpret any proprietary
content.

## Dictionary selection and I/O

OpenGeoName reads the existing [text] dictionary preference and defaults to
EN_US.DCT when the key is missing. It accepts only an ASCII DOS 8.3 basename
with letters, digits and underscore, followed by a three-character extension.
Path separators, drive names, wildcards, empty names and overlong names are
rejected. The three services share the same selected stem; DCT, THS or HYP is
substituted as required. Install the accompanying GDI entries and preference
settings so the old availability check also names the new dictionary.

The adapter temporarily enters SP_USER_DATA/DICTS and restores the thread's
previous directory on every path. A dictionary handle denies other writers
while open and is reassigned to the library owner, so a client process cannot
invalidate another service's file handle by exiting. Files are read at explicit
32-bit offsets; seeks and short reads are checked. The declared OpenLex file
size must equal the actual file size. The portable reader validates the binary
structure and lookup bounds.

ICB_hctlBuff owns a movable context. Every spelling call locks it, rebinds the
portable reader's user pointer to its current address, performs the lookup,
and unlocks it. No pointer into that context survives as a usable pointer
across an unlock. This is covered by a host test that relocates every block on
every final unlock. The separate read function pointer is also persistent:
OpenGeoRead alone is placed in the dedicated OpenReadCode resource. The portable
core invokes an ordinary far function pointer; movable GEOS code pointers
would instead require ProcCallFixedOrMovable. Keeping this tiny callback fixed
avoids a stale or virtual segment while keeping the portable core independent
of GEOS. Its distinct name matters: the supplied linker creates separate C
and assembly resources when both are named FixedCode, and the old declaration
marks only the assembly one fixed. spell.gp therefore explicitly marks
OpenReadCode fixed, read-only and shared. The rest of the bridge remains
movable CODE.

## Verification and suggestions

Input words contain at most 64 GEOS SBCS bytes. Longer input is returned as
invalid rather than truncated and accidentally accepted. Pure decimal digit
strings and words containing only recognized edge punctuation are accepted as
preprocessed nonwords. Text offsets retain the original byte positions and
report the inclusive last character, matching the existing possessive logic.

ASCII quotes and punctuation, GEOS smart quotes, guillemets, ellipsis and dash
characters are recognized at word edges. An internal GEOS right single quote
is normalized to ASCII apostrophe without changing byte offsets. Slash,
hyphen, dash and ellipsis presence is recorded for the existing assembly
subword fallback; that fallback intentionally retains its old language rules.

An exact dictionary key is tried first. Lowercase entries marked foldable may
also match ordinary title case or all capitals. Arbitrary mixed case is not
silently folded. Entries marked exact-case, such as mixed-case names, require
their stored spelling. The case map is the same one-byte GEOS map used by the
builder. Multi-character case expansions are not performed.

Successful consecutive identical folded words set the existing double-word
error flag. The existing ICResetSpellCheck clears its existing ICB_prevWord
field. A/an grammatical rules and the proprietary engine's undocumented
specialized grammatical heuristics are not reproduced.

The legacy suggestions UI calls ST_CORRECT with an empty input string and
loops while the result is IC_RET_FOUND. The adapter therefore uses the
retained ICB_word, fills the bounded alternate list, and returns
IC_RET_NOT_FOUND to indicate enumeration is complete. The populated list and
error flags remain available to ICGetNumAlts and ICGetAlternate. Returning
FOUND repeatedly here would hang the existing UI.

The reader ranks typed and lowercase lexical neighborhoods together. At most
four leaves per neighborhood and 48 exact probes for likely corrections are
examined. Direct probes cover deletion, adjacent transposition, doubled-letter
insertion and one-byte accent substitution. They can reach a dictionary entry
outside the local leaf window, including a missing initial accent. Every
candidate must actually exist in the selected dictionary; accent equivalence
is never used to accept an unaccented spelling automatically.

There are at most eight suggestions and at most 200 output bytes including
terminators. Folded optimal string alignment distance, with adjacent swaps
counting once, is the primary ranking criterion. Bounded mutation preferences
break ties; these are typing heuristics, not corpus-frequency estimates. See
OpenSpellGEOSFormat.md for the complete ordering and work limits. A separate
workspace belongs only to the spelling context. Filling its list does not stop
the search, so later better candidates can displace earlier poor ones.

Before displaying a candidate, the adapter retrieves its dictionary case flag.
A foldable lowercase entry follows the misspelling's ordinary title case or
all capitals. Exact-case entries, such as names and German nouns, retain their
stored form. Arbitrary mixed case does not impose a guessed pattern. Projected
duplicates are removed, candidate byte lengths remain unchanged, and alternate
offsets are rebuilt inside the existing ICBuff. GetAlternate rejects a word
whose NUL is outside its remaining buffer tail, even if a short prefix would
otherwise fit the destination.

The wildcard and anagram legacy exports remain callable but unsupported tasks
return IC_RET_INVALID with no alternates. They do not perform an unbounded
full-dictionary scan. Hyphenation and thesaurus requests use the separate
existing public APIs implemented by the other adapter. Supporting complete
wildcard/anagram enumeration would require an explicit resumable scan budget
and should be added as a separate enhancement.

## Ignore-list behavior

An ICBuff has its own 1024-byte ignore list. Entries are folded, nonempty,
1 to 64 bytes long and terminated by NUL. Adding an already ignored word has
no effect. ICResetIgnoreUserDict empties this client's list without affecting
other clients or persistent personal words.

If the list is full, the new entry is not inserted and ICB_retCode becomes
IC_RET_NOMEM. The historical ignore API returns no status, so the existing UI
cannot display that exhaustion directly. No unchecked append is permitted.

## Personal dictionary format

All six language selections share one personal dictionary, OPENUSER.USR.
It is independent of the old proprietary personal files. It is a native DOS
file with no GEOS file header, using the following byte layout:

- Offset 0, four bytes: ASCII OSU1.
- Offset 4, two bytes: unsigned little-endian payload byte count.
- Offset 6, two bytes: unsigned little-endian word count.
- Offset 8: payload, consisting of consecutive NUL-terminated words.

The file is exactly 8 plus the payload byte count, and at most 4096 bytes.
The maximum payload is therefore 4088 bytes. Every word is nonempty and
contains 1 to 64 GEOS SBCS bytes. Bytes 1 through 32 are rejected. NUL is only
a terminator. Words are in strictly increasing unsigned-byte lexical order;
duplicates are invalid. No implicit padding or trailing unused memory is
written. There is no checksum in this small personal-file format; complete
structural validation is required before accepting it.

Original spelling case is preserved in the file and returned list. The
existing Edit User Dictionary UI searches for the exact string it just added,
so folding the stored/displayed form would break that UI. Spelling checks
compare personal entries case-insensitively. A duplicate exact add reports
UR_WORD_ALREADY_ADDED; deletion requires the exact listed spelling. The
existing UI obtains that spelling from the returned list.

One library-owned movable 4096-byte personal table is shared by all initialized
ICBuff instances. The existing spellSem serializes load, lookup, mutation and
list creation. This small shared state is intentional: separate cached copies
would lose changes made simultaneously in Writer and Preferences. It is freed
when the last ICBuff closes and reloaded on the next initialization.

## Persistent updates and recovery

Each successful add or delete is saved synchronously. UpdateUserDictionary
has no deferred work. Mutations are made in a separate 4096-byte temporary
memory block. The original live block is replaced only after disk publication
succeeds; allocation, write, commit, close or rename errors return failure and
leave the live personal table unchanged.

The commit sequence is as follows:

1. Write the complete candidate to OPENUSER.TMP.
2. Commit and close the temporary file successfully.
3. If OPENUSER.USR exists, remove the older OPENUSER.BAK and rename the live
   USR file to BAK. The backup is not removed when it is the only saved copy.
4. Rename TMP to USR. If this fails after moving USR, attempt to rename BAK
   back to USR. Even if that rollback fails, the BAK copy is retained.
5. Publish the replacement memory block only after the final rename succeeds.

At initialization a missing USR permits recovery from BAK. A malformed,
unreadable or otherwise erroneous existing USR does not silently fall back or
become an empty dictionary: initialization fails with the user-dictionary
error flag. If neither USR nor BAK exists, initialization starts an empty
personal list. A leftover TMP is never automatically trusted.

The semaphore serializes users of this loaded spell library, not external
editors. Personal files must not be edited or replaced externally while a
spell session is active. DOS rename and commit cannot guarantee survival of
all physical media failures or abrupt power loss; the retained BAK and strict
read validation provide recovery within those platform limits.

## Memory and performance boundaries

The reader and scratch buffers are allocated in handles, not on the stack.
With the supplied 16-bit compiler and byte-packed structures, a spelling
context is 4996 bytes (about 4.9 KiB), verified by the Watcom size probe. It
includes the 2969-byte reader, two-byte file handle, two-byte ignore-list size,
1024-byte ignore list, 65-byte folded word, 734-byte suggestion workspace and
200-byte output scratch. The reader includes a fixed 1024-byte index-page
cache and seven upper binary-search nodes. A compile-time assertion caps the
complete spelling context at 8192 bytes. The 734-byte workspace belongs only
to spelling; IH and ET do not allocate it.

An ICBuff remains 636 bytes in the normal build. The shared personal table is
4 KiB; a mutation temporarily needs one additional 4 KiB block. Building the
public personal-word list temporarily allocates at most 4 KiB for its required
copy. One active client's persistent data totals 9728 bytes before allocator
overhead: 4996 context, 636 ICBuff and 4096 shared personal table. No individual
allocation exceeds 8 KiB. These buffers are swappable and shared under GEOS
memory management. Relative to the preceding compact release, the per-client
context grows by 735 bytes: the 734-byte spelling workspace and one cached
last-key length in the common reader.

The existing 2500-byte spelling-thread stack is unchanged. The largest adapter
local array is 65 bytes. Lookups use the indexed dictionary reader and bounded index cache, with no
full-file load or decompression buffer. Personal and ignore lookup are linear
only over their explicit small memory bounds. Suggestions use bounded block
reads and bounded edit-distance work. Existing library/thread/kernel overhead
and the application's document memory are additional; host tests do not
establish that an entire Ensemble workload fits a particular 640 KiB machine.

## Verification

The supplied Open/test_icgeos.test includes the actual production adapter with
host-only memory, file and lexical-reader shims. It covers initialization,
forced block relocation, casing, punctuation offsets and smart apostrophes,
double-word flags, empty-input suggestion completion, jointly ranked real-data
corrections, title/all-cap projection, exact-case preservation, duplicate
removal, every alternate-tail offset, ignore/reset, display-case preservation, cross-client
personal changes, short-write/commit/rename rollback, corrupt-file rejection,
backup recovery ignore-list exhaustion, allocation-failure cleanup and complete handle cleanup.

From Library/Spell/Open, run:

    cc -x c -std=c89 -Wall -Wextra -Wno-unknown-pragmas \
       -I../../../CInclude test_icgeos.test -o test_icgeos
    ./test_icgeos /absolute/path/to/DICTS

The test compiler and malloc/free are used only in this host fixture. Production
code uses the GEOS memory APIs exclusively. The fixture cannot replace actual
16-bit EC/NC compilation, assembly/link verification, GEOS UI interaction,
segmented-memory execution or hardware timing. See the main build report for
the exact validation achieved with the attached toolchain.
