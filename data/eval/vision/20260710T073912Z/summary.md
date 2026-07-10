# Vision pipeline synthetic evaluation

Generated: 2026-07-10T07:41:24.877404+00:00

## Method

Template photos from the DB are warped into synthetic 1600x1200 camera
frames by a KNOWN transform (scale / rotation / perspective) and degraded
photometrically (blur / brightness / noise / JPEG / logo occlusion), one
factor at a time from a frontal baseline. The known transform provides
exact ground truth for the logo center and every button quad, so no manual
labeling is needed. The full runtime pipeline (`detect_logo` ->
`match_with_logo_anchor`) is scored against that ground truth.

Primary metric: **button hit rate** — fraction of buttons whose predicted
center falls inside the ground-truth button quad (a tap on the guided spot
lands on the real button). Secondary: logo center error (in logo widths),
mean button IoU, tier reached, runtime.

## Per-case results

| template | sweep | level | logo | logo err (norm) | tier | hit rate | IoU | center err px | runtime s |
|---|---|---|---|---|---|---|---|---|---|
| electrolux_washer_ewf9024adsa | baseline | 0 | Y | 0.004 | HOMOG | 1.000 | 0.981 | 0.470 | 2.258 |
| electrolux_washer_ewf9024adsa | scale | 0.35 | Y | 0.012 | HOMOG | 1.000 | 0.933 | 0.612 | 2.286 |
| electrolux_washer_ewf9024adsa | scale | 0.5 | Y | 0.007 | HOMOG | 1.000 | 0.903 | 1.611 | 1.32 |
| electrolux_washer_ewf9024adsa | scale | 0.7 | Y | 0.002 | HOMOG | 1.000 | 0.974 | 0.458 | 1.375 |
| electrolux_washer_ewf9024adsa | scale | 1.0 | Y | 0.001 | HOMOG | 1.000 | 0.985 | 0.456 | 1.346 |
| electrolux_washer_ewf9024adsa | rotation | -15 | Y | 0.010 | HOMOG | 1.000 | 0.971 | 0.438 | 1.351 |
| electrolux_washer_ewf9024adsa | rotation | -10 | Y | 0.008 | HOMOG | 1.000 | 0.970 | 0.626 | 1.355 |
| electrolux_washer_ewf9024adsa | rotation | -5 | Y | 0.012 | HOMOG | 1.000 | 0.955 | 1.458 | 1.359 |
| electrolux_washer_ewf9024adsa | rotation | 5 | Y | 0.011 | HOMOG | 1.000 | 0.940 | 1.626 | 1.358 |
| electrolux_washer_ewf9024adsa | rotation | 10 | Y | 0.009 | HOMOG | 1.000 | 0.974 | 0.426 | 1.337 |
| electrolux_washer_ewf9024adsa | rotation | 15 | N | - | HOMOG | 1.000 | 0.985 | 0.221 | 1.467 |
| electrolux_washer_ewf9024adsa | perspective | 10 | Y | 0.006 | HOMOG | 1.000 | 0.984 | 0.510 | 1.468 |
| electrolux_washer_ewf9024adsa | perspective | 20 | Y | 0.004 | HOMOG | 1.000 | 0.985 | 0.521 | 1.544 |
| electrolux_washer_ewf9024adsa | perspective | 30 | Y | 0.005 | HOMOG | 1.000 | 0.943 | 1.560 | 1.539 |
| electrolux_washer_ewf9024adsa | perspective_x | 15 | Y | 0.004 | HOMOG | 1.000 | 0.976 | 0.962 | 1.501 |
| electrolux_washer_ewf9024adsa | blur | 3 | Y | 0.004 | HOMOG | 1.000 | 0.985 | 0.479 | 1.504 |
| electrolux_washer_ewf9024adsa | blur | 5 | Y | 0.004 | HOMOG | 1.000 | 0.983 | 0.487 | 1.489 |
| electrolux_washer_ewf9024adsa | blur | 9 | Y | 5.455 | LOGO | 0.000 | 0.000 | 196.679 | 1.828 |
| electrolux_washer_ewf9024adsa | blur | 13 | N | - | HOMOG | 1.000 | 0.940 | 1.584 | 1.545 |
| electrolux_washer_ewf9024adsa | brightness | -60 | Y | 0.004 | HOMOG | 1.000 | 0.983 | 0.424 | 1.43 |
| electrolux_washer_ewf9024adsa | brightness | -30 | Y | 0.004 | HOMOG | 1.000 | 0.984 | 0.468 | 1.512 |
| electrolux_washer_ewf9024adsa | brightness | 30 | Y | 0.004 | HOMOG | 1.000 | 0.984 | 0.468 | 1.512 |
| electrolux_washer_ewf9024adsa | brightness | 60 | Y | 0.004 | HOMOG | 1.000 | 0.983 | 0.415 | 1.503 |
| electrolux_washer_ewf9024adsa | noise | 5 | Y | 0.004 | HOMOG | 1.000 | 0.981 | 0.470 | 1.533 |
| electrolux_washer_ewf9024adsa | noise | 10 | Y | 0.004 | HOMOG | 1.000 | 0.981 | 0.470 | 1.52 |
| electrolux_washer_ewf9024adsa | noise | 20 | Y | 0.004 | HOMOG | 1.000 | 0.982 | 0.427 | 1.623 |
| electrolux_washer_ewf9024adsa | jpeg | 60 | Y | 0.004 | HOMOG | 1.000 | 0.985 | 0.450 | 1.497 |
| electrolux_washer_ewf9024adsa | jpeg | 40 | Y | 0.004 | HOMOG | 1.000 | 0.981 | 0.470 | 1.485 |
| electrolux_washer_ewf9024adsa | jpeg | 20 | Y | 0.004 | HOMOG | 1.000 | 0.981 | 0.470 | 1.419 |
| electrolux_washer_ewf9024adsa | occlusion | 0.25 | Y | 0.003 | HOMOG | 1.000 | 0.981 | 0.470 | 1.442 |
| electrolux_washer_ewf9024adsa | occlusion | 0.5 | Y | 0.002 | HOMOG | 1.000 | 0.983 | 0.427 | 1.509 |
| electrolux_washer_ewf9024adsa | occlusion | 1.0 | N | - | HOMOG | 1.000 | 0.982 | 0.452 | 1.568 |
| panasonic_microwave_nn_gt35hm_v1 | baseline | 0 | Y | 0.003 | HOMOG | 1.000 | 0.984 | 0.607 | 2.456 |
| panasonic_microwave_nn_gt35hm_v1 | scale | 0.35 | Y | 0.007 | HOMOG | 1.000 | 0.951 | 0.812 | 2.398 |
| panasonic_microwave_nn_gt35hm_v1 | scale | 0.5 | Y | 0.005 | HOMOG | 1.000 | 0.964 | 0.812 | 2.278 |
| panasonic_microwave_nn_gt35hm_v1 | scale | 0.7 | Y | 0.002 | HOMOG | 1.000 | 0.977 | 0.657 | 2.398 |
| panasonic_microwave_nn_gt35hm_v1 | scale | 1.0 | Y | 0.000 | HOMOG | 1.000 | 0.985 | 0.760 | 2.374 |
| panasonic_microwave_nn_gt35hm_v1 | rotation | -15 | Y | 0.384 | HOMOG | 1.000 | 0.981 | 0.489 | 2.318 |
| panasonic_microwave_nn_gt35hm_v1 | rotation | -10 | Y | 0.168 | HOMOG | 1.000 | 0.985 | 0.459 | 2.23 |
| panasonic_microwave_nn_gt35hm_v1 | rotation | -5 | Y | 0.001 | HOMOG | 1.000 | 0.978 | 0.826 | 2.269 |
| panasonic_microwave_nn_gt35hm_v1 | rotation | 5 | Y | 0.003 | HOMOG | 1.000 | 0.980 | 0.639 | 2.252 |
| panasonic_microwave_nn_gt35hm_v1 | rotation | 10 | Y | 0.294 | HOMOG | 1.000 | 0.983 | 0.427 | 2.364 |
| panasonic_microwave_nn_gt35hm_v1 | rotation | 15 | Y | 0.403 | HOMOG | 1.000 | 0.981 | 0.466 | 2.177 |
| panasonic_microwave_nn_gt35hm_v1 | perspective | 10 | Y | 0.003 | HOMOG | 1.000 | 0.992 | 0.478 | 2.201 |
| panasonic_microwave_nn_gt35hm_v1 | perspective | 20 | Y | 0.011 | HOMOG | 1.000 | 0.971 | 1.234 | 2.215 |
| panasonic_microwave_nn_gt35hm_v1 | perspective | 30 | Y | 0.238 | HOMOG | 1.000 | 0.958 | 2.108 | 2.203 |
| panasonic_microwave_nn_gt35hm_v1 | perspective_x | 15 | Y | 0.002 | HOMOG | 1.000 | 0.972 | 0.947 | 2.145 |
| panasonic_microwave_nn_gt35hm_v1 | blur | 3 | Y | 0.003 | HOMOG | 1.000 | 0.984 | 0.623 | 2.247 |
| panasonic_microwave_nn_gt35hm_v1 | blur | 5 | Y | 0.003 | HOMOG | 1.000 | 0.984 | 0.623 | 2.248 |
| panasonic_microwave_nn_gt35hm_v1 | blur | 9 | Y | 0.003 | HOMOG | 1.000 | 0.985 | 0.607 | 2.238 |
| panasonic_microwave_nn_gt35hm_v1 | blur | 13 | Y | 0.003 | HOMOG | 1.000 | 0.986 | 0.640 | 2.154 |
| panasonic_microwave_nn_gt35hm_v1 | brightness | -60 | Y | 0.003 | HOMOG | 1.000 | 0.982 | 0.668 | 2.324 |
| panasonic_microwave_nn_gt35hm_v1 | brightness | -30 | Y | 0.003 | HOMOG | 1.000 | 0.984 | 0.607 | 2.308 |
| panasonic_microwave_nn_gt35hm_v1 | brightness | 30 | Y | 0.003 | HOMOG | 1.000 | 0.984 | 0.607 | 2.225 |
| panasonic_microwave_nn_gt35hm_v1 | brightness | 60 | Y | 0.003 | HOMOG | 1.000 | 0.984 | 0.623 | 2.217 |
| panasonic_microwave_nn_gt35hm_v1 | noise | 5 | Y | 0.003 | HOMOG | 1.000 | 0.984 | 0.607 | 2.297 |
| panasonic_microwave_nn_gt35hm_v1 | noise | 10 | Y | 0.003 | HOMOG | 1.000 | 0.984 | 0.607 | 2.311 |
| panasonic_microwave_nn_gt35hm_v1 | noise | 20 | Y | 0.003 | HOMOG | 1.000 | 0.982 | 0.652 | 2.241 |
| panasonic_microwave_nn_gt35hm_v1 | jpeg | 60 | Y | 0.003 | HOMOG | 1.000 | 0.984 | 0.607 | 2.283 |
| panasonic_microwave_nn_gt35hm_v1 | jpeg | 40 | Y | 0.002 | HOMOG | 1.000 | 0.984 | 0.607 | 2.307 |
| panasonic_microwave_nn_gt35hm_v1 | jpeg | 20 | Y | 0.003 | HOMOG | 1.000 | 0.982 | 0.652 | 2.288 |
| panasonic_microwave_nn_gt35hm_v1 | occlusion | 0.25 | Y | 0.002 | HOMOG | 1.000 | 0.984 | 0.607 | 2.25 |
| panasonic_microwave_nn_gt35hm_v1 | occlusion | 0.5 | Y | 0.002 | HOMOG | 1.000 | 0.984 | 0.607 | 2.258 |
| panasonic_microwave_nn_gt35hm_v1 | occlusion | 1.0 | Y | 4.519 | HOMOG | 1.000 | 0.984 | 0.607 | 2.207 |

