#!/usr/bin/env python3
"""Install the first three-layer Revelation scenario packet.

The scenario process is:
- what: religious text
- how: procedure documents
- structure: public-domain weird fiction
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ROOMS_PATH = ROOT / "rooms_post_update.json"
EVENTS_PATH = ROOT / "events_post_update.json"
DECK_PATH = ROOT / "encounter_decks_post_update.json"

NEW_ROOM_ID = "bitter_water_pump_station"
OLD_MISSION_IDS = [
    "choir_beneath_floorboards",
    "county_records_annex",
    "hospital_discharge_ward",
    "backward_voices_drainage_tunnels",
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


RELIGIOUS_ANCHOR = {
    "source_id": "world_english_bible",
    "source_chunk_id": "world_english_bible:00192",
    "anchor_role": "religious_what",
    "source_fingerprint": [
        "written curse is blotted into bitter water",
        "water becomes a test that enters the body",
        "clean/unclean status is decided by a ritualized liquid record",
    ],
    "playable_transform": "A municipal pump station turns wet, identity-bearing paperwork into a bitter-water exposure routed through ordinary taps, cups, and sinks; sealed samples record the effect but are not consumed.",
    "required_visible_details": [
        "condensation, sink splash, or wet gloves reaching signed paperwork",
        "ink dissolving into a sink or custody bag",
        "bitter water in routine cups or taps",
        "operator status changing after a written statement enters the water system",
    ],
    "followup_payoff": "The cooldown interlude tests whether ordinary drinking water and written debrief language still carry the dissolved accusation.",
}

PROCEDURE_ANCHOR = {
    "source_id": "cdc_environmental_infection_control_2019",
    "source_chunk_id": "cdc_environmental_infection_control_2019:00003",
    "anchor_role": "procedural_how",
    "source_fingerprint": [
        "water systems can carry environmental risk",
        "equipment and engineering controls shape exposure",
        "facility systems become reservoirs when controls fail",
    ],
    "playable_transform": "The squad must isolate valves, protect the sample chain, or shut down the pump gallery while controlling condensation, sink splash, wet gloves, and washdown runoff.",
    "required_visible_details": [
        "valve isolation or pump lockout",
        "sealed sample jars or chain-of-custody bags sweating in humid air",
        "washdown/drain as a possible carrier",
    ],
    "followup_payoff": "The interlude follows sealed evidence, routine cups, and the washdown drain into base, where personnel state changes replace generic loot/resource fallout.",
}

STRUCTURE_ANCHOR = {
    "source_id": "lovecraft_colour_out_of_space_pg68236",
    "source_chunk_id": "lovecraft_colour_out_of_space_pg68236:00004",
    "anchor_role": "weird_fiction_structure",
    "source_fingerprint": [
        "local testimony begins with a fallen material near a well",
        "scientists test a sample that refuses ordinary categories",
        "contamination moves from object to water, land, and household",
    ],
    "playable_transform": "The mission starts as a municipal complaint, becomes a sampling problem, and ends with official fear that the water system has learned to test people.",
    "required_visible_details": [
        "worker testimony before full explanation",
        "instrument or lab result that cannot classify the sample",
        "delayed dread around future municipal water use",
    ],
    "followup_payoff": "The cooldown does not repeat the pump event; it shows the sample chain altering Saye, Park, Ross, and Torah's next readiness.",
}

STRESS_ANCHOR = {
    "source_id": "cdc_niosh_judgment_decision_stress_emergency_managers",
    "source_chunk_id": "cdc_niosh_judgment_decision_stress_emergency_managers:00008",
    "anchor_role": "hidden_state_resolution",
    "source_fingerprint": [
        "stress changes judgment quality",
        "available information constrains good decisions",
        "a useful result can still leave personnel impaired",
    ],
    "playable_transform": "Every plan can succeed, partially succeed, or backfire based on the proposing character's hidden condition.",
    "required_visible_details": [
        "one character shows decision residue after the mission",
        "success and harm can coexist in the outcome",
    ],
    "followup_payoff": "Cooldown choices update morale, stress, mental_state, contamination, or availability instead of only reporting atmosphere.",
}


def corpus_influences() -> list[dict[str, Any]]:
    return [
        {
            "seed_id": "world_english_bible",
            "source_title": "World English Bible",
            "source_chunk_id": "world_english_bible:00192",
            "source_moment": "A written curse is washed into bitter water and becomes an embodied test.",
            "writing_influence": "Use water, ink, dust, and judgment as a concrete symbolic mechanism.",
            "room_application": "The pump station anomaly makes signed incident statements dissolve when routine pump-station moisture reaches them through condensation, sink splash, or wet handling.",
            "followup_application": "The interlude tests whether debrief language and drinking water remain neutral after the mission.",
            "interlude_application": "Cooldown scenes show personnel avoiding cups, signatures, and spoken certainty.",
            "license_category": "public-domain",
            "source_fingerprint": RELIGIOUS_ANCHOR["source_fingerprint"],
            "structural_transfer": RELIGIOUS_ANCHOR["playable_transform"],
            "required_visible_details": RELIGIOUS_ANCHOR["required_visible_details"],
            "followup_payoff": RELIGIOUS_ANCHOR["followup_payoff"],
        },
        {
            "seed_id": "cdc_environmental_infection_control_2019",
            "source_title": "Guidelines for Environmental Infection Control in Health-Care Facilities",
            "source_chunk_id": "cdc_environmental_infection_control_2019:00003",
            "source_moment": "Facility water systems and equipment can serve as environmental reservoirs.",
            "writing_influence": "Make valves, drains, pumps, PPE, and sample custody drive the choices.",
            "room_application": "Player choices are medical triage, evidence-preserving sampling, or physical system isolation.",
            "followup_application": "Base fallout depends on whether water, paperwork, or personnel carried the residue home.",
            "interlude_application": "Cooldown uses washdown, break-room water, and evidence intake rather than free-floating dread.",
            "license_category": "us-federal-public-domain",
            "source_fingerprint": PROCEDURE_ANCHOR["source_fingerprint"],
            "structural_transfer": PROCEDURE_ANCHOR["playable_transform"],
            "required_visible_details": PROCEDURE_ANCHOR["required_visible_details"],
            "followup_payoff": PROCEDURE_ANCHOR["followup_payoff"],
        },
        {
            "seed_id": "lovecraft_colour_out_of_space_pg68236",
            "source_title": "The Colour Out of Space",
            "source_chunk_id": "lovecraft_colour_out_of_space_pg68236:00004",
            "source_moment": "A strange material near a well defeats laboratory categories and contaminates ordinary rural life.",
            "writing_influence": "Borrow slow evidence accumulation, scientific uncertainty, and dread of future water use.",
            "room_application": "The mission proceeds from worker testimony to sample failure to a municipal-system implication.",
            "followup_application": "The interlude carries delayed realization into base, not a second copy of the same event.",
            "interlude_application": "Cooldown shows normal infrastructure feeling compromised after the team returns.",
            "license_category": "public-domain",
            "source_fingerprint": STRUCTURE_ANCHOR["source_fingerprint"],
            "structural_transfer": STRUCTURE_ANCHOR["playable_transform"],
            "required_visible_details": STRUCTURE_ANCHOR["required_visible_details"],
            "followup_payoff": STRUCTURE_ANCHOR["followup_payoff"],
        },
    ]


def room_record() -> dict[str, Any]:
    anchors = [RELIGIOUS_ANCHOR, PROCEDURE_ANCHOR, STRUCTURE_ANCHOR, STRESS_ANCHOR]
    return {
        "id": NEW_ROOM_ID,
        "name": "Bitter Water Pump Station",
        "type": "mission",
        "active": True,
        "room_role": "recovery_operation",
        "encounter_family": "water_judgment_site",
        "object_class": "municipal pump station anomaly",
        "operation_type": "water_system_isolation_sampling_and_personnel_triage",
        "captaincy_role": "authorize_character_plan",
        "scene_path": "",
        "description": "A municipal pump station turns wet, identity-bearing paperwork into a bitter-water exposure routed through ordinary taps, cups, and sinks.",
        "first_visit_description": "The pump station is quiet except for the check valves. Condensation beads on the clipboard rail above the operator sink. Paper cups sit beside the tap; sealed evidence jars wait unopened in a plastic carrier.",
        "return_description": "The station remains locked out. The bypass line stays dry until someone signs a report in the control room.",
        "detection_report": "Two operators collapsed after signing routine pressure logs and drinking from the employee sink. Both pages were damp along the lower edge from the sink-side clipboard rail; during bagging, the ink ran black into the sample basin. Lab water is chemically ordinary. Bitterness appears only in routine potable water near the person named by wet paperwork.",
        "current_situation": "Torah and the squad must decide whether to stop new signatures, preserve the damp paperwork, or cut off the wet pump system before the municipal bypass reopens at dawn.",
        "scenario_generation_contract": {
            "what_from": "religious_text",
            "how_from": "procedure_docs",
            "structure_from": "lovecraft_public_domain_weird_fiction",
            "rule": "The anomaly's symbolic engine comes from religious text; the player actions come from procedure; the escalation shape comes from weird fiction evidence structure.",
        },
        "religious_subtext": {
            "motif": "bitter water, written accusation dissolved into liquid, dust from the floor, and embodied judgment",
            "primary_sources": [
                "world_english_bible:00191",
                "world_english_bible:00192",
            ],
            "subtext": "The pump station is not poisoning water in a normal sense. It turns written certainty into a test, then routes the test through civic infrastructure.",
            "visible_requirements": [
                "written line dissolving after condensation, sink splash, or wet handling reaches the page",
                "bitter taste tied to routine water near the named person",
                "floor dust or grit entering the sample",
                "clean/uncertain status changing after procedure",
            ],
        },
        "officer_reports": [
            {
                "officer_id": "dr_lenora_saye",
                "stance": "patients_first",
                "report": "The immediate hazard is more signatures. Move the named operators, switch intake to role numbers, and keep wet paperwork away from their water until symptoms stabilize."
            },
            {
                "officer_id": "specialist_mina_park",
                "stance": "evidence_chain_first",
                "report": "The transfer path is probably moisture to identity text to tap water. Photograph the damp edges, bag the paper dry-side out, and keep custody labels off the wet bench."
            },
            {
                "officer_id": "agent_caleb_ross",
                "stance": "physical_lockout",
                "report": "The room is making its own wet surfaces. Lock the bypass, kill the washdown line, and get the pump gallery dry before another form becomes a route."
            },
        ],
        "recurring_character_ids": [
            "dr_lenora_saye",
            "specialist_mina_park",
            "agent_caleb_ross",
            "torah",
            "brooks",
        ],
        "crew_state_hooks": [
            "water_judgment_first_contact",
            "statement_handling_warning",
        ],
        "ship_state_hooks": [
            "institute_water_system_lockout_protocol",
        ],
        "resource_stakes": {
            "site.bitter_water_pump_station.bypass_risk": "opens at dawn",
            "site.bitter_water_pump_station.symbolic_contamination": 1,
            "squad.stress": 1,
            "artifact.bitter_sample_jars.opportunity": 1,
        },
        "black_hole_anomaly": {
            "type": "symbolic_resonance",
            "evidence": "Signed statements bleed after condensation, sink splash, or wet gloves touch the paper; sealed jars stay unopened, and only routine potable water reacts near the named person."
        },
        "followup_vectors": [
            "medical triage leaves a clean patient and a damaged sample chain",
            "evidence-first handling preserves the religious mechanism and strains Park",
            "physical lockout protects the city but exposes Ross to the pump gallery",
            "cooldown interlude tests whether cups, signatures, and washdown drains remain safe",
        ],
        "progression_state": {
            "early": "The Institute learns that civic infrastructure can make symbolic judgment operational.",
            "mid": "Written reports and utility systems become possible contamination surfaces.",
            "late": "Base procedure must decide whether truth, confession, and evidence can be separated."
        },
        "environment_echoes": [
            "Signed debrief forms, wet clipboards, paper cups, sealed evidence jars, and washdown drains can carry later consequences."
        ],
        "ending_vectors": [
            {
                "id": "civic_judgment_network",
                "pulls_toward": [
                    "careless evidence writing",
                    "utility systems treated as inert",
                    "personnel forced to sign under stress",
                ],
                "diverts_to": [
                    "controlled language",
                    "water-system isolation",
                    "personnel recovery before testimony",
                ],
            }
        ],
        "procedure_hooks": [
            {
                "procedure": "water_system_lockout",
                "effect": "valve isolation can protect civilians while shifting risk to the exposed operator or security lead"
            },
            {
                "procedure": "sample_chain_of_custody",
                "effect": "preserving sequence improves understanding but may let the anomaly preserve accusation"
            },
            {
                "procedure": "post_exposure_cooldown",
                "effect": "after-action interludes update character mental state before the next mission"
            },
        ],
        "corpus_artifact_ids": [
            "world_english_bible",
            "cdc_environmental_infection_control_2019",
            "fema_nims_2017",
            "lovecraft_colour_out_of_space_pg68236",
            "cdc_niosh_judgment_decision_stress_emergency_managers",
        ],
        "corpus_influences": corpus_influences(),
        "corpus_anchor_points": anchors,
        "character_state_stakes": {
            "character.dr_lenora_saye.mental_state": "patient-first plan may steady her or leave her guilty over evidence loss",
            "character.specialist_mina_park.mental_state": "evidence-chain plan can preserve the mechanism while making her fixate on labels",
            "character.agent_caleb_ross.morale": "lockout plan can protect civilians while making him feel used as a valve",
            "character.torah.contamination": "Torah can sense bitterness from routine water before anyone drinks it",
            "character.brooks.command_confidence": "Brooks must decide whether cooldown is recovery or lost readiness",
        },
        "interlude_vectors": [
            "Break-room water tastes wrong only after condensation beads along a signed intake form.",
            "Sample jars sweat through sealed bags during cooldown, wetting the outer labels but remaining evidence only.",
            "Saye, Park, or Ross can become less available depending on the chosen plan.",
        ],
        "corpus_specificity_pass": {
            "pass_id": "three_layer_scenario_contract_v1",
            "visible_source_mechanisms": [
                "Numbers bitter-water ordeal appears as signed statements dissolving only after mundane water contact and then testing named operators.",
                "CDC/FEMA procedural material appears as lockout, sampling, decon, incident reporting, and status updates.",
                "Lovecraft structure appears as local testimony, lab uncertainty, contaminated water infrastructure, and delayed dread rather than mythos names.",
            ],
        },
    }


def entry_event() -> dict[str, Any]:
    anchors = [RELIGIOUS_ANCHOR, PROCEDURE_ANCHOR, STRUCTURE_ANCHOR, STRESS_ANCHOR]
    return {
        "id": "bitter_water_pump_station_entry",
        "type": "choice",
        "speaker": "SITREP",
        "line_1": "Municipal pump station, south service district. Two operators collapsed after signing pressure logs on a damp clipboard rail and drinking from the employee sink.",
        "line_2": "Lab samples test ordinary. When system water touches identity-bearing paper, nearby cups and taps turn bitter for the named person. The bypass line reopens at dawn unless the team changes the system state.",
        "reactivate_on_reshuffle": False,
        "environment_memory_flags": [
            "bitter_water_site_seen",
            "three_layer_generation_contract_active",
        ],
        "ship_state_changes": [
            "institute_water_system_lockout_protocol_logged",
        ],
        "infrastructure_actor": "municipal pump system",
        "buttons": [
            {
                "label": "Saye triages operators",
                "action": "quarantine",
                "voice_aliases": [
                    "triage operators",
                    "saye triage",
                    "patients first",
                ],
            },
            {
                "label": "Park preserves sample chain",
                "action": "observe",
                "voice_aliases": [
                    "sample chain",
                    "park evidence",
                    "preserve evidence",
                ],
            },
            {
                "label": "Ross locks out bypass",
                "action": "seal",
                "voice_aliases": [
                    "lockout bypass",
                    "ross lockout",
                    "seal pump",
                ],
            },
        ],
        "action_results": {
            "quarantine": {
                "lines": [
                    "Saye stops new signatures, moves the named operators to bottled water, and accepts that the sample timeline may suffer."
                ],
                "resource_changes": {},
                "environment_state_changes": [
                    "bitter_water_medical_plan_selected",
                    {"key": "character.dr_lenora_saye.stress", "delta": 1},
                ],
            },
            "observe": {
                "lines": [
                    "Park preserves the damp paperwork path and sample order, but her custody form may become the next identity-bearing surface."
                ],
                "resource_changes": {},
                "environment_state_changes": [
                    "bitter_water_evidence_plan_selected",
                    {"key": "character.specialist_mina_park.stress", "delta": 1},
                ],
            },
            "seal": {
                "lines": [
                    "Ross cuts the bypass, washdown, and gallery humidity first, protecting the city while putting himself in the wettest part of the site."
                ],
                "resource_changes": {},
                "environment_state_changes": [
                    "bitter_water_lockout_plan_selected",
                    {"key": "character.agent_caleb_ross.stress", "delta": 1},
                ],
            },
        },
        "story_followups": {
            "quarantine": {
                "event_id": "bitter_water_revelation_debrief",
                "trigger_key": "bitter_water_resolution_saye",
                "delay_rooms": 0,
                "immediate": True,
                "queued_line": "The operators leave under medical hold. One sealed evidence jar remains labeled but unclaimed, and the plant manager asks whether confessions count as medical evidence."
            },
            "observe": {
                "event_id": "bitter_water_revelation_debrief",
                "trigger_key": "bitter_water_resolution_park",
                "delay_rooms": 0,
                "immediate": True,
                "queued_line": "Park finds two pressure logs with the same timestamp. One accuses the operators. The older ink does not."
            },
            "seal": {
                "event_id": "bitter_water_revelation_debrief",
                "trigger_key": "bitter_water_resolution_ross",
                "delay_rooms": 0,
                "immediate": True,
                "queued_line": "Ross locks the bypass before dawn and finds the manual override tagged with a supervisor's initials, not an operator's."
            },
        },
        "corpus_artifact_ids": [
            "world_english_bible",
            "cdc_environmental_infection_control_2019",
            "lovecraft_colour_out_of_space_pg68236",
        ],
        "corpus_influences": corpus_influences(),
        "corpus_anchor_points": anchors,
        "story_thread": {
            "id": "bitter_water_statement_arc",
            "role": "first three-layer scenario and post-mission cooldown arc",
        },
        "state_reads": [
            "site.bitter_water_pump_station.bypass_risk",
            "character.dr_lenora_saye.mental_state",
            "character.specialist_mina_park.mental_state",
            "character.agent_caleb_ross.morale",
        ],
        "interlude_hooks": [
            "bitter_water_cooldown_interlude",
        ],
        "operation_plans": [
            {
                "action": "quarantine",
                "officer_id": "dr_lenora_saye",
                "primary_skill": "medicine",
                "base_success": 0.74,
                "yield": "medical hold, operator separation, bottled water, and a pause on new names entering the paperwork",
                "risk": "the sample sequence may break and leave the moisture-to-document pathway legally clean but symbolically unresolved",
                "minimum_availability": 30,
                "blocked_mental_states": [
                    "unfit",
                    "dissociated",
                    "ritualizing",
                ],
                "outcomes": {
                    "strong_success": {
                        "lines": [
                            "Saye moves the operators by bed number and refuses the plant manager's demand for signed statements.",
                            "The older operator accepts bottled water without reacting. The sample basin keeps a black ring where the ink went down.",
                        ],
                        "resource_changes": {
                            "squad.morale": 1,
                        },
                        "environment_state_changes": [
                            "operators_medically_separated",
                            "unsigned_operator_statements",
                            {"key": "character.dr_lenora_saye.morale", "delta": 4},
                            {"key": "character.dr_lenora_saye.mental_state", "value": "steady"},
                            {"key": "site.bitter_water_pump_station.symbolic_contamination", "delta": -1},
                        ],
                    },
                    "success": {
                        "lines": [
                            "Saye isolates the operators by bed number. Their signatures stay bagged, wet, and unread.",
                            "The team gains a symptom timeline. The pump system remains only partly understood.",
                        ],
                        "resource_changes": {},
                        "environment_state_changes": [
                            "operators_medically_separated",
                            "sample_chain_incomplete",
                            {"key": "character.dr_lenora_saye.stress", "delta": 2},
                            {"key": "character.specialist_mina_park.morale", "delta": -2},
                        ],
                    },
                    "partial": {
                        "lines": [
                            "Saye gets the operators out, but one orderly asks for a signature at intake.",
                            "The pen dries white. Torah says the cup beside the bed has gone assigned before anyone lifts it.",
                        ],
                        "resource_changes": {
                            "squad.morale": -1,
                        },
                        "environment_state_changes": [
                            "intake_signature_contaminated",
                            {"key": "character.dr_lenora_saye.stress", "delta": 4},
                            {"key": "character.torah.contamination", "delta": 1},
                        ],
                    },
                    "failure": {
                        "lines": [
                            "Saye separates the patients too late. The second operator signs a correction before medical catches his hand.",
                            "Every paper cup beside the sink now belongs to someone different.",
                        ],
                        "resource_changes": {
                            "squad.morale": -1,
                        },
                        "environment_state_changes": [
                            "operator_correction_spread",
                            {"key": "character.dr_lenora_saye.stress", "delta": 5},
                            {"key": "character.dr_lenora_saye.mental_state", "value": "strained"},
                            {"key": "institute.quarantine_load", "delta": 1},
                        ],
                    },
                    "catastrophe": {
                        "lines": [
                            "Saye calls the hold as the plant printer wakes and produces discharge slips for people not yet admitted.",
                            "The water stays clear. The paperwork becomes the carrier.",
                        ],
                        "resource_changes": {
                            "squad.morale": -2,
                            "squad.refusal_risk": 1,
                        },
                        "environment_state_changes": [
                            "medical_paperwork_carrier",
                            {"key": "character.dr_lenora_saye.stress", "delta": 7},
                            {"key": "character.dr_lenora_saye.mental_state", "value": "spooked"},
                            {"key": "site.bitter_water_pump_station.symbolic_contamination", "delta": 2},
                        ],
                    },
                },
                "corpus_anchor_points": anchors,
            },
            {
                "action": "observe",
                "officer_id": "specialist_mina_park",
                "primary_skill": "analysis",
                "base_success": 0.69,
                "yield": "complete label order, preserved damp-edge evidence, and a readable moisture-to-identity mechanism",
                "risk": "Park's custody record may become the next wet identity-bearing surface the water tests",
                "minimum_availability": 30,
                "blocked_mental_states": [
                    "unfit",
                    "dissociated",
                    "withdrawn",
                ],
                "outcomes": {
                    "strong_success": {
                        "lines": [
                            "Park photographs each label before touching the jars. She bags the logbook open to the page where the ink has thinned but not vanished.",
                            "The sequence holds: name, tap, grit, reaction. Nobody has to drink from evidence to prove it.",
                        ],
                        "resource_changes": {
                            "squad.morale": 1,
                        },
                        "environment_state_changes": [
                            "bitter_water_sequence_preserved",
                            "artifact.bitter_sample_jars.secured",
                            {"key": "character.specialist_mina_park.morale", "delta": 4},
                            {"key": "character.specialist_mina_park.mental_state", "value": "steady"},
                        ],
                    },
                    "success": {
                        "lines": [
                            "Park preserves the logbook order and seals three jars with witness tape.",
                            "The fourth jar fogs from inside the bag when she writes her initials on the custody line.",
                        ],
                        "resource_changes": {},
                        "environment_state_changes": [
                            "bitter_water_sequence_preserved",
                            "park_initials_on_custody_line",
                            {"key": "character.specialist_mina_park.stress", "delta": 3},
                            {"key": "character.specialist_mina_park.mental_state", "value": "fixated"},
                        ],
                    },
                    "partial": {
                        "lines": [
                            "Park saves the sample chain but loses the first witness statement when the plastic sleeve fills with clear water.",
                            "She can still prove the order. She cannot prove who started it.",
                        ],
                        "resource_changes": {},
                        "environment_state_changes": [
                            "first_statement_lost_to_water",
                            {"key": "character.specialist_mina_park.stress", "delta": 4},
                            {"key": "thread.bitter_water_statement_arc.pressure", "delta": 1},
                        ],
                    },
                    "failure": {
                        "lines": [
                            "Park keeps the jars in order, then notices the labels have sorted themselves by guilt language instead of time.",
                            "The evidence improves. Her confidence does not.",
                        ],
                        "resource_changes": {
                            "squad.morale": -1,
                        },
                        "environment_state_changes": [
                            "custody_order_sorted_by_accusation",
                            {"key": "character.specialist_mina_park.stress", "delta": 5},
                            {"key": "character.specialist_mina_park.mental_state", "value": "fixated"},
                        ],
                    },
                    "catastrophe": {
                        "lines": [
                            "Park signs the custody form to stop the argument. Her name feathers through all four jars before the ink reaches the paper.",
                            "The sample chain is perfect. It is also aimed at her.",
                        ],
                        "resource_changes": {
                            "squad.morale": -2,
                        },
                        "environment_state_changes": [
                            "park_named_by_sample_chain",
                            {"key": "character.specialist_mina_park.stress", "delta": 8},
                            {"key": "character.specialist_mina_park.contamination", "delta": 3},
                            {"key": "character.specialist_mina_park.mental_state", "value": "spooked"},
                        ],
                    },
                },
                "corpus_anchor_points": anchors,
            },
            {
                "action": "seal",
                "officer_id": "agent_caleb_ross",
                "primary_skill": "security",
                "base_success": 0.64,
                "yield": "physical lockout of the bypass, washdown line, and humid pump gallery before the municipal system receives another name",
                "risk": "the pump gallery may use Ross's direct action and wet gear as the statement it needs",
                "minimum_availability": 35,
                "blocked_mental_states": [
                    "unfit",
                    "dissociated",
                    "withdrawn",
                ],
                "outcomes": {
                    "strong_success": {
                        "lines": [
                            "Ross cuts power and pins the bypass valve with a mechanical lock. No one has to say the plant is safe.",
                            "The pressure drops in stages. The city stays out of the test.",
                        ],
                        "resource_changes": {
                            "squad.morale": 1,
                        },
                        "environment_state_changes": [
                            "municipal_bypass_locked_out",
                            {"key": "character.agent_caleb_ross.morale", "delta": 3},
                            {"key": "character.agent_caleb_ross.stress", "delta": 1},
                        ],
                    },
                    "success": {
                        "lines": [
                            "Ross reaches the gallery before dawn and locks the bypass by hand.",
                            "The valve wheel leaves a wet circle on his glove. Torah reports bitterness in his mouth from ten feet away and refuses the nearby cup.",
                        ],
                        "resource_changes": {},
                        "environment_state_changes": [
                            "municipal_bypass_locked_out",
                            "ross_glove_bitter_valve_mark",
                            {"key": "character.agent_caleb_ross.stress", "delta": 4},
                            {"key": "character.torah.contamination", "delta": 1},
                        ],
                    },
                    "partial": {
                        "lines": [
                            "Ross locks the bypass but the pressure gauge keeps climbing with the breaker open.",
                            "The city is protected. The pump station is not finished.",
                        ],
                        "resource_changes": {},
                        "environment_state_changes": [
                            "bypass_locked_pressure_continues",
                            {"key": "character.agent_caleb_ross.stress", "delta": 5},
                            {"key": "site.bitter_water_pump_station.symbolic_contamination", "delta": 1},
                        ],
                    },
                    "failure": {
                        "lines": [
                            "Ross closes the bypass after the first scheduled pulse. The downstream monitor prints one pressure reading with his call sign beside it.",
                            "He does not ask how the plant learned it.",
                        ],
                        "resource_changes": {
                            "squad.refusal_risk": 1,
                        },
                        "environment_state_changes": [
                            "downstream_monitor_prints_ross_callsign",
                            {"key": "character.agent_caleb_ross.stress", "delta": 6},
                            {"key": "character.agent_caleb_ross.mental_state", "value": "defiant"},
                            {"key": "character.agent_caleb_ross.contamination", "delta": 1},
                        ],
                    },
                    "catastrophe": {
                        "lines": [
                            "Ross forces the bypass shut and the gallery answers with every valve tag in his voice.",
                            "The city is spared. Ross comes back with his glove full of clear water and no memory of opening his hand.",
                        ],
                        "resource_changes": {
                            "squad.morale": -2,
                            "squad.refusal_risk": 1,
                        },
                        "environment_state_changes": [
                            "ross_voice_in_valve_tags",
                            {"key": "character.agent_caleb_ross.stress", "delta": 9},
                            {"key": "character.agent_caleb_ross.contamination", "delta": 3},
                            {"key": "character.agent_caleb_ross.mental_state", "value": "dissociated"},
                            {"key": "character.agent_caleb_ross.availability", "delta": -25},
                        ],
                    },
                },
                "corpus_anchor_points": anchors,
            },
        ],
    }


def cooldown_interlude() -> dict[str, Any]:
    anchors = [RELIGIOUS_ANCHOR, PROCEDURE_ANCHOR, STRUCTURE_ANCHOR, STRESS_ANCHOR]
    return {
        "id": "bitter_water_cooldown_interlude",
        "type": "interlude",
        "interlude_type": "cooldown",
        "speaker": "Break Room",
        "line_1": "The squad returns before dawn. Someone has set paper cups beside the coffee urn and nobody touches them.",
        "line_2": "Four sealed evidence jars sit in the intake window. The labels are dry. The table under them is not.",
        "visible_text": "The squad returns before dawn. Someone has set paper cups beside the coffee urn and nobody touches them. Four sealed evidence jars sit in the intake window. The labels are dry. The table under them is not.",
        "reactivate_on_reshuffle": False,
        "trigger_conditions": [
            "bitter_water_site_seen",
        ],
        "state_reads": [
            "operators_medically_separated",
            "bitter_water_sequence_preserved",
            "municipal_bypass_locked_out",
            "park_named_by_sample_chain",
            "ross_voice_in_valve_tags",
            "medical_paperwork_carrier",
        ],
        "state_writes": [
            "character.dr_lenora_saye.mental_state",
            "character.specialist_mina_park.mental_state",
            "character.agent_caleb_ross.mental_state",
            "character.torah.contamination",
            "squad.morale",
        ],
        "featured_characters": [
            "brooks",
            "torah",
            "dr_lenora_saye",
            "specialist_mina_park",
            "agent_caleb_ross",
        ],
        "buttons": [
            {
                "label": "Order cooldown before debrief",
                "action": "clinic",
                "voice_aliases": [
                    "cooldown",
                    "clinic first",
                    "stand down",
                ],
            },
            {
                "label": "Continue intake analysis",
                "action": "continue_analysis",
                "voice_aliases": [
                    "continue analysis",
                    "analyze samples",
                    "finish intake",
                ],
            },
            {
                "label": "Let Brooks handle the room",
                "action": "brooks_handles",
                "voice_aliases": [
                    "brooks handles",
                    "let brooks",
                    "brooks debrief",
                ],
            },
        ],
        "choices": [
            {
                "label": "Order cooldown before debrief",
                "action": "clinic",
                "voice_aliases": [
                    "cooldown",
                    "clinic first",
                    "stand down",
                ],
            },
            {
                "label": "Continue intake analysis",
                "action": "continue_analysis",
                "voice_aliases": [
                    "continue analysis",
                    "analyze samples",
                    "finish intake",
                ],
            },
            {
                "label": "Let Brooks handle the room",
                "action": "brooks_handles",
                "voice_aliases": [
                    "brooks handles",
                    "let brooks",
                    "brooks debrief",
                ],
            },
        ],
        "action_results": {
            "clinic": {
                "lines": [
                    "Brooks sends the squad through washdown and delays the signatures until after breakfast.",
                    "Saye dislikes the lost hour. Park stops staring at the labels. Ross drinks coffee from a metal mug and says nothing about the taste.",
                ],
                "resource_changes": {
                    "squad.morale": 1,
                },
                "environment_state_changes": [
                    "bitter_water_cooldown_completed",
                    {"key": "character.dr_lenora_saye.stress", "delta": -2},
                    {"key": "character.specialist_mina_park.stress", "delta": -2},
                    {"key": "character.agent_caleb_ross.stress", "delta": -1},
                    {"key": "character.brooks.command_confidence", "delta": 1},
                ],
            },
            "continue_analysis": {
                "lines": [
                    "The intake team works while the coffee goes cold. The fourth jar finally shows a precipitate like concrete dust.",
                    "The report is useful enough that no one says it was a mistake.",
                ],
                "resource_changes": {
                    "squad.morale": -1,
                },
                "environment_state_changes": [
                    "bitter_water_precipitate_identified",
                    {"key": "character.specialist_mina_park.stress", "delta": 3},
                    {"key": "character.dr_lenora_saye.stress", "delta": 2},
                    {"key": "character.torah.contamination", "delta": 1},
                    {"key": "thread.bitter_water_statement_arc.pressure", "delta": 1},
                ],
            },
            "brooks_handles": {
                "lines": [
                    "Brooks collects the cups, replaces them with canteens, and tells everyone to write role labels until morning.",
                    "It is not a cure. It is enough for the room to start breathing normally again.",
                ],
                "resource_changes": {
                    "squad.morale": 1,
                },
                "environment_state_changes": [
                    "brooks_role_label_cooldown",
                    {"key": "character.brooks.command_confidence", "delta": 2},
                    {"key": "character.agent_caleb_ross.morale", "delta": 1},
                    {"key": "character.specialist_mina_park.mental_state", "value": "recovering"},
                ],
            },
        },
        "outcomes": {
            "clinic": {
                "lines": [
                    "Brooks sends the squad through washdown and delays the signatures until after breakfast.",
                    "Saye dislikes the lost hour. Park stops staring at the labels. Ross drinks coffee from a metal mug and says nothing about the taste.",
                ],
                "resource_changes": {
                    "squad.morale": 1,
                },
                "environment_state_changes": [
                    "bitter_water_cooldown_completed",
                    {"key": "character.dr_lenora_saye.stress", "delta": -2},
                    {"key": "character.specialist_mina_park.stress", "delta": -2},
                    {"key": "character.agent_caleb_ross.stress", "delta": -1},
                    {"key": "character.brooks.command_confidence", "delta": 1},
                ],
            },
            "continue_analysis": {
                "lines": [
                    "The intake team works while the coffee goes cold. The fourth jar finally shows a precipitate like concrete dust.",
                    "The report is useful enough that no one says it was a mistake.",
                ],
                "resource_changes": {
                    "squad.morale": -1,
                },
                "environment_state_changes": [
                    "bitter_water_precipitate_identified",
                    {"key": "character.specialist_mina_park.stress", "delta": 3},
                    {"key": "character.dr_lenora_saye.stress", "delta": 2},
                    {"key": "character.torah.contamination", "delta": 1},
                    {"key": "thread.bitter_water_statement_arc.pressure", "delta": 1},
                ],
            },
            "brooks_handles": {
                "lines": [
                    "Brooks collects the cups, replaces them with canteens, and tells everyone to write role labels until morning.",
                    "It is not a cure. It is enough for the room to start breathing normally again.",
                ],
                "resource_changes": {
                    "squad.morale": 1,
                },
                "environment_state_changes": [
                    "brooks_role_label_cooldown",
                    {"key": "character.brooks.command_confidence", "delta": 2},
                    {"key": "character.agent_caleb_ross.morale", "delta": 1},
                    {"key": "character.specialist_mina_park.mental_state", "value": "recovering"},
                ],
            },
        },
        "followup_hooks": [
            "bitter_water_cooldown_completed",
            "bitter_water_precipitate_identified",
            "brooks_role_label_cooldown",
        ],
        "corpus_anchors": [
            "world_english_bible:00192",
            "cdc_environmental_infection_control_2019:00003",
            "lovecraft_colour_out_of_space_pg68236:00004",
            "cdc_niosh_judgment_decision_stress_emergency_managers:00008",
        ],
        "corpus_influences": corpus_influences(),
        "corpus_anchor_points": anchors,
        "story_thread": {
            "id": "bitter_water_statement_arc",
            "role": "post-mission cooldown and character-state fallout",
        },
        "tone_notes": "Cooldown should feel ordinary and procedural: cups, forms, washdown, tired staff, and quiet avoidance.",
    }


def revelation_debrief() -> dict[str, Any]:
    anchors = [RELIGIOUS_ANCHOR, PROCEDURE_ANCHOR, STRUCTURE_ANCHOR, STRESS_ANCHOR]
    return {
        "id": "bitter_water_revelation_debrief",
        "type": "resolution",
        "speaker": "Control Room",
        "line_1": "Park reconstructs the wet logs before the bypass timer expires. The sin is false witness: a supervisor forced the operators to sign blame for an illegal pressure release he ordered.",
        "line_2": "The water is not asking whether they are guilty. It is carrying the accusation until someone answers the lie in a form the station recognizes.",
        "visible_text": "Park reconstructs the wet logs before the bypass timer expires. The sin is false witness: a supervisor forced the operators to sign blame for an illegal pressure release he ordered. The water is not asking whether they are guilty. It is carrying the accusation until someone answers the lie in a form the station recognizes.",
        "reactivate_on_reshuffle": False,
        "trigger_conditions": [
            "bitter_water_site_seen",
        ],
        "state_reads": [
            "operators_medically_separated",
            "bitter_water_sequence_preserved",
            "municipal_bypass_locked_out",
            "bitter_water_medical_plan_selected",
            "bitter_water_evidence_plan_selected",
            "bitter_water_lockout_plan_selected",
        ],
        "state_writes": [
            "site.bitter_water_pump_station.resolved",
            "thread.bitter_water_statement_arc.sin",
            "thread.bitter_water_statement_arc.resolution",
            "character.torah.contamination",
            "character.specialist_mina_park.mental_state",
            "character.brooks.command_confidence",
        ],
        "featured_characters": [
            "brooks",
            "torah",
            "specialist_mina_park",
            "dr_lenora_saye",
            "agent_caleb_ross",
        ],
        "buttons": [
            {
                "label": "Force sworn correction",
                "action": "force_sworn_correction",
                "voice_aliases": [
                    "sworn correction",
                    "force correction",
                    "make him correct it",
                ],
            },
            {
                "label": "Enter counter-record",
                "action": "enter_counter_record",
                "voice_aliases": [
                    "counter record",
                    "enter evidence",
                    "correct the record",
                ],
            },
            {
                "label": "Let Torah bear witness",
                "action": "torah_bears_witness",
                "voice_aliases": [
                    "torah witness",
                    "let torah speak",
                    "bear witness",
                ],
            },
        ],
        "choices": [
            {
                "label": "Force sworn correction",
                "action": "force_sworn_correction",
                "voice_aliases": [
                    "sworn correction",
                    "force correction",
                    "make him correct it",
                ],
            },
            {
                "label": "Enter counter-record",
                "action": "enter_counter_record",
                "voice_aliases": [
                    "counter record",
                    "enter evidence",
                    "correct the record",
                ],
            },
            {
                "label": "Let Torah bear witness",
                "action": "torah_bears_witness",
                "voice_aliases": [
                    "torah witness",
                    "let torah speak",
                    "bear witness",
                ],
            },
        ],
        "action_results": {
            "force_sworn_correction": {
                "lines": [
                    "Brooks seats the supervisor away from the sink and makes him dictate the correction before two witnesses. He admits the bypass order was his.",
                    "When his name replaces the operators' names in the pressure log, the cups on the desk go flat. The station stops assigning bitterness to them.",
                ],
                "resource_changes": {
                    "squad.morale": 1,
                },
                "environment_state_changes": [
                    "bitter_water_false_witness_confessed",
                    {"key": "site.bitter_water_pump_station.resolved", "value": "confession_corrected_false_witness"},
                    {"key": "thread.bitter_water_statement_arc.sin", "value": "false_witness"},
                    {"key": "thread.bitter_water_statement_arc.resolution", "value": "sworn_correction"},
                    {"key": "character.brooks.command_confidence", "delta": 2},
                    {"key": "character.specialist_mina_park.stress", "delta": -1},
                ],
            },
            "enter_counter_record": {
                "lines": [
                    "Park builds the counter-record from timestamps, valve position, and witness tape. She does not need the supervisor's confession to prove the lie.",
                    "The black ring in the sample basin breaks into grit. The phenomenon accepts the corrected record, but Park keeps checking every label twice.",
                ],
                "resource_changes": {
                    "squad.morale": 0,
                },
                "environment_state_changes": [
                    "bitter_water_counter_record_entered",
                    {"key": "site.bitter_water_pump_station.resolved", "value": "evidence_corrected_false_witness"},
                    {"key": "thread.bitter_water_statement_arc.sin", "value": "false_witness"},
                    {"key": "thread.bitter_water_statement_arc.resolution", "value": "counter_record"},
                    {"key": "character.specialist_mina_park.stress", "delta": 2},
                    {"key": "character.specialist_mina_park.mental_state", "value": "focused"},
                ],
            },
            "torah_bears_witness": {
                "lines": [
                    "Torah reads the false statement aloud and stops before the operator's name. He says the accusation has been carried by the wrong body.",
                    "The tap coughs once and runs clear. The log dries from the signature line outward, but Torah cannot get the bitter taste out of his mouth.",
                ],
                "resource_changes": {
                    "squad.morale": 1,
                },
                "environment_state_changes": [
                    "torah_bore_false_witness_assignment",
                    {"key": "site.bitter_water_pump_station.resolved", "value": "torah_interrupted_false_witness"},
                    {"key": "thread.bitter_water_statement_arc.sin", "value": "false_witness"},
                    {"key": "thread.bitter_water_statement_arc.resolution", "value": "torah_witness"},
                    {"key": "character.torah.contamination", "delta": 2},
                    {"key": "character.brooks.command_confidence", "delta": -1},
                ],
            },
        },
        "outcomes": {
            "force_sworn_correction": {
                "lines": [
                    "Brooks seats the supervisor away from the sink and makes him dictate the correction before two witnesses. He admits the bypass order was his.",
                    "When his name replaces the operators' names in the pressure log, the cups on the desk go flat. The station stops assigning bitterness to them.",
                ],
                "resource_changes": {
                    "squad.morale": 1,
                },
                "environment_state_changes": [
                    "bitter_water_false_witness_confessed",
                    {"key": "site.bitter_water_pump_station.resolved", "value": "confession_corrected_false_witness"},
                    {"key": "thread.bitter_water_statement_arc.sin", "value": "false_witness"},
                    {"key": "thread.bitter_water_statement_arc.resolution", "value": "sworn_correction"},
                    {"key": "character.brooks.command_confidence", "delta": 2},
                    {"key": "character.specialist_mina_park.stress", "delta": -1},
                ],
            },
            "enter_counter_record": {
                "lines": [
                    "Park builds the counter-record from timestamps, valve position, and witness tape. She does not need the supervisor's confession to prove the lie.",
                    "The black ring in the sample basin breaks into grit. The phenomenon accepts the corrected record, but Park keeps checking every label twice.",
                ],
                "resource_changes": {
                    "squad.morale": 0,
                },
                "environment_state_changes": [
                    "bitter_water_counter_record_entered",
                    {"key": "site.bitter_water_pump_station.resolved", "value": "evidence_corrected_false_witness"},
                    {"key": "thread.bitter_water_statement_arc.sin", "value": "false_witness"},
                    {"key": "thread.bitter_water_statement_arc.resolution", "value": "counter_record"},
                    {"key": "character.specialist_mina_park.stress", "delta": 2},
                    {"key": "character.specialist_mina_park.mental_state", "value": "focused"},
                ],
            },
            "torah_bears_witness": {
                "lines": [
                    "Torah reads the false statement aloud and stops before the operator's name. He says the accusation has been carried by the wrong body.",
                    "The tap coughs once and runs clear. The log dries from the signature line outward, but Torah cannot get the bitter taste out of his mouth.",
                ],
                "resource_changes": {
                    "squad.morale": 1,
                },
                "environment_state_changes": [
                    "torah_bore_false_witness_assignment",
                    {"key": "site.bitter_water_pump_station.resolved", "value": "torah_interrupted_false_witness"},
                    {"key": "thread.bitter_water_statement_arc.sin", "value": "false_witness"},
                    {"key": "thread.bitter_water_statement_arc.resolution", "value": "torah_witness"},
                    {"key": "character.torah.contamination", "delta": 2},
                    {"key": "character.brooks.command_confidence", "delta": -1},
                ],
            },
        },
        "story_followups": {
            "force_sworn_correction": {
                "event_id": "bitter_water_cooldown_interlude",
                "trigger_key": "bitter_water_cooldown_after_confession",
                "immediate": True,
                "queued_line": "The pump station releases pressure after the correction is filed. Nobody drinks from the sink."
            },
            "enter_counter_record": {
                "event_id": "bitter_water_cooldown_interlude",
                "trigger_key": "bitter_water_cooldown_after_counter_record",
                "immediate": True,
                "queued_line": "The station accepts the counter-record. Park keeps the original lie sealed in a dry evidence box."
            },
            "torah_bears_witness": {
                "event_id": "bitter_water_cooldown_interlude",
                "trigger_key": "bitter_water_cooldown_after_torah_witness",
                "immediate": True,
                "queued_line": "The tap runs clear. Torah asks for no water on the ride back."
            },
        },
        "followup_hooks": [
            "bitter_water_false_witness_confessed",
            "bitter_water_counter_record_entered",
            "torah_bore_false_witness_assignment",
        ],
        "corpus_anchors": [
            "world_english_bible:00192",
            "cdc_environmental_infection_control_2019:00003",
            "lovecraft_colour_out_of_space_pg68236:00004",
        ],
        "corpus_influences": corpus_influences(),
        "corpus_anchor_points": anchors,
        "story_thread": {
            "id": "bitter_water_statement_arc",
            "role": "sin identified and local phenomenon resolved",
        },
        "tone_notes": "This beat should give closure on the local phenomenon: the sin was false witness, and the anomaly stops when the lie is answered by confession, counter-record, or Torah's costly witness.",
    }


def upsert_room(rooms_payload: dict[str, Any]) -> None:
    rooms = rooms_payload.setdefault("rooms", [])
    for room in rooms:
        if isinstance(room, dict) and room.get("id") in OLD_MISSION_IDS:
            room["active"] = False
            room["set_aside_reason"] = "Superseded for active testing by the three-layer scenario generation process."
    new_record = room_record()
    for index, room in enumerate(rooms):
        if isinstance(room, dict) and room.get("id") == NEW_ROOM_ID:
            rooms[index] = new_record
            return
    rooms.append(new_record)


def upsert_events(events_payload: dict[str, Any]) -> None:
    room_events = events_payload.setdefault("room_events", {})
    room_events[NEW_ROOM_ID] = [entry_event()]
    special_events = events_payload.setdefault("special_events", {})
    special_events["bitter_water_cooldown_interlude"] = cooldown_interlude()
    special_events["bitter_water_revelation_debrief"] = revelation_debrief()


def update_deck(deck_payload: dict[str, Any]) -> None:
    deck_payload["first_room_after_opening"] = NEW_ROOM_ID
    deck_payload["starter_rooms"] = [NEW_ROOM_ID]
    pools = deck_payload.setdefault("room_pools", {})
    for pool_name in ["mission", "branch", "straight_noncombat", "recovery", "random_non_special"]:
        pools[pool_name] = [NEW_ROOM_ID]
    pools.setdefault("enemy", [])
    pools.setdefault("ship_crisis", [])


def main() -> int:
    rooms_payload = load_json(ROOMS_PATH)
    events_payload = load_json(EVENTS_PATH)
    deck_payload = load_json(DECK_PATH)
    upsert_room(rooms_payload)
    upsert_events(events_payload)
    update_deck(deck_payload)
    write_json(ROOMS_PATH, rooms_payload)
    write_json(EVENTS_PATH, events_payload)
    write_json(DECK_PATH, deck_payload)
    print(f"ADDED_THREE_LAYER_SCENARIO {NEW_ROOM_ID}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
