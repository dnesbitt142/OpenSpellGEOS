# OpenSpellGEOS repeated spell-check dialog repair

The Spell controller now asks the specific UI to center its dialog instead
of retaining a position at 90 percent of the parent height. This avoids a
shared window-code defect that turns the previous dialog's absolute right
and bottom coordinates into its next width and height. The change is confined
to the GPC_SPELL dialog branch in Library/Spell/UI/uiSpell.asm, in
SpellControlGenerateUI. Existing CRLF line endings are preserved.

This is a placement change: the dialog opens near the center rather than near
the bottom of the screen. Its normal contents still determine its dimensions.
No fixed height, new window resource, extra memory allocation or specific-UI
binary is introduced.

## Reproduction with the released binary

The supplied screenshots show normal-sized controls grouped at the top of a
much larger outer frame. A fresh isolated NC Ensemble run reproduced that
appearance with the released OpenSpellGEOS compact geode and EN_GB data.

At 72-point Nimbus Roman, the first spelling dialog occupied approximately
(30, 418) through (447, 576) in the 800-by-600 framebuffer. After expanding
Suggestions, pressing Escape twice, selecting the document again and pressing
F7, the second frame occupied approximately (30, 0) through (478, 576).
The inner controls retained their original height. Thus the new frame's
dimensions closely match the first frame's absolute right and bottom
coordinates, rather than its original width and height. These are approximate
image coordinates, not a debugger dump of VI_bounds.

A separate 12-point control reproduced the same second-open growth without
ever expanding Suggestions. The sequence was a new document, text entry,
Ctrl+A, a 12-point font selection, F7, Escape, Ctrl+Home, Ctrl+A and F7.
Neither large document text nor opening the suggestion list is required.
The released EC binary also reproduced the growth through three openings at
72 points. That independently confirms the visible defect in both build types;
it is not inferred solely from the reported worker-exit trace.

The baseline captures are baseline72-check-first.png,
baseline72-check-second.png, baseline12-check-first.png and
baseline12-check-second.png in the runtime evidence. Exact action streams
and file identities accompany those captures. The EC comparison uses
baselineec2-check-first.png, baselineec2-check-second.png and
baselineec2-check-third-settled.png.

## Cause in the supplied shared UI source

The relevant source path is Library/SpecUI/CommonUI/CWin:

1. cwinClassOther.asm, OpenWinPrepForReOpen, sends
   MSG_OL_WIN_PREPARE_FIELD_SIZE_CHANGE when a window closes, even when no
   physical display-size change has occurred.
2. cwinClassMisc.asm, OLWinPrepareFieldSizeChange, converts left/top to ratios
   for WPT_AT_RATIO windows and sets WPSS_VIS_POS_IS_SPEC_PAIR. It replaces
   right/bottom only when the size policy itself is a ratio policy. With the
   Spell dialog's content-derived size, those fields retain absolute pixel
   coordinates instead of becoming independent pixel width and height.
3. cwinClassCommonHigh.asm, ConvertSpecWinSizePairsToPixels, must interpret
   right/bottom as independent sizes whenever any position or size spec-pair
   flag is set. It then adds the converted left/top to those sizes to recover
   rectangle coordinates. That invariant is correct for the normal hint
   conversion, but the close preparation above violates it.

The original SpellControlGenerateUI explicitly enabled the affected ratio
positioning with HINT_POSITION_WINDOW_AT_RATIO_OF_PARENT and a SpecWinSizePair.
The source path explains the observed growth on the second check, including
the unchanged dimensions of the child controls.

The narrow repair replaces that hint with HINT_CENTER_WINDOW, whose payload
length is zero, and removes the two ratio-coordinate assignments. The existing
geometry-hint scan remains. Center positioning avoids the faulty ratio-only
conversion during close preparation. The patch does not edit shared CommonUI
code or require replacing motif.geo or another specific-UI library. It is a
Spell-local workaround for the identified shared defect, not a system-wide
repair of every ratio-positioned dialog.

## Engine and thread lifecycle findings

