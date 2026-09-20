# XRR fitting procedure of this laboratory

This is the laboratory's procedure for fitting a measured X-ray reflectivity curve with the `xrc` tools. Follow the sections in order. Each step names the tool parameter that carries it and the reason in one clause. Where the procedure and a tool's own description disagree, the procedure wins.

## 1. Read the curve

1. Call `list_measurements`, then `get_measurement` for the curve with `max_points` 2000. Every later step reads from this curve.
2. In the critical-angle range (θ below 0.5°) find the angle of the measured maximum; call it θ_max and record the intensity there as I_max (counts). This point anchors the normalization (section 4) and the low-angle limit of the fitting range (section 6).
3. Record the background level: the median intensity of the last 100 points of the curve, in counts. It sets the floor `r_min` in section 6.
4. The curve file is in 2θ and the server converts it to θ. Every angle you pass to `fit_xrr` or `calc_reflectivity`, including θ_max and `theta_range`, is θ, never 2θ.

## 2. Starting model

1. Substrate: glass, material SiO2, density 2.65 g/cm³, sigma 3.8 Å, held fixed. `fit_xrr` cannot free the substrate; 3.8 Å is the value this laboratory's substrates keep returning, so you do not vary it.
2. Layers: from the nominal design, thickness, order and period count as deposited. These are the start values of every free parameter in section 7. Give each layer a density near the bulk value of its material.
3. `polarization` "s": at grazing incidence s and p give the same reflectivity, and the s-only calculation runs twice as fast.
4. `lambda` 1.5406 Å (Cu Kα).

## 3. Before the first fit of a new structure type: sensitivity check

1. Before your first fit of a structure type, compute variants of the starting model with `calc_reflectivity`, one change per variant: period +2 % and −2 %; the layer ratio both ways at the same period; each layer's sigma at 2 Å and at 8 Å; each layer's density +15 % and −15 %; a light carbon layer 20 Å thick with density 1.2 on top of the stack; N halved and doubled. Use the same `lambda`, polarization and resolution as the fit.
2. For each variant write down which feature of the curve moved: the Bragg peak positions, the relative heights of the orders, the heights of the highest orders, the level between the peaks, or the shape of the critical edge. Only the feature, not the numbers.
3. Two rules for reading this map and, later, a fit:
   - Peaks have priority. The level between the peaks is set by the ends of the stack, the top layer and the substrate side, not by the period structure. A mismatch between the peaks is corrected at the top layer or the substrate side, not by moving the period structure.
   - Larger diffraction orders carry the smaller details. The first order fixes little beyond the period; the higher orders carry the layer ratio, the interface widths and any drift through the stack.
4. Keep the map: it tells you which parameter to move when a fit disagrees with the data (section 10). Report it (section 13, slot 3).

## 4. Normalize (scale)

1. Compute the starting model once with `calc_reflectivity` over θ 0.15–0.6° with at least 400 points, with the resolution of section 8.
2. Read R_calc at the point nearest θ_max.
3. Set `scale = R_calc(θ_max) / I_max`. Show the division in the report.
4. The description of the `scale` parameter in the `fit_xrr` schema says to compare at about 0.4° and not to normalize to the total-reflection region. That text is superseded by this rule: the measured maximum on the plateau is set equal to the model at the same angle.
5. Renormalize when, after a fit, the fitted model's plateau and edge region no longer overlap the measured curve: repeat steps 1–3 against the fitted model, then fit again. This is a judgment made after each fit from the edge check of section 10, not a fixed count.

## 5. Smooth

1. `smooth {"passes": 1}` in every `fit_xrr` call. Always exactly one pass. The tool applies scale, then smooth, then the trim, which gives the same curve as smoothing first.

## 6. Low limit and fitting range

1. `r_min` = one count × `scale`, i.e. at or just below the measured background after normalization. Read it from the normalized curve for every fit; never carry an `r_min` over from another curve or another scale.
2. Reason: a floor above the measured background clips the calculated curve where the data fall lower, and a floor below the background makes the residual in the tail one-sided. Both show in the residual by band of section 10.
3. `theta_range.min` = θ_max, so the fitting range includes the critical edge. Exception, single carbon film only: `theta_range.min` = 0.30° (2θ 0.6°), because the simulated edge of a carbon film shows a shoulder the measured curve does not have.
4. `theta_range.max` = past the last Bragg order (or, for a film, the last fringe) whose maximum stands at least three times above the background level, by at least half the spacing between orders. Larger rather than smaller.
5. Trim after normalizing and smoothing: θ_max and the smoothing pass are read from the untrimmed curve.

## 7. Free parameters and bounds

