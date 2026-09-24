# An XRR fitting procedure for a laboratory LLM agent

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22851595.svg)](https://doi.org/10.5281/zenodo.22851595)

A written procedure for fitting a measured X-ray reflectivity curve, elicited from an expert at the
keyboard and written so that a language-model agent can follow it without further instruction.

This is the procedure studied in "Teaching an LLM agent to fit XRR curves with X-Ray Calc 3" (Penkov, Peng,
Fu, 2026). It is published separately from the paper because it is usable on its own,
and because a reader who wants the procedure should not have to extract it from a supplement.

## What it contains

- `xrr-fitting-skill.md`: the procedure, thirteen numbered sections with a 22-item report template as
  section 13. From version 2.0 the text carries no laboratory constant: every instrument, substrate,
  material and threshold value comes from a preset file.
- `presets/csmic-empyrean.json`: this laboratory's preset (PANalytical Empyrean, Cu tube, parallel-beam
  mirror), with the ground of every value written beside it.
- `substrates.json`: the substrate library the preset names.
- `preset.schema.json`, `substrates.schema.json`: the schemas a preset and a substrate library must
  validate against.
- `validate_preset.py`: checks a preset and its library (schema, ordering of bounds, start values inside
  their bounds, the substrate resolving). `--check-materials` also asks the X-Ray Calc 3 tool server which
  materials its table knows; set the environment variable `XRC_MCP` to the server's path.

To use the procedure on another instrument, write a preset of your own and validate it:
`python validate_preset.py presets/your-preset.json`.

The procedure covers what a fitting engine does not: where to put the normalization point, how far to
trim, what to free and in what order, when to change the resolution, when a profile fit may replace a
periodic one, and when a fit may be accepted. Those decisions are the ones no engine and no manual
specifies, and they are what an operator supplies from practice.

## The software it drives

The procedure is written against **X-Ray Calc 3**, this laboratory's program for simulating and fitting
X-ray reflectivity, reached through its tool server. The program supplies the optical model, the cost
function and the optimizer. The procedure supplies what the program does not decide: the conditioning of
the curve and the acceptance of the fit.

X-Ray Calc 3 is at <https://github.com/OleksiyPenkov/X-RayCalc3>.

If you use the program, cite it:

- O. V. Penkov, M. Li, S. Mikki et al., "X-Ray Calc 3: improved software for simulation and inverse
  problem solving for X-ray reflectivity", J. Appl. Cryst. 57(2), 555-566 (2024).
  doi:10.1107/S1600576724001031
- O. V. Penkov, I. A. Kopylets, M. Khadem et al., "X-Ray Calc: A software for the simulation of X-ray
  reflectivity", SoftwareX 12, 100528 (2020). doi:10.1016/j.softx.2020.100528
- M. Li, S. Mikki, P. C. Uzoma et al., "An Efficient Method for the Experimental Characterization of
  Periodic Multilayer Mirrors: A Global Optimization Approach", IEEE Trans. Nucl. Sci. 70(4), 650-658
  (2023). doi:10.1109/TNS.2023.3255892

The physics of the procedure is not specific to this program. The step names, the parameter names and the
report template are, so expect to translate them for another fitting engine.

## What was tested, and what was found

Six fresh agent sessions and one autonomous agent fitted two Co/C multilayer curves under this
procedure, blind, against fits the expert had made and withheld. Every fitted thickness agreed with
the expert's within 0.7 Å, and five of the six sessions within 0.3 Å. The procedure was then applied to six
published Ru/C curves in twelve sessions, and every period layer agreed within 1 Å.

The final procedure, version 5.0.2 in this record, was then run unchanged on two measured W/B4C
multilayers, two fresh sessions each. It recovered the mean period within 0.3 Å of the expert's fits and
the period drift through the stack on both, and the W and B4C thicknesses within 1 Å on one of them. No
session met the tolerance on the intensities of the Bragg orders.

The negative result matters more for anyone reusing this. **The conditioning steps transferred between
the two material systems. The rules of verdict did not.**

## Known limits, in the order they will bite you