The controller already clears SCI_ICBuffHan on exit. SuggestListReset clears
SLI_icBuff and initializes the list again. The context field receives plain
text and an underline style; it does not import the document's 72-point font.
Those paths did not justify an additional cache-reset or font-reset patch.

The supplied SWAT trace reports repeated creation and exit of Write's spelling
worker, including the displayed status 189. That number alone does not prove
a crash or a fatal error. The existing ICExit path intentionally requests
worker shutdown, and the next spelling session creates a worker lazily.
This repair does not change that thread structure or reinterpret the trace as
a demonstrated engine failure.

In ICS/icsThread.asm, GetHandleOfSpellThread passes SpellThreadClass to
MSG_PROCESS_CREATE_EVENT_THREAD through ProcessClass in the calling process
context, then stores the returned handle in ICB_spellThread. A Write-owned
event thread can therefore execute the spelling worker's code. SWAT reporting
"Thread 2 of write" is compatible with that implementation; it does not imply
that the spelling worker must belong to a separate Spell process. Identifying
that particular numbered thread would still require inspecting its class or
stack in SWAT. The source supports this compatibility, not a positive
identification of the reported Thread 2.

## Required assembler warning cleanup

The target build reported two conditional branches beyond the short-jump
range. The supplied Agents.md requires explicit LONG annotations for these
warnings. IH/ihCalls.asm now uses LONG jc markStatusError after the
HyphenOpen allocation, and UI/thesCtrl.asm uses LONG jnz getOneWord after
ThesControlGetStringToken identifies punctuation. These one-line annotations
retain the existing failure and token-selection paths; they make the branch
encoding explicit rather than relying on ESP's warning-producing rewrite.
Both files retain their CRLF line endings. This cleanup is separate from the
dialog geometry repair and does not change either routine's logic.

## Verification status

The prescribed EC/NC Spell build completed. The reviewed target rebuild uses
the explicit LONG branches above without double-jump or triple-jump warnings.
The rebuilt NC spell.geo is 42,034 bytes with SHA-256
13770fb852bfc5afefc74b171295cfa89a06664f5cccea26c9dd67cc90be7efb.

A fresh NC run at 72 points passed three successive dialog openings, including
explicitly expanding Suggestions and closing it before reopening spelling.
The first, second and third outer frames all occupy approximately
(192, 220) through (607, 380): centered, content-sized and without the previous
growth. The captures are patched72-check-first.png,
patched72-check-second.png and patched72-check-third.png in the runtime
evidence. These are observations of the rebuilt geode, separately preserved
from the failing released-binary captures.

A fourth check closed after 100 ms and reopened also returned to the same
normal frame, with This populated as the correction for Thjis. Selecting
Change replaced that first document word with This; the following dialog
reported the end of the current selection. The captures
patched72-check-rapid-reopen.png and patched72-corrected-result.png establish
these bounded checks. The replacement observation covers the first word,
not every proposed correction in the document.

A fresh 12-point NC control also passed three successive openings without
explicitly expanding Suggestions. It retained the same normal centered
bounds throughout. The captures are patched12-check-first.png,
patched12-check-second.png and patched12-check-third.png. This repeats the
baseline control sequence whose second opening previously grew.

The EC spellec.geo is 50,074 bytes with SHA-256
d5b57d6391dbe34405ba18de4f07bae54995c714ae9af517b90e56885ae4a51b.
Its fresh 72-point run also passed three openings and the 100 ms close/reopen
sequence, retaining the normal centered frame. The captures are
patchedec-check-first.png, patchedec-check-second.png,
patchedec-check-third.png and patchedec-check-rapid-reopen.png. No EC fatal
dialog was observed in these bounded checks. The reported candidate cases
also returned This, This, test and house first for Thjis, Tthis, teast and
hous respectively.

The runtime evidence includes separate baseline and fixed captures, action
streams, configurations and geode/data hash manifests. The tests used an
emulated 386 with 16 MB configured memory. They establish the observed dialog
repair and the exercised interaction paths, not physical 286/386 timings,
640 KB-only operation, complete multi-language acceptance or freedom from
all possible resource leaks.