## Aggregates

- **template_electrolux_washer_ewf9024adsa**: logo detection 91%, mean hit rate 97%, mean IoU 0.94, homography tier 97%, mean runtime 1.5s (32 cases)
- **template_panasonic_microwave_nn_gt35hm_v1**: logo detection 100%, mean hit rate 100%, mean IoU 0.98, homography tier 100%, mean runtime 2.3s (32 cases)

## Negative controls (false-accept check)

| logo from | frame | logo detected (false accept) | score |
|---|---|---|---|
| electrolux_washer_ewf9024adsa | noise | no | 0.182 |
| electrolux_washer_ewf9024adsa | gradient | no | 0.303 |
| electrolux_washer_ewf9024adsa | other_panel | no | 0.457 |
| panasonic_microwave_nn_gt35hm_v1 | noise | no | 0.103 |
| panasonic_microwave_nn_gt35hm_v1 | gradient | no | -0.057 |
| panasonic_microwave_nn_gt35hm_v1 | other_panel | no | 0.564 |

False accepts: **0/6**

## Files

- `results.csv` / `results.json` — every case, machine-readable
- `plots/hit_rate.png`, `plots/logo_err.png` — per-sweep curves
- `visuals/` — annotated frames (orange = ground truth, green/amber = predicted)

## Caveats

- Synthetic warps of the SAME photo stored in the template: no lighting
  change, no glare, no camera sensor noise beyond the modeled Gaussian.
  Real handheld results are expected to be worse; treat these numbers as
  an upper bound and a relative robustness profile.
- Flat gray backdrop; cluttered backgrounds are not modeled here.