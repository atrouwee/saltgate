# What changed

Written for photographers, not from the commit log. Versions marked **renders
change** will make your files look different; everything else is the tool
around them.

Full technical history: `luts/CHANGELOG.md` for the LUTs themselves.

## 0.5.1 — it runs on Windows
A photographer tried to install it on a PC and the second line of the
instructions — `saltgate` — came back as an unrecognised command. It wasn't
their mistake: there was no Windows installer. The one-liner in the README
needs `curl` and `sh`, and Windows has neither, so nothing was ever installed
and step 2 had nothing to find.

**There is now a PowerShell installer**, and the README gives it as its own
line next to the Mac one, with a short note about what to do when a terminal
still says the command doesn't exist (nearly always: open a new window). It
installs the same way — uv, its own Python, the 47 MB orientation model
checked against the same digest — and it doesn't need git, which most PCs
don't have.

Three quieter things that had also only ever run on a Mac. **The walkthrough's
arrow keys work**, and with them the review of frames it wasn't sure it turned
the right way up: that review was switched off by the same missing piece, so
Windows users were losing the one question the tool cannot answer for itself.
**Long grades no longer stop when the machine sleeps.** And **the roll is
graded on as many workers as the machine can hold** — how much memory a PC has
was never actually measured, so every one of them, and every Linux machine,
was grading a whole roll one frame at a time.

And the text files. Windows decodes with the machine's legacy code page unless
it is told otherwise, so anything carrying this walkthrough's own characters
failed there — including the crash log, which quotes the source and so failed
at exactly the moment it was most wanted. Every file the tool reads or writes
now says utf-8 out loud, a redirected `saltgate > log.txt` no longer stops at
the banner, and a test refuses to let the next file forget.

Nothing about the renders changed. Windows is now in the test matrix
alongside macOS and Linux, including a run through the installed command
itself, so this can't quietly rot again.

## 0.5.0 — the black point, returned to you — **renders change (if you use it)**
The lab chose a black point per frame, and measured across all 67 donated
pairs that choice is most of what still separates these LUTs from the lab's
own files — on the 250D default it is the difference between ΔE 4.7 and 1.0.
No model reads it from a flat (we tried three; all failed honestly), so the
walkthrough now hands it to you: a **blacks step** flags the frames the lab
would have pressed — dim, neutral, detail in the shadows — shows each at
three depths, and takes your choice per frame or one depth for the whole
roll. Skip it and nothing changes. The same guidance is written up in
USING_THE_LUTS.md for people applying the cubes elsewhere.

Also: a **demo roll** — six downscaled flats from the maintainer's own film,
one `curl` away, so the walkthrough can be tried without owning a SILBERSALZ
roll. And the grader now sizes itself by the memory your machine actually
has free (not what it theoretically contains), pausing rather than freezing
a busy machine mid-roll.

## 0.4.0 — a new stock, and a tripwire — **renders change**
Two things, both born from one donation. **Kodak ColorPlus 200 joins the
stocks** — 13 flat/graded pairs of a Cairo roll (thanks @_.cherrymy) were
enough to fit a first LUT: held-out frames land within ΔE 4.9 of the lab's own
grade, the same class as the 250D default. Honesty in full: one roll, one
donor, and the roll was pushed +2 stops, so this is *pushed* ColorPlus under
the lab's grade — a normal-dev roll will differ.

And the walkthrough now **checks your roll against the pairs behind the look**
before the density step. The donation arrived labelled as a different stock,
and the engine caught it only because we went looking — now the tool looks
every time. Wrong stock or a pushed/pulled roll measures 2–3× outside the
look's envelope and gets a plain warning; honest rolls pass with room to
spare. (The film base itself can't tell — the lab normalised every scan; we
measured that too, and the dead end is recorded in FINDINGS.)

## 0.3.2 — credit where it was owed
Documentation only. The donors are now named in full — the footer had credited
only two of the four; Sebastian and Lukas Walter, whose 250D pairs stand behind
the default look itself, were missing. A dedicated callout says what each
donation bought. And a short "How it was built" section states the ledger:
ten hours of one photographer's judgement steering fifty hours of AI work.

## 0.3.1 — the walkthrough, shown
Documentation only; nothing about your files changes. The README now opens the
walkthrough with a picture of it — the guided flow, what's automatic and what's
yours to choose — and says plainly that it is how the maintainer grades his own
rolls. New hero image rendered with the shipped default.

