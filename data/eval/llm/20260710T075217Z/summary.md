# Guidance (LLM) golden-set evaluation

Generated: 2026-07-10T07:52:17.260593+00:00
Provider: **mock** (`SILVERTECH_LLM_PROVIDER`)
Cases: 97 (85 guidance, 12 out-of-scope)

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
- fully correct cases: **26%** (25/97)
- guidance cases — mean recall 16%, mean precision 21%
- out-of-scope refusal accuracy: 100% (12/12)
- TTS-safe (no raw button_id spoken): 100%
- mean latency: 3 ms

## Per-case results

| case | outcome | scope | predicted | recall | precision | correct | ms |
|---|---|---|---|---|---|---|---|
| mw_grill_1 | accepted | Y | grill | 1.0 | 1.0 | Y | 10 |
| mw_grill_2 | accepted | Y | grill | 1.0 | 1.0 | Y | 2 |
| mw_grill_3 | accepted | Y | grill | 1.0 | 1.0 | Y | 3 |
| mw_grill_4 | accepted | Y | grill | 1.0 | 1.0 | Y | 3 |
| mw_defrost_1 | accepted | Y | turbo_defrost | 1.0 | 1.0 | Y | 3 |
| mw_defrost_2 | accepted | Y | turbo_defrost | 1.0 | 1.0 | Y | 2 |
| mw_defrost_3 | accepted | N | - | 0.0 | 0.0 | N | 3 |
| mw_defrost_4 | accepted | Y | turbo_defrost | 1.0 | 1.0 | Y | 2 |
| mw_reheat_1 | accepted | N | - | 0.0 | 0.0 | N | 3 |
| mw_reheat_2 | accepted | N | - | 0.0 | 0.0 | N | 5 |
| mw_reheat_3 | accepted | N | - | 0.0 | 0.0 | N | 2 |
| mw_reheat_4 | accepted | N | - | 0.0 | 0.0 | N | 3 |
| mw_auto_menu_1 | accepted | N | - | 0.0 | 0.0 | N | 2 |
| mw_auto_menu_2 | accepted | N | - | 0.0 | 0.0 | N | 2 |
| mw_auto_menu_3 | accepted | N | - | 0.0 | 0.0 | N | 3 |
| mw_combination_1 | accepted | Y | grill | 0.0 | 0.0 | N | 2 |
| mw_combination_2 | accepted | N | - | 0.0 | 0.0 | N | 2 |
| mw_combination_3 | accepted | N | - | 0.0 | 0.0 | N | 3 |
| mw_power_1 | accepted | N | - | 0.0 | 0.0 | N | 2 |
| mw_power_2 | accepted | N | - | 0.0 | 0.0 | N | 2 |
| mw_power_3 | accepted | N | - | 0.0 | 0.0 | N | 2 |
| mw_quick30_1 | accepted | N | - | 0.0 | 0.0 | N | 2 |
| mw_quick30_2 | accepted | N | - | 0.0 | 0.0 | N | 2 |
| mw_quick30_3 | accepted | N | - | 0.0 | 0.0 | N | 2 |
| mw_timer_1 | accepted | Y | time_clock | 1.0 | 1.0 | Y | 2 |
| mw_timer_2 | accepted | N | - | 0.0 | 0.0 | N | 2 |
| mw_timer_3 | accepted | N | - | 0.0 | 0.0 | N | 2 |
| mw_time1min_1 | accepted | N | - | 0.0 | 0.0 | N | 2 |
| mw_time1min_2 | accepted | N | - | 0.0 | 0.0 | N | 4 |
| mw_time10min_1 | accepted | N | - | 0.0 | 0.0 | N | 2 |
| mw_time10min_2 | accepted | N | - | 0.0 | 0.0 | N | 2 |
| mw_time10sec_1 | accepted | N | - | 0.0 | 0.0 | N | 2 |
| mw_addtime_1 | accepted | N | - | 0.0 | 0.0 | N | 2 |
| mw_addtime_2 | accepted | N | - | 0.0 | 0.0 | N | 2 |
| mw_stop_1 | accepted | N | - | 0.0 | 0.0 | N | 2 |
| mw_stop_2 | accepted | N | - | 0.0 | 0.0 | N | 2 |
| mw_stop_3 | accepted | N | - | 0.0 | 0.0 | N | 2 |
| mw_stop_4 | accepted | N | - | 0.0 | 0.0 | N | 2 |
| mw_start_1 | accepted | N | - | 0.0 | 0.0 | N | 3 |
| mw_start_2 | accepted | N | - | 0.0 | 0.0 | N | 2 |
| mw_start_3 | accepted | N | - | 0.0 | 0.0 | N | 2 |
| mw_up_1 | accepted | N | - | 0.0 | 0.0 | N | 3 |
| mw_down_1 | accepted | N | - | 0.0 | 0.0 | N | 2 |
| mw_multi_grill_time | accepted | Y | grill | 0.5 | 1.0 | N | 3 |
| mw_multi_defrost_grill | accepted | Y | grill | 0.5 | 1.0 | N | 3 |
| mw_oos_weather | accepted | Y | - | 1.0 | 1.0 | Y | 2 |
| mw_oos_recipe | accepted | Y | - | 1.0 | 1.0 | Y | 8 |
| mw_oos_other_device | accepted | Y | - | 1.0 | 1.0 | Y | 3 |
| mw_oos_smalltalk | accepted | Y | - | 1.0 | 1.0 | Y | 3 |
| mw_oos_lottery | accepted | Y | - | 1.0 | 1.0 | Y | 3 |
| mw_oos_tv | accepted | Y | - | 1.0 | 1.0 | Y | 3 |
| el_program_1 | accepted | Y | 1 | 1.0 | 1.0 | Y | 3 |
| el_program_2 | accepted | N | - | 0.0 | 0.0 | N | 2 |
| el_program_3 | accepted | N | - | 0.0 | 0.0 | N | 3 |
| el_program_4 | accepted | N | - | 0.0 | 0.0 | N | 2 |
| el_temp_1 | accepted | Y | 1 | 0.0 | 1.0 | N | 3 |
| el_temp_2 | accepted | N | - | 0.0 | 0.0 | N | 2 |
| el_temp_3 | accepted | N | - | 0.0 | 0.0 | N | 2 |
| el_power_1 | accepted | N | - | 0.0 | 0.0 | N | 2 |
| el_power_2 | accepted | N | - | 0.0 | 0.0 | N | 2 |
| el_power_3 | accepted | N | - | 0.0 | 0.0 | N | 2 |
| el_spin_1 | accepted | N | - | 0.0 | 0.0 | N | 2 |
| el_spin_2 | accepted | N | - | 0.0 | 0.0 | N | 3 |
| el_spin_3 | accepted | N | - | 0.0 | 0.0 | N | 3 |
| el_vapour_1 | accepted | N | - | 0.0 | 0.0 | N | 3 |
| el_vapour_2 | accepted | N | - | 0.0 | 0.0 | N | 3 |
| el_prewash_1 | accepted | N | - | 0.0 | 0.0 | N | 2 |
| el_prewash_2 | accepted | N | - | 0.0 | 0.0 | N | 2 |
| el_prewash_3 | accepted | N | - | 0.0 | 0.0 | N | 3 |
| el_rinse_1 | accepted | N | - | 0.0 | 0.0 | N | 2 |
| el_rinse_2 | accepted | N | - | 0.0 | 0.0 | N | 3 |
| el_rinse_3 | accepted | N | - | 0.0 | 0.0 | N | 2 |
| el_start_1 | accepted | N | - | 0.0 | 0.0 | N | 3 |
| el_start_2 | accepted | N | - | 0.0 | 0.0 | N | 2 |
| el_start_3 | accepted | N | - | 0.0 | 0.0 | N | 2 |
| el_start_4 | accepted | N | - | 0.0 | 0.0 | N | 2 |
| el_timemgr_1 | accepted | N | - | 0.0 | 0.0 | N | 2 |
| el_timemgr_2 | accepted | N | - | 0.0 | 0.0 | N | 2 |
| el_delay_1 | accepted | Y | 1 | 0.0 | 1.0 | N | 2 |
| el_delay_2 | accepted | N | - | 0.0 | 0.0 | N | 3 |
| el_delay_3 | accepted | Y | 1 | 0.0 | 1.0 | N | 2 |
| el_display_1 | accepted | N | - | 0.0 | 0.0 | N | 2 |
| el_oos_time | accepted | Y | - | 1.0 | 1.0 | Y | 2 |
| el_oos_fridge | accepted | Y | - | 1.0 | 1.0 | Y | 3 |
| el_oos_detergent | accepted | Y | - | 1.0 | 1.0 | Y | 2 |
| el_oos_joke | accepted | Y | - | 1.0 | 1.0 | Y | 2 |
| ts_quick_1 | accepted | Y | quick_wash | 1.0 | 1.0 | Y | 2 |
| ts_quick_2 | accepted | Y | quick_wash | 1.0 | 1.0 | Y | 2 |
| ts_dry_1 | accepted | N | - | 0.0 | 0.0 | N | 2 |
| ts_dry_2 | accepted | N | - | 0.0 | 0.0 | N | 2 |
| ts_start_1 | accepted | N | - | 0.0 | 0.0 | N | 2 |
| ts_start_2 | accepted | N | - | 0.0 | 0.0 | N | 2 |
| ts_oos_price | accepted | Y | - | 1.0 | 1.0 | Y | 3 |
| dk_temp_1 | accepted | Y | temp_up | 1.0 | 1.0 | Y | 3 |
| dk_temp_2 | accepted | N | - | 0.0 | 0.0 | N | 3 |
| dk_temp_3 | accepted | Y | temp_up | 1.0 | 1.0 | Y | 2 |
| dk_oos_fan | accepted | Y | - | 1.0 | 1.0 | Y | 2 |

## Production llm_logs aggregate

- total logged attempts: 300
- accepted: 296 (mean latency 4455 ms)
- rejected: 4 (mean latency 7825 ms)
- p95 latency: 25005 ms

## Caveats

- With the mock provider this measures the keyword-matcher baseline and
  the correctness gates, NOT real LLM quality. Re-run with
  `SILVERTECH_LLM_PROVIDER=openrouter` for provider evaluation.
- Button-set metrics don't judge instruction wording quality; pair with
  a small human rubric pass for the report.