1. **The acceptance threshold does not transfer.** The chi-squared limit (1.3 in the example preset,
   without angle weighting and with the scale solved inside the fit) was calibrated on Co/C curves of four
   orders to 4.2 degrees. In unweighted chi-squared the Ru/C curves, of ten orders to 6 degrees, sit about
   2.3-fold above the Co/C ones, so no single threshold carries across the two. Recalibrate it for your
   curves.
2. **The roughness assignment within a period is decided by the optimizer seed, not by the data.** Two
   fits started from opposite structures return the same answer, and the two roughnesses of a
   two-material period can swap without changing the peaks. Do not use the assignment as a pass
   criterion.
3. **The material bounds are this laboratory's.** The example preset names density bounds for the
   materials it has fitted and a default rule (0.7 to 1.0 of bulk) for the rest. For a new material pair,
   check them.
4. **The constants are this laboratory's.** They are in `presets/csmic-empyrean.json`, not in the text.
   The rules are general; the numbers are not. Write your own preset.
5. **It is written in angstroms and it names X-Ray Calc 3's own tools and parameters.** The physics is
   portable; the vocabulary is not. Expect to translate.

## Versions

Five texts were used. They are in `versions/`, each the procedure exactly as a session received it.

| Version | Used by | Characters | sha256 (first 12) |
|---|---|---|---|
| `v1-stage1-round-1.md` | Co/C qualification, round 1 | 11731 | `18200bf17917` |
| `v2-stage1-round-2.md` | Co/C qualification, round 2 | 11930 | `e53695c64601` |
| `v3-stage1-round-3.md` | Co/C qualification, round 3 | 13119 | `5b864e9fe74e` |
| `v4-transfer-final.md` | all twelve Ru/C transfer sessions | 15832 | `8c515f3d5a25` |
| `v5.0.2-final.md` | the four W/B4C sessions of campaign 3 | 38315 | `3910aef0837c` |

`xrr-fitting-skill.md` is byte-identical to `v5.0.2-final.md` and is the version to use. The campaign-3
sessions ran it with `presets/csmic-empyrean.json` (sha256 `baa7117339ec`) and `substrates.json`
(`0c6701cf72a1`), the files in this record. These three files are stored with the Windows line endings
(CRLF) the sessions read, and the hashes above are of those bytes; with LF line endings the same texts hash
to `3e769ac0d6c5`, `6c2d8c603d23` and `1a2dd97d5853`. The files of v1 to v4 are hashed with LF endings.

What changed between them: v2 stated the per-material density bounds explicitly and narrowed the band a
session applies to its own orders from a factor of two to 25 percent; v3 moved the judgment of a fit onto
the report the server returns; v4 added a carbon surface layer to the starting model and rewrote the
rule governing when a profile fit may replace a periodic fit, so that a passing periodic fit is final.
v5 moved every constant into a preset validated against a schema, added the substrate library, reads
curves imported from `.xrdml` files, identifies the Bragg orders with refraction, and solves the scale
inside the fit within a window of 0.7; its preset turns angle weighting off, uses a wavelength of
1.54187 Å and five seeds, and holds the interlayer thicknesses constant. v5.0.2 fixed the chi-squared
limit of 1.3 under the solved scale.

## Provenance

The procedure was recorded during the expert's own fitting session, condensed, and given to the agent as
a single written intervention. It was not written by an agent and then approved; it was elicited from a
person who had never written it down.

The sessions that ran it, the fits they produced, the curves, and the expert's reference fits are in the
paper's data deposit, which is published with the paper.

## How to cite

Cite the paper for the method and this record for the artifact.

> O. V. Penkov, J. Peng, H. Fu, "An XRR fitting procedure for a laboratory LLM agent", version 2.0,
> Zenodo (2026). doi:10.5281/zenodo.22851594

The concept DOI `10.5281/zenodo.22851594` resolves to the newest version. Each version also has a DOI of
its own, which is the one to cite when it matters which text was used; version 1.0, the procedure of the
Co/C and Ru/C sessions, is doi:10.5281/zenodo.22851595.

## License

Creative Commons Attribution 4.0 International (CC BY 4.0). Full text in `LICENSE`.

You may use, adapt and redistribute this procedure, including commercially, provided you give credit.
Adapting it is the expected use: the limits above say which parts are this laboratory's and will need
replacing.