## 0.3.0 — the film edge, cropped like the lab did · **renders change**
Your graded frames are now **cropped** by default — just outside the picture,
keeping the camera gate's rounded corners and a sliver of film. The lab did
the same before grading: an uncropped grade renders the unexposed rebate near
white (L\* 77–96 measured, against the lab's own L\* 6 borders). The walkthrough
previews all three treatments on your own frames — just outside · film edge ·
whole scan — and whichever you pick, the crop is **centred on the film itself**:
35 mm rarely sits square on the strip, so a scan-centred crop leaves a dark bar
down one edge. After grading it reports what happened ("88 cropped, 61
re-centred, 5 left whole"). Choose *whole scan* and nothing is cropped at all.

A third 250D look joins the picker: **cooled hybrid** — the default with its
colour cooled toward the maintainer's 668-frame graded archive, the amount set
by measurement rather than by eye. Same fidelity to the 22 real pairs as the
default; about 1 ΔE apart, all colour. The archive-matched look's description
now carries its exact provenance: 668 frames, 16 rolls, Sep 2022–Mar 2026, all
APOLLON-era; 180 frames on a Canonet QL17, 488 on a Contax T2.

Also: a new hero image rendered with the shipped default, and a new line under
the name — *we couldn't ask the lab, so we asked the frames.*

## 0.2.1 — check the frames it wasn't sure about
Auto-rotation is right about 95% of the time, and it knows which frames it is
unsure of: on a test roll, five of the six it got wrong were among the six it
was least confident about.

So it now asks. The handful it is unsure of get graded small and on their own —
a second or two, not the full run — into `check-upright.jpg`, and you answer one
question per frame: already upright, turn left, turn right, upside down. The
full roll grades the whole time you are looking, and each question shows how far
it has got. Anything you turn is re-graded at the end.

Nothing about how your files look has changed.

## 0.2.0 — 250D fitted on the lab's own files · **renders change**
The default 250D LUT changes. Your 250D frames will look different: warmer and
lighter than before, and less green in the neutrals.

It is fitted on 22 real flat/graded pairs from two photographers across four
rolls — and most of those pairs are now the lab's original 16-bit files instead
of re-compressed JPEGs. That mostly buys a cleaner *measurement*: given its own
exposure per frame the fit now reads 0.8 ΔE2000 against the lab, which the
previous version could not show because its own reference files carried
compression error. The rendering itself moved very little.

If it reads too warm on your roll, the previous look is still there: pick
**archive-matched** in the walkthrough, or `saltgate apply --look 250d:proxy`.
Neither is provably right for a roll we have no pairs from, which is why the
walkthrough shows you both on your own frames before writing anything.

Also: every prompt now moves with ← → ↑ ↓ and explains each option as you land
on it, and density is a scale you slide rather than a list of numbers.

## 0.1.25 — arrow through it
Every choice in the walkthrough now moves with ↑↓ and confirms with Enter — film,
look, density, yes/no. Typing the number still works. The 250D look selector
explains each option as you land on it instead of stacking both explanations
above the choice. And the restart after a self-update finally says what it did,
instead of replaying "checking for updates" when it wasn't.

## 0.1.22 — 16-bit, and a density you can set
If the lab gave you 16-bit scans (`.jxl` / `.jp2`), the walkthrough can now read
them at all — it used to only accept `.jpg` and told you the 16-bit files were
the graded ones, which was wrong. Feed it 16-bit and you get 16-bit TIFF back,
or JPEG if you'd rather.

New optional step: **per-roll density**. The lab set print density per roll and
a colour transform cannot know what yours was — it is the single biggest
difference left between our render and the lab's. Five-step ladder on your own
frames, skipped with one Enter.

## 0.1.21 — 250D fitted on real pairs · **renders change**
250D stopped being an estimate. Fitted on 22 flat/graded pairs from two
photographers instead of inferred from graded frames alone.

## 0.1.23–0.1.24 — 250D back to the safer default · **renders change**
And then reverted, honestly. On the donated pairs the new fit is much closer to
the lab; on the author's own rolls it renders noticeably warmer, and we cannot
measure which is right for *your* roll without pairs from it. The estimate is
the default again; the pair-fitted version is one keypress away
(`--look 250d:paired`). Both are described for what they are.

## 0.1.19 — pick your look, and no more PyTorch
Auto-rotation used to install 529 MB of PyTorch mid-walkthrough and then restart,
losing every answer you had given. It now runs a 47 MB model through the
libraries already installed. No install, no restart.

Where a stock has more than one credible LUT, the walkthrough renders them side
by side on six of your own frames and asks.

## 0.1.18 and earlier
500T refit with a corrected black point; the first 50D LUT; the guided
walkthrough; the first Gold 200 and 250D LUTs. See the releases page.
