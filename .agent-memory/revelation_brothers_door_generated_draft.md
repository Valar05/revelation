# Brother's Door Generated Draft

## Status

This is a stack-generated draft patch for review. It has not been applied to the active room deck.

Generated patch:

- `generated/brothers_door_scenario_patch.json`

Selected source packet:

- `generated/corpus/brothers_door_selected_fragments.json`

Validation:

- `python3 tools/scenario_agent.py validate generated/brothers_door_scenario_patch.json --allow-new-actions --strict-tradeoffs`
- Result: `ok`

## Stack Path

The draft was produced through `tools/scenario_agent.py generate` using a compact source packet and the Revelation generation system.

I added `--context-lite` to the generator because the full repository context was making API requests too large and the API connection repeatedly closed before returning output.

The successful model output was then structurally normalized to satisfy the existing patch validator. The normalization kept the generated scenario shape and source anchors, but repaired validation issues in event keys, resolution choices, button length, and report-line wording.

## Corpus Anchors

- `world_english_bible:00005`: Cain and Abel; keeper responsibility; sin at the door; blood crying from the ground.
- `enoch_laurence_gutenberg_77815:00028`: separated dead; accusing voice; divided places.
- `army_ranger_handbook_sh_21_76:00156`: stairwells as fatal funnels; clearing flow; casualty evacuation; site exploitation.
- `cdc_niosh_judgment_decision_stress_emergency_managers:00007`: decision-making under smoke, stress, incomplete information, and execution pressure.
- `lovecraft_colour_out_of_space_pg68236:00002`: local warning, bad site history, physical residue, official explanation failing under observation.

## Draft Premise

`brothers_door_stairwell` is an action investigation at a smoke-stained municipal stairwell.

The official evacuation record says the disabled-care floor was cleared. Wristband records and field instruments disagree. The threshold behaves like a witness: it resists movement when named civilians are missing from the living roster.

Root sin:

Official abandonment of vulnerable civilians under a false "all clear" report.

Local closure requires the squad to answer that sin, not merely contain the stairwell.

## Play Shape

Opening choices are character-owned plans:

- Brooks pushes through and clears the landing under fatal-funnel conditions.
- Park/Owen locks down the threshold and audits the record.
- Iyad withdraws to a secure zone and reviews casualty procedure.

The resolution beat adds ways to answer the sin:

- Correct the record.
- Retrieve the missing.
- Torah bears witness at the threshold.

The cooldown interlude moves into clinic and evidence handling:

- Saye cleans soot from triage tags.
- Brooks refuses any report marked "all clear."
- The powered-down recorder still catches one missing name under static.

## Review Notes

This is closer to the action-heavy format we discussed: the investigation happens while movement, rescue, smoke, stress, and stairwell procedure are under pressure.

The strongest next critique point is whether the draft should become active content as-is, or whether we should run one more generation pass focused only on improving specificity, character names, and result text before applying it.
