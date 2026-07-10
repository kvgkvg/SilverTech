# Guidance (LLM) golden-set evaluation

Generated: 2026-07-10T07:47:22.376903+00:00
Provider: **mock** (`SILVERTECH_LLM_PROVIDER`)
Cases: 25 (21 guidance, 4 out-of-scope)

## Method

Golden set (`data/eval/llm/golden_set.json`) authored from the appliance
manuals: each Vietnamese query lists the REQUIRED button_ids a correct
answer must reference and ALLOWED helper buttons; out-of-scope queries
must be refused. Every query runs through the real service path
(`create_guidance`): prompt build -> provider -> parse ->
`validate_guidance_buttons` gate -> humanization. `correct` = scope
handled right AND all required buttons present AND no button outside
required+allowed.

## Aggregates

- validation gate pass rate: **100%**
- fully correct cases: **40%** (10/25)
- guidance cases — mean recall 29%, mean precision 38%
- out-of-scope refusal accuracy: 100% (4/4)
- TTS-safe (no raw button_id spoken): 100%
- mean latency: 91 ms

## Per-case results

| case | outcome | scope | predicted | recall | precision | correct | ms |
|---|---|---|---|---|---|---|---|
| mw_grill | accepted | Y | grill | 1.0 | 1.0 | Y | 420 |
| mw_defrost | accepted | Y | turbo_defrost | 1.0 | 1.0 | Y | 386 |
| mw_reheat | accepted | N | - | 0.0 | 0.0 | N | 2 |
| mw_timer | accepted | Y | time_clock | 1.0 | 1.0 | Y | 480 |
| mw_add_minute | accepted | N | - | 0.0 | 0.0 | N | 2 |
| mw_stop | accepted | N | - | 0.0 | 0.0 | N | 2 |
| mw_auto_menu | accepted | N | - | 0.0 | 0.0 | N | 2 |
| mw_power | accepted | N | - | 0.0 | 0.0 | N | 2 |
| mw_combination | accepted | Y | grill | 0.0 | 0.0 | N | 2 |
| mw_quick30 | accepted | N | - | 0.0 | 0.0 | N | 2 |
| mw_oos_weather | accepted | Y | - | 1.0 | 1.0 | Y | 2 |
| mw_oos_recipe | accepted | Y | - | 1.0 | 1.0 | Y | 2 |
| mw_oos_other_device | accepted | Y | - | 1.0 | 1.0 | Y | 2 |
| el_program | accepted | Y | 1 | 1.0 | 1.0 | Y | 457 |
| el_power_on | accepted | N | - | 0.0 | 0.0 | N | 3 |
| el_temperature | accepted | Y | 1 | 0.0 | 1.0 | N | 495 |
| el_spin | accepted | N | - | 0.0 | 0.0 | N | 3 |
| el_add_clothes | accepted | N | - | 0.0 | 0.0 | N | 3 |
| el_delay_end | accepted | Y | 1 | 0.0 | 1.0 | N | 3 |
| el_prewash | accepted | N | - | 0.0 | 0.0 | N | 3 |
| el_extra_rinse | accepted | N | - | 0.0 | 0.0 | N | 3 |
| el_oos_time | accepted | Y | - | 1.0 | 1.0 | Y | 3 |
| ts_quick_wash | accepted | Y | quick_wash | 1.0 | 1.0 | Y | 3 |
| ts_dry | accepted | N | - | 0.0 | 0.0 | N | 2 |
| dk_temp_up | accepted | Y | temp_up | 1.0 | 1.0 | Y | 2 |

## Production llm_logs aggregate

- total logged attempts: 203
- accepted: 199 (mean latency 6627 ms)
- rejected: 4 (mean latency 7825 ms)
- p95 latency: 28324 ms

## Caveats

- With the mock provider this measures the keyword-matcher baseline and
  the correctness gates, NOT real LLM quality. Re-run with
  `SILVERTECH_LLM_PROVIDER=openrouter` for provider evaluation.
- Button-set metrics don't judge instruction wording quality; pair with
  a small human rubric pass for the report.