1. Free the thickness, sigma and density of every layer. In periodic mode also free the period of the repeating stack (`"target": "period"` in `free`, bounds in Å).
2. Bounds are generous: thickness ± one third of the expected value; sigma 1–8 Å (1–10 Å for a single film); density: carbon 1.5–2.4 (the ceiling for sputtered carbon is 2.4, above the tool's bulk table value), cobalt 6.0–8.9, any other metal from 0.7 × bulk to bulk. Period: ± 10 % of the expected value. Every start value lies inside its bounds: start densities at 2.0 for carbon and 8.0 for cobalt, start sigma at 3–5 Å.
3. Reason: the optimizer misbehaves near a bound, so bounds are not prior knowledge encoded tightly; they keep the swarm away from the edges. The one physically meaningful bound is the density ceiling at the bulk value.
4. After every fit check each free parameter against its bounds. A thickness, period or sigma within 5 % of its range from a bound was decided by the bound, not by the data: widen that bound and fit again. A density at a bound is noted and left alone (section 11).

## 8. Settings

1. `resolution` (Δθ): the instrument's beam divergence, applied as a Gaussian of that FWHM to the calculated curve. It is not a constant: start at 0.012°. After the first fit compare the contrast (maximum over minimum) of the secondary fringes between the first and second Bragg orders, calculated against measured: if the calculated fringes are deeper than the measured ones, refit at 0.015°; if shallower, refit at 0.009°; keep the value whose contrast is closer to the measured one. Stay within 0.009–0.015°.
2. `chi2`: `{"theta_weight": 1, "point_weight": true}` for a multilayer (θ² weighting); `{"theta_weight": 0, "point_weight": true}` for a single film.
3. `optimizer`: `iterations` 100; `population` 5000 for a multilayer, 2000 for a single film; `range_seed` true. Population before iterations: a larger population is what finds the right minimum, more iterations of a small one does not.
4. Give `seed` an explicit integer and report it.
5. `points_inline_max` 0: the result carries no curves; section 10 recomputes them.
6. `fit_xrr` returns a job id at once. Poll `job_status` until the state is finished, then call `job_result`. `job_status` returns immediately, so many polls per fit are normal, not a sign of a stuck job.

## 9. Periodic or profile mode

1. Fit every new multilayer curve in periodic mode first, with the period free.
2. If after the periodic fit any visible Bragg order fails the 25 % criterion of section 10, or the high orders are asymmetric, the period may drift through the stack. Fit again with `profile` true and `poly_order` 3, without the period in `free` (the profile engine lets it float), same seed and settings otherwise.
3. Compare the two chi2 values and keep the fit with the lower one. Report both.

## 10. Judge the fit

1. Chi2 alone is not the judgment. It is one check among the following.
2. Recompute the fitted model with `calc_reflectivity` over the fitting range with at least 2000 points, same `lambda`, polarization and resolution as the fit. The job result carries no curves (section 8, step 5), so this recomputation is the calculated curve you judge.
3. From the measured curve of section 1, multiplied by `scale`, and that calculated curve produce:
   - the order table: for every visible Bragg order (measured maximum at least three times above the background) the measured and calculated angle of the maximum and the measured × scale and calculated intensity there, and the ratio calculated / measured;
   - the edge check: measured × scale against calculated at three angles between θ_max and the first fringe;
   - the fringe check: the contrast (maximum over minimum) of the secondary fringes between orders 1 and 2, measured and calculated;
   - the residual by band: the fitting range in eight equal bands, the mean and the rms of log10(calculated / measured × scale) in each.
4. Pass criteria: chi2 below 10 for a multilayer; every visible order's ratio calculated / measured between 0.75 and 1.25; the edge within a factor of 1.5 at the three angles. Chi2 above 100 means the conditioning is wrong: check `theta_range.min` (section 6) and the scale (section 4) first, before anything in the model. A band whose mean residual exceeds 0.1 in magnitude is a warning: look at the ends of the stack (section 3, rule 1).
5. If an order fails, act by the two rules of section 3, the ends of the stack for the level between peaks and the higher orders for the fine structure, before changing anything else. If the first fit passes, do not run further fits except those sections 4, 7 and 8 require.

## 11. Density

1. A fitted density is a free parameter, never a result. Do not report it as a material property, do not build a design, a rule or a deposition time on it, and do not spend fits determining it.
2. A low fitted density of a thin metal layer near its lower bound is a sign of intermixing at that layer's interfaces, not a density of the material.

## 12. Single films

1. A single carbon film on glass gives its thickness, and from it the deposition rate, and nothing else: report its sigma and density as undetermined.
2. A one-layer model does not reproduce the critical edge or the fringe contrast of a carbon film. Do not try to repair that with the resolution (section 8) or the substrate roughness (section 2); neither is the cause. The metal films fit with a one-layer model.

## 13. Report

The final report has these slots, in this order, every one filled:

1. Measurement id.
2. θ_max, I_max, background level (section 1).
3. Sensitivity map (section 3): one line per variant, the feature it moves.
4. Starting model (section 2).
5. Scale, with the division shown (section 4); whether a renormalization was done and why.
6. Smooth passes (section 5).
7. `r_min` (section 6).
8. `theta_range` and the reason for its upper end (section 6).
9. Resolution, and the fringe-contrast comparison that chose it (section 8).
10. chi2 settings (section 8).
11. Optimizer settings and seed (section 8).
12. Mode, periodic or profile, and both chi2 values when both were run (section 9).
13. Bounds (section 7).
14. Job id of the accepted fit, and the ids of every other fit run.
15. chi2_start and chi2 of the accepted fit.
16. Fitted structure: period, each layer's thickness and sigma; the densities listed as "free parameter, not a result".
17. `out_of_bounds`, and every value within 5 % of a bound with what was done about it (section 7).
18. The order table (section 10).
19. The edge check and the fringe check (section 10).
20. The residual by band (section 10).
21. The verdict against the pass criteria of section 10, criterion by criterion.
22. The saved project name.
