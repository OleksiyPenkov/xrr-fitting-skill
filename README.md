# An XRR fitting procedure for a laboratory LLM agent

A written procedure for fitting a measured X-ray reflectivity curve, elicited from an expert at the
keyboard and written so that a language-model agent can follow it without further instruction.

This is the artifact studied in "Teaching a laboratory LLM agent a tacit procedure: an XRR fitting
skill" (Penkov, Peng, Fu). It is published separately from the paper because it is usable on its own,
and because a reader who wants the procedure should not have to extract it from a supplement.

## What it contains

One file, `xrr-fitting-skill.md`: thirteen numbered sections, a 22-item report template as section 13,
and the laboratory's own constants marked in place with the words "this laboratory". Nothing else is
needed to run it.

The procedure covers what a fitting engine does not: where to put the normalization point, how far to
trim, what to free and in what order, when to change the resolution, when a profile fit may replace a
periodic one, and when a fit may be accepted. Those decisions are the ones no engine and no manual
specifies, and they are what an operator supplies from practice.

## What was tested, and what was found

Six fresh agent sessions and one autonomous agent fitted two Co/C multilayer curves under this
procedure, blind, against fits the expert had made and withheld. Every fitted thickness agreed with
his within 0.03 nm. The procedure was then applied to six published Ru/C curves in twelve sessions,
and every period layer agreed within 0.1 nm.

The negative result matters more for anyone reusing this. **The conditioning steps transferred between
the two material systems. The rules of verdict did not.**

## Known limits, in the order they will bite you

1. **The acceptance threshold does not transfer.** The rule "chi-squared under 10" was calibrated on
   Co/C curves of four orders to 4.2 degrees. On Ru/C curves of ten orders to 6 degrees it rejects fits
   that are correct, including the expert's own. Recalibrate it for your curves, or read an unweighted
   chi-squared instead.
2. **The roughness assignment within a period is decided by the optimizer seed, not by the data.** Two
   fits started from opposite structures return the same answer, and the two roughnesses of a
   two-material period can swap without changing the peaks. Do not use the assignment as a pass
   criterion.
3. **The density bounds and start values are written for Co/C.** They were carried unchanged into the
   Ru/C test on purpose, to see what would happen. For a new material pair, rewrite them.
4. **The constants are this laboratory's.** The substrate model, the wavelength, and the resolution
   interval are marked "this laboratory" in the text. The rules around them are general; the numbers
   are not.
5. **It is written in angstroms and it names the tools of one particular server.** The physics is
   portable; the vocabulary is not. Expect to translate.

## Versions

Four texts were used. They are in `versions/`, each the procedure exactly as a session received it.

| Version | Used by | Characters | sha256 (first 12) |
|---|---|---|---|
| `v1-stage1-round-1.md` | Co/C qualification, round 1 | 11731 | `18200bf17917` |
| `v2-stage1-round-2.md` | Co/C qualification, round 2 | 11930 | `e53695c64601` |
| `v3-stage1-round-3.md` | Co/C qualification, round 3 | 13119 | `5b864e9fe74e` |
| `v4-transfer-final.md` | all twelve Ru/C transfer sessions | 15832 | `8c515f3d5a25` |

`xrr-fitting-skill.md` is byte-identical to `v4-transfer-final.md` and is the version to use.

What changed between them: v2 stated the per-material density bounds explicitly and narrowed the band a
session applies to its own orders from a factor of two to 25 percent; v3 moved the judgment of a fit onto
the report the server returns; v4 added a carbon surface layer to the starting model and rewrote the
rule governing when a profile fit may replace a periodic fit, so that a passing periodic fit is final.

## Provenance

The procedure was recorded during the expert's own fitting session, condensed, and given to the agent as
a single written intervention. It was not written by an agent and then approved; it was elicited from a
person who had never written it down.

The sessions that ran it, the fits they produced, the curves, and the expert's reference fits are in the
paper's data deposit, which is published with the paper.

## How to cite

Cite the paper for the method and this repository for the artifact. A DOI is minted when a release of
this repository is archived, and will be recorded here and in `CITATION.cff` when it exists.

## License

Creative Commons Attribution 4.0 International (CC BY 4.0). Full text in `LICENSE`.

You may use, adapt and redistribute this procedure, including commercially, provided you give credit.
Adapting it is the expected use: the limits above say which parts are this laboratory's and will need
replacing.
