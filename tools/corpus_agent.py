#!/usr/bin/env python3
"""Extract source motifs and transform them into Fleshpunk design seeds."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import textwrap
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
GENERATED_DIR = ROOT / "generated"
CORPUS_DIR = GENERATED_DIR / "corpus"
TEXTS_DIR = CORPUS_DIR / "texts"
SOURCES_PATH = CORPUS_DIR / "public_domain_sources.json"
MOTIFS_PATH = CORPUS_DIR / "motifs.json"
SEEDS_PATH = CORPUS_DIR / "fleshpunk_seeds.json"
NIGHTMARE_FRAGMENTS_PATH = CORPUS_DIR / "nightmare_voyage_fragments.json"
NIGHTMARE_INDEX_PATH = CORPUS_DIR / "nightmare_voyage_corpus_index.json"
ROOMS_PATH = ROOT / "room_dialogue.json"
RUN_MANAGER_PATH = ROOT / "run_manager.gd"

GUTENBERG_START_RE = re.compile(r"\*\*\*\s*START OF (?:THE|THIS) PROJECT GUTENBERG EBOOK[^\n]*\*\*\*", re.IGNORECASE)
GUTENBERG_END_RE = re.compile(r"\*\*\*\s*END OF (?:THE|THIS) PROJECT GUTENBERG EBOOK[^\n]*\*\*\*", re.IGNORECASE)
WORD_RE = re.compile(r"[a-z][a-z'-]+", re.IGNORECASE)
ACTION_CASE_RE_TEMPLATE = r'^{indent}"([^"]+)":\s*$'
WORLD_ACTIONS = {
    "proceed",
    "combat",
    "browse_wares",
    "restart_run",
    "observe",
    "seal",
    "quarantine",
    "ration",
    "wake_officer",
    "repair",
    "reroute",
    "dock",
    "recover",
    "send_party",
    "destroy",
    "vent",
    "intercept",
}

MOTIF_GROUPS: dict[str, dict[str, list[str]]] = {
    "locations": {
        "subterranean_route": ["cave", "cavern", "tunnel", "shaft", "gallery", "abyss", "underground", "subterranean", "crater"],
        "ocean_pressure": ["sea", "ocean", "submarine", "nautilus", "reef", "depth", "pressure", "current", "diving"],
        "polar_expedition": ["ice", "antarctic", "snow", "glacier", "polar", "frost", "white", "cold", "latitude"],
        "island_system": ["island", "shore", "beach", "colony", "settlement", "harbor", "coast", "reef"],
        "sealed_house_or_lab": ["house", "cellar", "laboratory", "room", "vault", "study", "library", "attic", "basement"],
        "ancient_ruin": ["ruin", "city", "cyclopean", "monolith", "stone", "temple", "wall", "arch", "masonry"],
    },
    "character_functions": {
        "mission_commander": ["captain", "commander", "leader", "chief", "authority", "orders", "command"],
        "scientist_witness": ["professor", "doctor", "naturalist", "geologist", "chemist", "student", "observer"],
        "engineer_operator": ["engineer", "mechanic", "machine", "engine", "apparatus", "instrument", "valve"],
        "hidden_patron": ["unknown", "invisible", "mysterious", "secret", "concealed", "anonymous", "unseen"],
        "crew_or_party": ["crew", "party", "companion", "sailor", "men", "expedition", "survivors"],
        "tainted_family_or_cult": ["family", "ancestor", "blood", "heir", "cult", "rite", "worship", "lineage"],
    },
    "machines_or_systems": {
        "sealed_vessel": ["vessel", "ship", "submarine", "boat", "nautilus", "hull", "cabin", "compartment"],
        "pressure_system": ["pressure", "valve", "pump", "current", "flow", "tide", "compression", "gauge"],
        "excavation_system": ["drill", "pickaxe", "shaft", "mine", "boring", "descent", "rope", "ladder"],
        "signal_or_record": ["signal", "message", "manuscript", "letter", "journal", "record", "document", "cipher"],
        "biological_process": ["growth", "organism", "creature", "tissue", "blood", "disease", "decay", "fungus", "cell"],
        "navigation_system": ["map", "compass", "latitude", "longitude", "route", "chart", "bearing", "course"],
    },
    "survival_pressures": {
        "hunger_and_ration": ["hunger", "thirst", "ration", "provisions", "food", "water", "starvation", "famine"],
        "isolation": ["alone", "silence", "solitude", "lost", "deserted", "abandoned", "remote"],
        "panic_or_mutiny": ["panic", "madness", "fear", "mutiny", "terror", "riot", "despair", "frenzy"],
        "injury_and_exhaustion": ["wound", "injury", "blood", "fatigue", "fever", "weakness", "pain", "sick"],
        "contamination": ["poison", "taint", "contamination", "infection", "disease", "corruption", "decay"],
        "pursuit_or_hunt": ["pursuit", "hunt", "chase", "attack", "enemy", "monster", "beast", "track"],
        "knowledge_cost": ["secret", "forbidden", "terrible", "truth", "revelation", "discovery", "horror", "unknown"],
    },
}

ROOM_AFFINITY: dict[str, list[str]] = {
    "subterranean_route": ["bone_corridor", "organ_chamber_red"],
    "ocean_pressure": ["healing_pool", "organ_chamber_red"],
    "polar_expedition": ["bone_corridor", "split_green_corridor"],
    "island_system": ["egg_corridor", "healing_pool"],
    "sealed_house_or_lab": ["red_corridor", "organ_chamber_red"],
    "ancient_ruin": ["bone_corridor", "spiked_red_corridor"],
    "mission_commander": ["red_corridor", "organ_chamber_red"],
    "scientist_witness": ["organ_chamber_red", "healing_pool"],
    "engineer_operator": ["amber_corridor", "split_red_corridor"],
    "hidden_patron": ["red_corridor", "split_green_corridor"],
    "crew_or_party": ["egg_corridor", "bone_corridor"],
    "tainted_family_or_cult": ["organ_chamber_red", "healing_pool"],
    "sealed_vessel": ["organ_chamber_red", "red_corridor"],
    "pressure_system": ["spiked_red_corridor", "split_red_corridor"],
    "excavation_system": ["bone_corridor", "amber_corridor"],
    "signal_or_record": ["red_corridor", "split_green_corridor"],
    "biological_process": ["healing_pool", "egg_corridor"],
    "navigation_system": ["split_green_corridor", "split_red_corridor"],
    "hunger_and_ration": ["amber_corridor", "egg_corridor"],
    "isolation": ["red_corridor", "bone_corridor"],
    "panic_or_mutiny": ["split_red_corridor", "spiked_red_corridor"],
    "injury_and_exhaustion": ["healing_pool", "red_corridor"],
    "contamination": ["healing_pool", "organ_chamber_red"],
    "pursuit_or_hunt": ["spiked_red_corridor", "bone_corridor"],
    "knowledge_cost": ["organ_chamber_red", "red_corridor"],
}

ACTION_AFFINITY: dict[str, list[str]] = {
    "subterranean_route": ["listen_at_green_split", "probe_bones", "mark_red_branch"],
    "ocean_pressure": ["study_pool", "drink_pool", "observe_organ_chamber"],
    "polar_expedition": ["retreat", "probe_bones", "listen_at_green_split"],
    "island_system": ["harvest_eggs", "study_pool", "proceed"],
    "sealed_house_or_lab": ["observe_organ_chamber", "study_pool", "proceed"],
    "ancient_ruin": ["probe_bones", "follow_marked_plates", "scavenge_bones"],
    "mission_commander": ["mark_red_branch", "proceed", "retreat"],
    "scientist_witness": ["study_pool", "observe_organ_chamber", "probe_bones"],
    "engineer_operator": ["probe_amber_cache", "vent_red_split", "break_amber_cache"],
    "hidden_patron": ["pay_resin_toll", "skip_resin_toll", "browse_wares"],
    "crew_or_party": ["retreat", "combat", "proceed"],
    "tainted_family_or_cult": ["take_mutation", "study_pool", "leave_mutation"],
    "sealed_vessel": ["observe_organ_chamber", "pay_resin_toll", "proceed"],
    "pressure_system": ["vent_red_split", "push_through_spikes", "break_spike_lane"],
    "excavation_system": ["break_amber_cache", "scavenge_bones", "cut_heart_cords"],
    "signal_or_record": ["mark_red_branch", "study_pool", "listen_red_wall"],
    "biological_process": ["disturb_pool", "drink_pool", "take_mutation"],
    "navigation_system": ["mark_red_branch", "listen_at_green_split", "proceed"],
    "hunger_and_ration": ["pay_resin_toll", "skip_resin_toll", "harvest_eggs"],
    "isolation": ["proceed", "retreat", "listen_red_wall"],
    "panic_or_mutiny": ["retreat", "rush_red_split", "combat"],
    "injury_and_exhaustion": ["drink_pool", "study_pool", "disturb_pool"],
    "contamination": ["take_mutation", "study_pool", "disturb_green_spores"],
    "pursuit_or_hunt": ["combat", "retreat", "push_through_spikes"],
    "knowledge_cost": ["study_pool", "observe_organ_chamber", "take_symbiote"],
}

TRANSFORM_LINES: dict[str, dict[str, str]] = {
    "subterranean_route": {
        "seed": "A descent route becomes a warm bore through layered tissue; each safer landmark is also a place the organism can remember Hymn.",
        "mechanic": "Repeated mapping lowers danger now but creates marked-route pressure that can later spring a snare.",
    },
    "ocean_pressure": {
        "seed": "An undersea pressure journey becomes a sealed fluid corridor that equalizes through valves grown from living membrane.",
        "mechanic": "Opening pressure buys passage or healing, but raises corruption when the fluid enters Hymn's body.",
    },
    "polar_expedition": {
        "seed": "A polar rescue route becomes a sterile white marrow field where warmth, signal, and memory drain together.",
        "mechanic": "Waiting and listening reduce immediate danger but increase isolation pressure and delayed hunter attention.",
    },
    "island_system": {
        "seed": "A survival island becomes a self-contained organ colony that supplies tools only when fed useful losses.",
        "mechanic": "Scavenging builds biomass, while repeated dependence teaches the room to price basic access.",
    },
    "sealed_house_or_lab": {
        "seed": "A haunted house or laboratory becomes a sealed operator chamber whose walls preserve failed procedures as tissue reflexes.",
        "mechanic": "Studying records unlocks safer choices but adds knowledge pressure and signal degradation.",
    },
    "ancient_ruin": {
        "seed": "An ancient ruin becomes old bio-infrastructure: bone masonry, maintenance rites, and organs mistaken for monuments.",
        "mechanic": "Respecting markings lowers danger; stripping relic tissue gives biomass and pushes greed or hunter pressure.",
    },
    "mission_commander": {
        "seed": "A commander figure becomes Chorus pressure: remote authority, incomplete orders, and mission logic that prices hesitation.",
        "mechanic": "Following orders should clarify the route while increasing a pressure the player can hear in later warnings.",
    },
    "scientist_witness": {
        "seed": "A scientist-witness becomes Hymn's field report discipline: observe first, name the mechanism, then admit the cost.",
        "mechanic": "Study actions should reveal a safer line or pressure forecast while trading time, danger, or corruption.",
    },
    "engineer_operator": {
        "seed": "An engineer-operator becomes a maintenance intelligence: valves, tolls, and repair reflexes that treat Hymn as a tool.",
        "mechanic": "Technical interactions should offer a clean manipulation and a forceful shortcut with different pressure costs.",
    },
    "hidden_patron": {
        "seed": "A hidden patron becomes unseen intervention by Chorus, the merchant, or the organism, helpful only because it creates leverage.",
        "mechanic": "Aid should solve the immediate room and leave a visible claim, debt, or dependency marker.",
    },
    "crew_or_party": {
        "seed": "An expedition party becomes internal company: symbiotes, old signals, and body systems arguing without becoming separate narrators.",
        "mechanic": "Group-pressure events should make retreat, combat, and waiting each teach the director a different habit.",
    },
    "tainted_family_or_cult": {
        "seed": "A tainted bloodline or cult becomes facility operator residue: maintenance rites remembered by tissue, not people.",
        "mechanic": "Ritual or inheritance choices should grant access while raising corruption or knowledge pressure without exposing clone truth.",
    },
    "sealed_vessel": {
        "seed": "A vessel becomes a ribbed transit organ with compartments that open only when Hymn matches its pulse economy.",
        "mechanic": "Paying or synchronizing advances safely; forcing bulkheads creates damage, noise, and future pursuit.",
    },
    "pressure_system": {
        "seed": "Mechanical pressure becomes vascular pressure: valves, clots, vents, and arterial doors that punish repeated shortcuts.",
        "mechanic": "Venting reduces danger and gives biomass, but overuse makes later rooms overpressurized.",
    },
    "excavation_system": {
        "seed": "Excavation becomes surgical trespass through marrow and amber, with every tool doubling as a wound.",
        "mechanic": "Breaking hard tissue yields resources at health cost; probing finds quiet routes with lower reward.",
    },
    "signal_or_record": {
        "seed": "Journals and signals become Chorus packets with missing checksum, old operator notes, and memory that may not belong to Hymn.",
        "mechanic": "Reading clarifies choices but can raise corruption, dependence, or knowledge pressure.",
    },
    "biological_process": {
        "seed": "Alien process becomes tissue logic: growth, rot, repair, and appetite operate as infrastructure, not scenery.",
        "mechanic": "Healing and growth choices are explicit transactions that restore stats while leaving residue.",
    },
    "navigation_system": {
        "seed": "Charts and bearings become pulse maps, scar routes, and branch markings that the organism can counter-map.",
        "mechanic": "Route skill reduces immediate danger, but repeated use schedules route-specific retaliation.",
    },
    "hunger_and_ration": {
        "seed": "Ration pressure becomes biomass economics: the body, merchant, and corridor all account for stored meat.",
        "mechanic": "Paying biomass avoids harm; skipping tolls accrues claim that can become a reckoning encounter.",
    },
    "isolation": {
        "seed": "Isolation becomes signal loss between Hymn and Chorus; quiet rooms are safer but less accountable.",
        "mechanic": "Silence can reduce danger while increasing dependence on internal voices, symbiotes, or memory residue.",
    },
    "panic_or_mutiny": {
        "seed": "Crew panic becomes internal system disagreement: organs, symbiotes, and mission orders pulling against each other.",
        "mechanic": "Fast choices avoid one cost and add another, making repeated panic legible to the director.",
    },
    "injury_and_exhaustion": {
        "seed": "Exhaustion becomes body debt: every forced route spends tissue that the facility can recognize later.",
        "mechanic": "Damage choices should state the wound, the resource gained, and which pressure axis noticed it.",
    },
    "contamination": {
        "seed": "Contamination becomes useful corruption: the facility repairs Hymn by making her more legible to itself.",
        "mechanic": "Healing, mutation, and study can all restore control while moving corruption toward a lock.",
    },
    "pursuit_or_hunt": {
        "seed": "Hunt logic becomes immune response: the organism dispatches specialized hunters to answer repeated avoidance or noise.",
        "mechanic": "Avoiding combat is valid but must increment a visible pressure that eventually sends a named response.",
    },
    "knowledge_cost": {
        "seed": "Forbidden knowledge becomes operational truth that helps Hymn survive while crossing her knowledge boundaries.",
        "mechanic": "Lore choices should grant route clarity or safer actions, never clone truth, and should carry pressure.",
    },
}

NIGHTMARE_FRAGMENT_PROFILES: list[dict[str, Any]] = [
    {
        "id": "sailcloth_brine_water_test",
        "source_ids": ["verne_survivors_chancellor"],
        "search_terms": ["canvas", "sail", "water", "briny", "salt", "rain"],
        "source_circumstance": "Canvas or sailcloth expected to preserve water instead contaminates it with salt.",
        "room_seed": "Recovered quarantine screens or emergency sailcloth around salvage become damp with brine despite sealed air.",
        "escalation_thread": [
            "screen edge logs dry",
            "screen returns damp after a procedure",
            "ward water or oxygen scrubber tests salty",
            "captain chooses between hard seal, rationing, or risky repair"
        ],
        "ship_state_hooks": ["water_compromised", "medical_fatigue", "quarantine_screens_stressed"],
        "suggested_actions": ["observe", "quarantine", "ration", "seal"],
    },
    {
        "id": "pump_bucket_line_emergency",
        "source_ids": ["verne_survivors_chancellor"],
        "search_terms": ["pump", "bucket", "hold", "water", "line", "hands"],
        "source_circumstance": "A ship survives by organized pump and bucket-line labor after water rises in the hold.",
        "room_seed": "A pressure compartment or flooded lock demands a crew line, exposing fatigue, discipline, and manpower limits.",
        "escalation_thread": [
            "small leak becomes watch labor",
            "crew line forms under officer command",
            "fatigue causes missed handoff or injury",
            "captain chooses between machinery, crew rest, or sealed loss"
        ],
        "ship_state_hooks": ["pressure_stability", "manpower", "department_fatigue"],
        "suggested_actions": ["repair", "ration", "seal", "reroute"],
    },
    {
        "id": "southward_rescue_obsession",
        "source_ids": ["verne_antarctic_mystery"],
        "search_terms": ["survivors", "jane", "succour", "rescue", "anchor", "ice"],
        "source_circumstance": "A practical expedition pushes south to rescue named survivors from an earlier failed voyage.",
        "room_seed": "A falling rescue signal names a previous ship or launch order and pulls officers toward an expensive intercept.",
        "escalation_thread": [
            "signal names survivors",
            "record contradicts current ship chronology",
            "officers split over rescue duty versus stores",
            "later packet returns with altered names or impossible dates"
        ],
        "ship_state_hooks": ["morale", "stores", "officer_trust", "route_memory"],
        "suggested_actions": ["observe", "wake_officer", "quarantine", "proceed"],
    },
    {
        "id": "ice_preserved_shutters_hinges",
        "source_ids": ["lovecraft_at_mountains_of_madness"],
        "search_terms": ["shutters", "hinges", "windows", "ice", "wood", "preserved"],
        "source_circumstance": "Ice-preserved shutters and hinge placement imply old architecture used from an unexpected side.",
        "room_seed": "A derelict hatch, shutter, or lock shows wear from the wrong side and turns a salvage scene into evidence.",
        "escalation_thread": [
            "inspect preserved hinge",
            "wear pattern contradicts access route",
            "copied pattern appears on ship fitting",
            "captain chooses to mark, seal, or exploit the orientation"
        ],
        "ship_state_hooks": ["navigation_uncertainty", "system_anomaly", "science_progress"],
        "suggested_actions": ["observe", "seal", "repair", "reroute"],
    },
    {
        "id": "sealed_vessel_pressure_domain",
        "source_ids": ["verne_twenty_thousand_leagues"],
        "search_terms": ["nautilus", "pressure", "compartment", "hatch", "depth", "electric"],
        "source_circumstance": "A sealed vessel survives a hostile pressure domain through compartments, apparatus, and command discipline.",
        "room_seed": "An intercepted vessel or ship subsystem behaves like a pressure domain with legible apparatus but alien priorities.",
        "escalation_thread": [
            "instrument reading makes pressure legible",
            "officer proposes technical entry",
            "apparatus obeys a different boundary",
            "ship gains resource but inherits a pressure habit"
        ],
        "ship_state_hooks": ["pressure_manifold_stress", "replacement_machinery", "officer_confidence"],
        "suggested_actions": ["dock", "repair", "reroute", "observe"],
    },
    {
        "id": "projectile_launch_authority",
        "source_ids": ["verne_moon_voyage"],
        "search_terms": ["projectile", "launch", "calculation", "trajectory", "observatory", "oxygen"],
        "source_circumstance": "A mission reduces human survival to launch calculations, institutional authority, and trajectory tolerances.",
        "room_seed": "A falling object carries a launch order, trajectory correction, or oxygen calculation that predates the captain's decision.",
        "escalation_thread": [
            "calculation arrives before order",
            "navigator can use it",
            "using it confirms the future record",
            "refusing it costs fuel or certainty"
        ],
        "ship_state_hooks": ["navigation_certainty", "fuel", "oxygen", "doctrine"],
        "suggested_actions": ["observe", "reroute", "wake_officer", "proceed"],
    },
    {
        "id": "island_hidden_assistance",
        "source_ids": ["verne_mysterious_island"],
        "search_terms": ["unknown", "mysterious", "island", "resources", "engineer", "help"],
        "source_circumstance": "A survival system appears to reward practical work through hidden assistance and resource discoveries.",
        "room_seed": "A salvage site supplies exactly needed stores, implying a hidden allocator in the falling debris field.",
        "escalation_thread": [
            "useful resource appears",
            "quartermaster notices impossible fitness",
            "second gift demands a pattern of behavior",
            "captain chooses to exploit, refuse, or audit the supply"
        ],
        "ship_state_hooks": ["stores", "quartermaster_trust", "debt", "attention"],
        "suggested_actions": ["observe", "recover", "ration", "seal"],
    },
    {
        "id": "well_water_contamination",
        "source_ids": ["lovecraft_colour_out_of_space"],
        "search_terms": ["well", "water", "colour", "vegetation", "poison", "blasted"],
        "source_circumstance": "A local water source becomes the carrier of contamination, visible first through taste and changed growth.",
        "room_seed": "Recovered water, condenser output, or hydroponic stock tests clean by instrument but wrong by taste or growth.",
        "escalation_thread": [
            "resource tests usable",
            "crew reports taste or growth change",
            "medical and quartermaster disagree",
            "captain chooses ration, jettison, or controlled use"
        ],
        "ship_state_hooks": ["water", "food", "contamination", "morale"],
        "suggested_actions": ["ration", "quarantine", "observe", "seal"],
    },
    {
        "id": "cellar_investigation_apparatus",
        "source_ids": ["lovecraft_shunned_house"],
        "search_terms": ["cellar", "vapour", "fungus", "wall", "sick", "house"],
        "source_circumstance": "Investigators use apparatus and records to make a hostile domestic space mechanically legible.",
        "room_seed": "A lower compartment sickens crew until instruments expose a wall, vapor, or vent behaving like a resident organism.",
        "escalation_thread": [
            "crew illness localizes to compartment",
            "apparatus maps vapor or residue",
            "repair attempt wakes the wall/vent",
            "captain chooses purge, seal, or continued study"
        ],
        "ship_state_hooks": ["medical_supplies", "contamination", "science_progress", "hull_integrity"],
        "suggested_actions": ["observe", "repair", "quarantine", "seal"],
    },
    {
        "id": "record_identity_continuity",
        "source_ids": ["lovecraft_charles_dexter_ward"],
        "search_terms": ["letter", "record", "handwriting", "ancestor", "portrait", "laboratory"],
        "source_circumstance": "Records and handwriting make identity continuity dangerous before any monster is visible.",
        "room_seed": "A recovered log, officer signature, or registry copy proves continuity between incompatible people or dates.",
        "escalation_thread": [
            "record appears ordinary",
            "handwriting or signature matches impossible source",
            "officer wants suppression or publication",
            "later order arrives in that same hand"
        ],
        "ship_state_hooks": ["officer_trust", "records", "morale", "route_memory"],
        "suggested_actions": ["observe", "wake_officer", "seal", "quarantine"],
    },
    {
        "id": "shutter_escape_route",
        "source_ids": ["lovecraft_shadow_over_innsmouth"],
        "search_terms": ["shutter", "window", "room", "street", "escape", "bolt"],
        "source_circumstance": "A shutter or window becomes the practical route out of pursuit.",
        "room_seed": "A shipboard shutter, lock, or exterior maintenance path offers escape from a boarding or pressure event at a cost.",
        "escalation_thread": [
            "normal passage is watched or blocked",
            "shutter route is found",
            "using it leaves a visible route marker",
            "later pursuer or pressure follows that marker"
        ],
        "ship_state_hooks": ["security_detail", "hull_stress", "pursuit_pressure"],
        "suggested_actions": ["seal", "repair", "observe", "proceed"],
    },
    {
        "id": "hidden_growth_visible_tracks",
        "source_ids": ["lovecraft_dunwich_horror"],
        "search_terms": ["invisible", "tracks", "prints", "growth", "house", "cattle"],
        "source_circumstance": "An unseen growing threat becomes legible through tracks, damage, and resource loss.",
        "room_seed": "An invisible pressure or organism crosses ship systems, visible only through bent rails, missing stores, and deck marks.",
        "escalation_thread": [
            "damage appears without actor",
            "tracks define size and route",
            "resource loss proves appetite",
            "captain chooses trap, seal, or sacrifice stores"
        ],
        "ship_state_hooks": ["stores", "hull_materials", "security_stress", "contamination"],
        "suggested_actions": ["observe", "seal", "repair", "ration"],
    },
]

NIGHTMARE_INDEX_PROFILES: list[dict[str, Any]] = [
    {
        "id": "sealed_pressure_vessel",
        "role": "premise",
        "terms": ["vessel", "ship", "submarine", "hull", "compartment", "hatch", "pressure", "depth", "valve"],
        "room_need": "sealed spaces, pressure domains, and apparatus that make a hazard mechanically legible",
        "nightmare_use": "Turn sealed craft or rooms into ship compartments, recovery targets, pressure manifolds, and officer repair arguments.",
        "suggested_actions": ["observe", "dock", "repair", "reroute", "seal"],
        "state_hooks": ["pressure_manifold_stress", "hull_integrity", "engineering_fatigue"],
    },
    {
        "id": "flooded_hold_labor",
        "role": "procedure",
        "terms": ["pump", "bucket", "hold", "leak", "water", "hands", "crew", "watch", "tired"],
        "room_need": "procedural labor under time pressure",
        "nightmare_use": "Use as a model for crew lines, watch rotations, missed handoffs, and fatigue-triggered followups.",
        "suggested_actions": ["repair", "ration", "seal", "reroute"],
        "state_hooks": ["manpower", "department_fatigue", "pressure_stability"],
    },
    {
        "id": "water_food_contamination",
        "role": "resource",
        "terms": ["water", "well", "drink", "taste", "poison", "taint", "food", "vegetation", "salt", "brine"],
        "room_need": "resources that test usable but become suspect through taste, growth, or secondary evidence",
        "nightmare_use": "Tie salvage and lifeboat supplies to rationing, medical disagreement, and delayed contamination costs.",
        "suggested_actions": ["ration", "quarantine", "observe", "seal"],
        "state_hooks": ["water", "food", "contamination", "morale"],
    },
    {
        "id": "ration_hunger_stores",
        "role": "resource",
        "terms": ["hunger", "thirst", "ration", "provisions", "food", "water", "starvation", "famine", "stores"],
        "room_need": "survival accounting and stores pressure",
        "nightmare_use": "Make cautious choices cost stores, make risky choices preserve stores while creating crew or contamination debt.",
        "suggested_actions": ["ration", "recover", "quarantine", "proceed"],
        "state_hooks": ["stores", "crew_morale", "quartermaster_trust"],
    },
    {
        "id": "rescue_signal_survivors",
        "role": "premise",
        "terms": ["survivors", "rescue", "succour", "signal", "lost", "expedition", "party", "boat", "ice"],
        "room_need": "named rescue obligations that compete with route, stores, and officer judgment",
        "nightmare_use": "Use rescue calls as captain-level moral pressure with later record contradictions.",
        "suggested_actions": ["observe", "intercept", "wake_officer", "proceed"],
        "state_hooks": ["morale", "stores", "route_memory", "officer_trust"],
    },
    {
        "id": "impossible_record_identity",
        "role": "evidence",
        "terms": ["record", "letter", "journal", "manuscript", "handwriting", "signature", "portrait", "ancestor", "identity"],
        "room_need": "paper evidence that changes the meaning of people, dates, and orders",
        "nightmare_use": "Use logs, registry copies, and signatures as contradictions that can start followups without revealing everything.",
        "suggested_actions": ["observe", "wake_officer", "seal", "quarantine"],
        "state_hooks": ["records", "officer_trust", "morale", "route_memory"],
    },
    {
        "id": "wrong_side_architecture",
        "role": "evidence",
        "terms": ["shutter", "hinge", "window", "door", "wall", "opening", "inside", "outside", "wear"],
        "room_need": "physical evidence that proves a route or mechanism was used from the wrong side",
        "nightmare_use": "Turn hinges, hatches, and wear marks into concrete evidence for reroute, seal, or exploit choices.",
        "suggested_actions": ["observe", "seal", "repair", "reroute"],
        "state_hooks": ["navigation_uncertainty", "system_anomaly", "science_progress"],
    },
    {
        "id": "escape_route_pursuit",
        "role": "followup",
        "terms": ["escape", "pursuit", "street", "window", "shutter", "bolt", "door", "flight", "chase"],
        "room_need": "routes that solve a current danger but mark the ship for later pursuit",
        "nightmare_use": "Let escape choices create route markers that later pressure, boarders, or security details can follow.",
        "suggested_actions": ["seal", "repair", "observe", "proceed"],
        "state_hooks": ["security_detail", "hull_stress", "pursuit_pressure"],
    },
    {
        "id": "apparatus_investigation",
        "role": "procedure",
        "terms": ["apparatus", "instrument", "chemical", "test", "experiment", "laboratory", "measure", "record", "specimen"],
        "room_need": "investigation scenes where procedure makes dread operational",
        "nightmare_use": "Give science or medical plans concrete instruments, test limits, and failure modes.",
        "suggested_actions": ["observe", "repair", "quarantine", "seal"],
        "state_hooks": ["science_progress", "medical_supplies", "contamination"],
    },
    {
        "id": "hidden_actor_assistance",
        "role": "complication",
        "terms": ["unknown", "mysterious", "secret", "concealed", "unseen", "help", "saved", "found", "resource"],
        "room_need": "useful aid that implies a hidden allocator or watcher",
        "nightmare_use": "Let helpful salvage solve one problem while creating debt, attention, or trust conflict.",
        "suggested_actions": ["observe", "recover", "ration", "seal"],
        "state_hooks": ["stores", "debt", "attention", "quartermaster_trust"],
    },
    {
        "id": "invisible_tracks_damage",
        "role": "evidence",
        "terms": ["invisible", "tracks", "prints", "footprints", "marks", "damage", "cattle", "growth", "trail"],
        "room_need": "unseen threats made legible by tracks, damage, and resource loss",
        "nightmare_use": "Use bent rails, missing stores, marks, and hull stress to advance a threat without showing it.",
        "suggested_actions": ["observe", "seal", "repair", "ration"],
        "state_hooks": ["stores", "hull_materials", "security_stress", "contamination"],
    },
    {
        "id": "expedition_route_navigation",
        "role": "procedure",
        "terms": ["route", "map", "chart", "bearing", "latitude", "longitude", "course", "compass", "south", "north"],
        "room_need": "navigation choices that turn story pressure into route policy",
        "nightmare_use": "Transform expedition bearings into black-hole descent routing, record contradictions, and navigator fatigue.",
        "suggested_actions": ["observe", "reroute", "proceed", "wake_officer"],
        "state_hooks": ["navigation_certainty", "route_memory", "fuel"],
    },
    {
        "id": "ancient_ruin_geometry",
        "role": "premise",
        "terms": ["ruin", "city", "stone", "wall", "arch", "masonry", "temple", "cyclopean", "ancient"],
        "room_need": "old architecture that supplies geometry, scale, and evidence",
        "nightmare_use": "Use ruin logic for derelict structures, impossible fittings, and repeated patterns copied onto the ship.",
        "suggested_actions": ["observe", "seal", "reroute", "send_party"],
        "state_hooks": ["science_progress", "navigation_uncertainty", "hull_integrity"],
    },
    {
        "id": "launch_trajectory_calculation",
        "role": "procedure",
        "terms": ["projectile", "launch", "calculation", "trajectory", "velocity", "oxygen", "observatory", "orbit"],
        "room_need": "mission math that constrains survival before people understand the full situation",
        "nightmare_use": "Use calculations as orders that may arrive before the captain authorizes them.",
        "suggested_actions": ["observe", "reroute", "wake_officer", "proceed"],
        "state_hooks": ["navigation_certainty", "oxygen", "fuel", "doctrine"],
    },
    {
        "id": "officer_command_discipline",
        "role": "officer",
        "terms": ["captain", "commander", "orders", "command", "officer", "discipline", "authority", "duty", "obey"],
        "room_need": "authority disputes and procedural discipline",
        "nightmare_use": "Use as source texture for competing officer proposals with different success odds and stress costs.",
        "suggested_actions": ["wake_officer", "observe", "repair", "seal"],
        "state_hooks": ["officer_trust", "department_fatigue", "doctrine"],
    },
    {
        "id": "crew_panic_mutiny",
        "role": "followup",
        "terms": ["panic", "mutiny", "terror", "fear", "riot", "frenzy", "despair", "madness", "crew"],
        "room_need": "crew-state escalation after repeated hard orders",
        "nightmare_use": "Use as followup pressure when a department is overworked or a captain action fails.",
        "suggested_actions": ["ration", "wake_officer", "seal", "proceed"],
        "state_hooks": ["crew_morale", "security_stress", "department_fatigue"],
    },
    {
        "id": "illness_fever_medical",
        "role": "consequence",
        "terms": ["illness", "sick", "fever", "disease", "infection", "wound", "pain", "medical", "doctor"],
        "room_need": "medical consequences that carry across followups",
        "nightmare_use": "Anchor medical plans, quarantine fatigue, contamination doubt, and costs of delayed treatment.",
        "suggested_actions": ["quarantine", "ration", "observe", "seal"],
        "state_hooks": ["medical_fatigue", "medical_supplies", "contamination"],
    },
    {
        "id": "isolation_signal_loss",
        "role": "atmosphere",
        "terms": ["alone", "silence", "solitude", "lost", "deserted", "abandoned", "remote", "signal", "voice"],
        "room_need": "isolation that changes command information",
        "nightmare_use": "Use silence and distance to justify missing reports, delayed followups, and officer uncertainty.",
        "suggested_actions": ["observe", "wake_officer", "proceed", "seal"],
        "state_hooks": ["officer_trust", "route_memory", "morale"],
    },
    {
        "id": "specimen_salvage_recovery",
        "role": "premise",
        "terms": ["specimen", "sample", "body", "object", "metal", "crate", "recover", "found", "strange"],
        "room_need": "recoverable objects with practical and investigative value",
        "nightmare_use": "Tie salvage recovery to quarantine, science progress, stores, and later evidence contradictions.",
        "suggested_actions": ["recover", "quarantine", "observe", "jettison"],
        "state_hooks": ["science_progress", "contamination", "stores"],
    },
    {
        "id": "quarantine_seal_containment",
        "role": "procedure",
        "terms": ["seal", "sealed", "closed", "quarantine", "confined", "locked", "barrier", "isolate", "contagion"],
        "room_need": "containment procedures and their social cost",
        "nightmare_use": "Use sealing as an order that solves immediate exposure while stressing crew, medicine, or access.",
        "suggested_actions": ["seal", "quarantine", "observe", "vent"],
        "state_hooks": ["quarantine_screens_stressed", "medical_fatigue", "crew_morale"],
    },
    {
        "id": "electrical_instrument_reading",
        "role": "evidence",
        "terms": ["electric", "electricity", "light", "lamp", "instrument", "gauge", "needle", "signal", "apparatus"],
        "room_need": "instrument readings that make the impossible operational",
        "nightmare_use": "Use gauges and lamps as the first contradiction before followups touch hull, water, or records.",
        "suggested_actions": ["observe", "repair", "reroute", "wake_officer"],
        "state_hooks": ["system_anomaly", "science_progress", "engineering_fatigue"],
    },
    {
        "id": "fuel_oxygen_life_support",
        "role": "resource",
        "terms": ["oxygen", "air", "breath", "fuel", "coal", "steam", "fire", "provisions", "supply"],
        "room_need": "life-support and propulsion resource pressure",
        "nightmare_use": "Use old air/fuel anxieties as stores, oxygen, and burn-window tradeoffs.",
        "suggested_actions": ["ration", "reroute", "repair", "proceed"],
        "state_hooks": ["oxygen", "fuel", "stores", "engineering_fatigue"],
    },
    {
        "id": "black_hole_relativistic_descent",
        "role": "gap",
        "terms": ["black hole", "singularity", "event horizon", "relativity", "gravity well", "spacetime"],
        "room_need": "modern black-hole descent physics and time dilation",
        "nightmare_use": "Treat as a known corpus gap; derive this from project lore and mechanics, then attach corpus artifacts for procedure/evidence.",
        "suggested_actions": ["observe", "reroute", "proceed", "wake_officer"],
        "state_hooks": ["navigation_certainty", "route_memory", "oxygen"],
        "gap_sensitive": True,
    },
    {
        "id": "department_stress_roster",
        "role": "gap",
        "terms": ["department", "roster", "shift", "stress", "fatigue score", "medical team", "engineering team"],
        "room_need": "hidden officer and department state behind action odds",
        "nightmare_use": "Treat as a known corpus gap; corpus can supply command texture, but mechanics must come from Nightmare Voyage.",
        "suggested_actions": ["wake_officer", "repair", "quarantine", "ration"],
        "state_hooks": ["department_fatigue", "officer_trust", "medical_fatigue", "engineering_fatigue"],
        "gap_sensitive": True,
    },
    {
        "id": "computer_sensor_logging",
        "role": "gap",
        "terms": ["computer", "sensor", "database", "console", "readout", "software", "checksum", "telemetry"],
        "room_need": "ship computers, logs, and sensor interfaces",
        "nightmare_use": "Treat as a known corpus gap; map manuscripts, instruments, and signals into ship logs and readouts.",
        "suggested_actions": ["observe", "repair", "reroute", "seal"],
        "state_hooks": ["records", "system_anomaly", "science_progress"],
        "gap_sensitive": True,
    },
    {
        "id": "reactor_engine_core",
        "role": "gap",
        "terms": ["reactor", "engine core", "fusion", "drive", "thruster", "plasma", "radiation"],
        "room_need": "spacecraft propulsion and reactor failures",
        "nightmare_use": "Treat as a known corpus gap; use Verne pressure and apparatus as structure, then provide project-specific engine terms.",
        "suggested_actions": ["repair", "reroute", "vent", "seal"],
        "state_hooks": ["engine_stress", "fuel", "engineering_fatigue"],
        "gap_sensitive": True,
    },
    {
        "id": "corporate_mission_protocol",
        "role": "gap",
        "terms": ["corporate", "company policy", "liability", "mission protocol", "board order", "insurance", "contract"],
        "room_need": "institutional procedure behind captain authority",
        "nightmare_use": "Treat as a known corpus gap; use expedition command and mission authority, then write original corporate protocol.",
        "suggested_actions": ["wake_officer", "observe", "proceed", "seal"],
        "state_hooks": ["doctrine", "officer_trust", "morale"],
        "gap_sensitive": True,
    },
]


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig") if path.exists() else ""


def strip_gutenberg_boilerplate(text: str) -> str:
    start = GUTENBERG_START_RE.search(text)
    if start is not None:
        text = text[start.end():]
    end = GUTENBERG_END_RE.search(text)
    if end is not None:
        text = text[:end.start()]
    return text


def count_terms(text: str, terms: list[str]) -> tuple[int, list[dict[str, int]]]:
    lower = text.lower()
    matches: list[dict[str, int]] = []
    total = 0
    for term in terms:
        pattern = r"(?<![a-z])%s(?![a-z])" % re.escape(term.lower())
        count = len(re.findall(pattern, lower))
        if count > 0:
            matches.append({"term": term, "count": count})
            total += count
    matches.sort(key=lambda item: (-int(item["count"]), str(item["term"])))
    return total, matches[:8]


def word_count(text: str) -> int:
    return len(WORD_RE.findall(text))


def get_sources() -> list[dict[str, Any]]:
    payload = load_json(SOURCES_PATH)
    works = payload.get("works", [])
    if not isinstance(works, list):
        raise ValueError("public_domain_sources.json must contain a works array")
    return [work for work in works if isinstance(work, dict)]


def get_room_ids() -> list[str]:
    if not ROOMS_PATH.exists():
        return []
    payload = load_json(ROOMS_PATH)
    rooms = payload.get("rooms", [])
    if not isinstance(rooms, list):
        return []
    return [str(room.get("id", "")) for room in rooms if isinstance(room, dict) and room.get("id")]


def existing_actions() -> set[str]:
    source = read_text(RUN_MANAGER_PATH)
    match_start = source.find("match action_id:")
    if match_start == -1:
        actions: set[str] = set()
    else:
        action_tail = source[match_start:]
        match_line = re.search(r'^([ \t]*)match action_id:\s*$', action_tail, re.MULTILINE)
        first_case = re.search(r'^([ \t]*)"[^"]+":\s*$', action_tail, re.MULTILINE)
        case_indent = first_case.group(1) if first_case else (match_line.group(1) + "\t") if match_line else "\t\t"
        default_re = re.compile(rf'^{re.escape(case_indent)}_:\s*$', re.MULTILINE)
        default_match = default_re.search(action_tail)
        action_block = action_tail[:default_match.start()] if default_match else action_tail
        action_re = re.compile(ACTION_CASE_RE_TEMPLATE.format(indent=re.escape(case_indent)), re.MULTILINE)
        actions = set(action_re.findall(action_block))
    actions.update(WORLD_ACTIONS)
    return actions


def summarize_source(work: dict[str, Any]) -> dict[str, Any]:
    local_path = ROOT / str(work.get("local_path", ""))
    raw_text = read_text(local_path)
    body = strip_gutenberg_boilerplate(raw_text)
    groups: dict[str, Any] = {}
    all_ranked: list[dict[str, Any]] = []
    body_word_count = word_count(body)

    for group_name, motifs in MOTIF_GROUPS.items():
        group_results: list[dict[str, Any]] = []
        for motif_id, terms in motifs.items():
            count, evidence_terms = count_terms(body, terms)
            if count <= 0:
                continue
            density = round(count / max(body_word_count, 1) * 10000, 2)
            result = {
                "motif_id": motif_id,
                "score": count,
                "density_per_10k_words": density,
                "evidence_terms": evidence_terms,
            }
            group_results.append(result)
            all_ranked.append({"group": group_name, **result})
        group_results.sort(key=lambda item: (-int(item["score"]), str(item["motif_id"])))
        groups[group_name] = group_results[:5]

    all_ranked.sort(key=lambda item: (-int(item["score"]), str(item["motif_id"])))
    return {
        "source_id": str(work.get("id", "")),
        "author": str(work.get("author", "")),
        "title": str(work.get("title", "")),
        "ebook_number": int(work.get("ebook_number", 0)),
        "source_page": str(work.get("source_page", "")),
        "local_path": str(work.get("local_path", "")),
        "word_count_without_gutenberg_boilerplate": body_word_count,
        "top_motifs": all_ranked[:10],
        "motif_groups": groups,
    }


def build_motifs_payload(limit: int = 0) -> dict[str, Any]:
    sources = get_sources()
    if limit > 0:
        sources = sources[:limit]
    works = [summarize_source(work) for work in sources]
    return {
        "generated_at": dt.datetime.now(dt.UTC).isoformat(),
        "source_manifest": str(SOURCES_PATH.relative_to(ROOT)),
        "notes": [
            "Scores are deterministic keyword counts against Gutenberg text with boilerplate stripped.",
            "Evidence terms are terms and counts, not source quotations.",
        ],
        "works": works,
    }


def flatten_top_motifs(work: dict[str, Any], max_count: int) -> list[dict[str, Any]]:
    seen: set[str] = set()
    flattened: list[dict[str, Any]] = []
    for item in work.get("top_motifs", []):
        if not isinstance(item, dict):
            continue
        motif_id = str(item.get("motif_id", ""))
        if motif_id == "" or motif_id in seen:
            continue
        seen.add(motif_id)
        flattened.append(item)
        if len(flattened) >= max_count:
            break
    return flattened


def affinity_values(motif_id: str, table: dict[str, list[str]], fallback: list[str]) -> list[str]:
    return table.get(motif_id, fallback)[:3]


def build_seed(work: dict[str, Any], motif: dict[str, Any], index: int, available_rooms: list[str]) -> dict[str, Any]:
    motif_id = str(motif.get("motif_id", ""))
    transform = TRANSFORM_LINES.get(motif_id, {
        "seed": "A public-domain expedition motif becomes a body-system encounter that offers safety with a visible cost.",
        "mechanic": "Make the choice affect at least one pressure axis, then let repeated use teach the organism.",
    })
    room_fallback = available_rooms[:3] if available_rooms else ["red_corridor"]
    return {
        "id": "%s_%02d_%s" % (str(work.get("source_id", "source")), index + 1, motif_id),
        "source_id": str(work.get("source_id", "")),
        "source_title": str(work.get("title", "")),
        "source_author": str(work.get("author", "")),
        "motif_id": motif_id,
        "motif_group": str(motif.get("group", "")),
        "source_signal": {
            "score": int(motif.get("score", 0)),
            "density_per_10k_words": float(motif.get("density_per_10k_words", 0.0)),
            "evidence_terms": motif.get("evidence_terms", []),
        },
        "fleshpunk_seed": transform["seed"],
        "mechanic_direction": transform["mechanic"],
        "suggested_rooms": affinity_values(motif_id, ROOM_AFFINITY, room_fallback),
        "suggested_existing_actions": affinity_values(motif_id, ACTION_AFFINITY, ["proceed", "retreat", "study_pool"]),
        "generation_guardrails": [
            "Transform structure and pressure, not names or prose.",
            "Keep Hymn's narration first-person and clipped.",
            "Do not reveal clone truth.",
            "State mechanical pressure changes in result text.",
        ],
    }


def build_seeds_payload(motifs_payload: dict[str, Any], max_per_work: int) -> dict[str, Any]:
    available_rooms = get_room_ids()
    seeds: list[dict[str, Any]] = []
    for work in motifs_payload.get("works", []):
        if not isinstance(work, dict):
            continue
        for index, motif in enumerate(flatten_top_motifs(work, max_per_work)):
            seeds.append(build_seed(work, motif, index, available_rooms))
    return {
        "generated_at": dt.datetime.now(dt.UTC).isoformat(),
        "motifs_source": str(MOTIFS_PATH.relative_to(ROOT)),
        "notes": [
            "Seeds are original Fleshpunk transformations derived from motif counts.",
            "Use suggested_existing_actions unless planning engine work.",
        ],
        "seeds": seeds,
    }


def normalize_excerpt(text: str, max_words: int = 45) -> str:
    words = WORD_RE.findall(" ".join(text.split()))
    return " ".join(words[:max_words])


def line_windows(lines: list[str], size: int, step: int) -> list[tuple[int, int, str]]:
    windows: list[tuple[int, int, str]] = []
    if not lines:
        return windows
    for start in range(0, len(lines), max(step, 1)):
        end = min(start + size, len(lines))
        text = "\n".join(lines[start:end])
        if text.strip():
            windows.append((start + 1, end, text))
        if end >= len(lines):
            break
    return windows


def profile_window_score(text: str, terms: list[str]) -> tuple[int, list[str]]:
    lower = text.lower()
    matched: list[str] = []
    score = 0
    for term in terms:
        pattern = r"(?<![a-z])%s(?![a-z])" % re.escape(term.lower())
        count = len(re.findall(pattern, lower))
        if count > 0:
            matched.append(term)
            score += count
    if len(matched) >= 3:
        score += len(matched)
    return score, matched


def build_nightmare_fragment(work: dict[str, Any], profile: dict[str, Any], hit: dict[str, Any], index: int) -> dict[str, Any]:
    source_id = str(work.get("id", "source"))
    profile_id = str(profile.get("id", "fragment"))
    return {
        "id": "%s_%s_%02d" % (source_id, profile_id, index + 1),
        "source_id": source_id,
        "source_title": str(work.get("title", "")),
        "source_author": str(work.get("author", "")),
        "local_path": str(work.get("local_path", "")),
        "line_start": int(hit.get("line_start", 0)),
        "line_end": int(hit.get("line_end", 0)),
        "match_score": int(hit.get("score", 0)),
        "matched_terms": hit.get("matched_terms", []),
        "source_excerpt": str(hit.get("excerpt", "")),
        "source_circumstance": str(profile.get("source_circumstance", "")),
        "nightmare_room_seed": str(profile.get("room_seed", "")),
        "escalation_thread": profile.get("escalation_thread", []),
        "ship_state_hooks": profile.get("ship_state_hooks", []),
        "suggested_actions": profile.get("suggested_actions", []),
        "generation_rules": [
            "Begin from this source circumstance, not from a new abstract anomaly.",
            "Recontextualize the procedure, evidence, and escalation into Nightmare Voyage.",
            "Do not copy source names, characters, or prose into player-facing text.",
            "Follow-ups should advance the escalation_thread or end the branch with a concrete cost.",
        ],
    }


def build_nightmare_fragments_payload(max_per_profile: int = 3, window_lines: int = 18, step_lines: int = 6) -> dict[str, Any]:
    works = {str(work.get("id", "")): work for work in get_sources()}
    fragments: list[dict[str, Any]] = []
    profile_summaries: list[dict[str, Any]] = []
    for profile in NIGHTMARE_FRAGMENT_PROFILES:
        profile_id = str(profile.get("id", ""))
        source_ids = [str(source_id) for source_id in profile.get("source_ids", [])]
        terms = [str(term) for term in profile.get("search_terms", [])]
        hits: list[dict[str, Any]] = []
        for source_id in source_ids:
            work = works.get(source_id)
            if not work:
                continue
            local_path = ROOT / str(work.get("local_path", ""))
            raw_text = read_text(local_path)
            body = strip_gutenberg_boilerplate(raw_text)
            lines = body.splitlines()
            for line_start, line_end, text in line_windows(lines, window_lines, step_lines):
                score, matched_terms = profile_window_score(text, terms)
                if score < 4 or len(matched_terms) < 2:
                    continue
                hits.append({
                    "work": work,
                    "line_start": line_start,
                    "line_end": line_end,
                    "score": score,
                    "matched_terms": matched_terms,
                    "excerpt": normalize_excerpt(text),
                })
        hits.sort(key=lambda item: (-int(item["score"]), str(item["work"].get("id", "")), int(item["line_start"])))
        selected = hits[:max(max_per_profile, 1)]
        profile_summaries.append({
            "profile_id": profile_id,
            "source_ids": source_ids,
            "hits_found": len(hits),
            "selected": len(selected),
            "source_circumstance": str(profile.get("source_circumstance", "")),
            "nightmare_room_seed": str(profile.get("room_seed", "")),
        })
        for index, hit in enumerate(selected):
            fragments.append(build_nightmare_fragment(hit["work"], profile, hit, index))

    return {
        "generated_at": dt.datetime.now(dt.UTC).isoformat(),
        "source_manifest": str(SOURCES_PATH.relative_to(ROOT)),
        "method": {
            "window_lines": window_lines,
            "step_lines": step_lines,
            "max_per_profile": max_per_profile,
            "profiles": len(NIGHTMARE_FRAGMENT_PROFILES),
            "notes": [
                "Fragments are deterministic retrieval hits plus original transformation notes.",
                "source_excerpt is for internal provenance only; do not copy it into game prose.",
                "Room generation should choose one fragment as the premise and one fragment as a complication or follow-up pressure.",
            ],
        },
        "profile_summaries": profile_summaries,
        "fragments": fragments,
    }


def validate_nightmare_fragments(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    fragments = payload.get("fragments", [])
    if not isinstance(fragments, list) or not fragments:
        errors.append("nightmare fragment payload must contain a non-empty fragments array")
        return errors
    known_actions = existing_actions()
    for index, fragment in enumerate(fragments):
        if not isinstance(fragment, dict):
            errors.append("fragments[%d] must be an object" % index)
            continue
        for key in ("id", "source_id", "source_title", "line_start", "line_end", "source_circumstance", "nightmare_room_seed", "escalation_thread", "ship_state_hooks", "suggested_actions"):
            if key not in fragment:
                errors.append("fragments[%d] missing %s" % (index, key))
        if int(fragment.get("line_start", 0)) <= 0 or int(fragment.get("line_end", 0)) < int(fragment.get("line_start", 0)):
            errors.append("fragments[%d] has invalid line span" % index)
        for action_id in fragment.get("suggested_actions", []):
            action_family = str(action_id).split(":", 1)[0]
            if action_family not in known_actions:
                errors.append("fragments[%d] suggests unhandled action %s" % (index, action_id))
    return errors


def _slug_part(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return normalized or "item"


def build_index_artifact(work: dict[str, Any], profile: dict[str, Any], hit: dict[str, Any]) -> dict[str, Any]:
    source_id = str(work.get("id", "source"))
    profile_id = str(profile.get("id", "need"))
    line_start = int(hit.get("line_start", 0))
    line_end = int(hit.get("line_end", 0))
    return {
        "id": "%s_%s_%05d_%05d" % (_slug_part(source_id), _slug_part(profile_id), line_start, line_end),
        "need_id": profile_id,
        "role": str(profile.get("role", "artifact")),
        "source_id": source_id,
        "source_title": str(work.get("title", "")),
        "source_author": str(work.get("author", "")),
        "local_path": str(work.get("local_path", "")),
        "line_start": line_start,
        "line_end": line_end,
        "match_score": int(hit.get("score", 0)),
        "matched_terms": hit.get("matched_terms", []),
        "source_excerpt": str(hit.get("excerpt", "")),
        "room_need": str(profile.get("room_need", "")),
        "nightmare_use": str(profile.get("nightmare_use", "")),
        "suggested_actions": profile.get("suggested_actions", []),
        "state_hooks": profile.get("state_hooks", []),
    }


def _coverage_status(hit_count: int, source_count: int, gap_sensitive: bool) -> str:
    if hit_count <= 0:
        return "gap"
    if gap_sensitive and source_count < 2:
        return "gap"
    if hit_count < 6 or source_count < 2:
        return "thin"
    return "covered"


def build_nightmare_index_payload(
    max_hits_per_need_per_work: int = 4,
    window_lines: int = 24,
    step_lines: int = 12,
    min_score: int = 4,
) -> dict[str, Any]:
    works = get_sources()
    artifacts: list[dict[str, Any]] = []
    profile_summaries: list[dict[str, Any]] = []
    work_summaries: list[dict[str, Any]] = []
    artifacts_by_need: dict[str, list[str]] = {}
    artifacts_by_source: dict[str, list[str]] = {}
    coverage_gaps: list[dict[str, Any]] = []

    for work in works:
        source_id = str(work.get("id", ""))
        local_path = ROOT / str(work.get("local_path", ""))
        body = strip_gutenberg_boilerplate(read_text(local_path))
        lines = body.splitlines()
        work_summary = {
            "source_id": source_id,
            "source_title": str(work.get("title", "")),
            "source_author": str(work.get("author", "")),
            "local_path": str(work.get("local_path", "")),
            "word_count_without_gutenberg_boilerplate": word_count(body),
            "need_hit_counts": {},
        }
        for profile in NIGHTMARE_INDEX_PROFILES:
            profile_id = str(profile.get("id", ""))
            terms = [str(term) for term in profile.get("terms", [])]
            hits: list[dict[str, Any]] = []
            for line_start, line_end, text in line_windows(lines, window_lines, step_lines):
                score, matched_terms = profile_window_score(text, terms)
                if score < min_score or len(matched_terms) < 2:
                    continue
                hits.append({
                    "line_start": line_start,
                    "line_end": line_end,
                    "score": score,
                    "matched_terms": matched_terms,
                    "excerpt": normalize_excerpt(text, max_words=60),
                })
            hits.sort(key=lambda item: (-int(item["score"]), int(item["line_start"])))
            selected = hits[:max(max_hits_per_need_per_work, 1)]
            if selected:
                work_summary["need_hit_counts"][profile_id] = len(selected)
            for hit in selected:
                artifact = build_index_artifact(work, profile, hit)
                artifacts.append(artifact)
                artifacts_by_need.setdefault(profile_id, []).append(str(artifact["id"]))
                artifacts_by_source.setdefault(source_id, []).append(str(artifact["id"]))
        work_summaries.append(work_summary)

    for profile in NIGHTMARE_INDEX_PROFILES:
        profile_id = str(profile.get("id", ""))
        profile_artifacts = [artifact for artifact in artifacts if artifact.get("need_id") == profile_id]
        source_ids = sorted({str(artifact.get("source_id", "")) for artifact in profile_artifacts if artifact.get("source_id")})
        hit_count = len(profile_artifacts)
        source_count = len(source_ids)
        status = _coverage_status(hit_count, source_count, bool(profile.get("gap_sensitive", False)))
        summary = {
            "need_id": profile_id,
            "role": str(profile.get("role", "")),
            "room_need": str(profile.get("room_need", "")),
            "coverage_status": status,
            "artifact_count": hit_count,
            "source_count": source_count,
            "sources": source_ids,
            "suggested_actions": profile.get("suggested_actions", []),
            "state_hooks": profile.get("state_hooks", []),
        }
        profile_summaries.append(summary)
        if status != "covered":
            if bool(profile.get("gap_sensitive", False)):
                gap_note = "Project-specific design must supply this directly, then attach corpus artifacts for procedure, evidence, or consequence."
            elif status == "gap":
                gap_note = "No strong indexed coverage; supply this from project design or combine adjacent corpus needs."
            else:
                gap_note = "Coverage is thin; use cautiously and combine with a stronger artifact from another need."
            coverage_gaps.append({
                **summary,
                "gap_note": gap_note,
            })

    artifacts.sort(key=lambda item: (str(item.get("need_id", "")), -int(item.get("match_score", 0)), str(item.get("source_id", "")), int(item.get("line_start", 0))))
    return {
        "generated_at": dt.datetime.now(dt.UTC).isoformat(),
        "source_manifest": str(SOURCES_PATH.relative_to(ROOT)),
        "method": {
            "window_lines": window_lines,
            "step_lines": step_lines,
            "min_score": min_score,
            "max_hits_per_need_per_work": max_hits_per_need_per_work,
            "profiles": len(NIGHTMARE_INDEX_PROFILES),
            "works_scanned": len(works),
            "notes": [
                "This is a deterministic lookup index over all local corpus texts.",
                "source_excerpt is internal provenance; do not copy it into game prose.",
                "Room generation may combine multiple artifacts from the same or different sources.",
            ],
        },
        "composition_rules": [
            "Pick one premise artifact, one procedure or evidence artifact, and one consequence/followup artifact when the room needs a long branch.",
            "Short branches may use one artifact and end with a concrete cost: stores, stress, pressure, route uncertainty, contamination, or officer trust.",
            "If a needed project concept is listed as a gap, write that concept from Nightmare Voyage lore and use corpus artifacts only for incident structure.",
            "Followups may source the same artifact's role or switch to another artifact if the state hook connects cleanly.",
        ],
        "profiles": [
            {
                "need_id": str(profile.get("id", "")),
                "role": str(profile.get("role", "")),
                "terms": profile.get("terms", []),
                "room_need": str(profile.get("room_need", "")),
                "nightmare_use": str(profile.get("nightmare_use", "")),
                "suggested_actions": profile.get("suggested_actions", []),
                "state_hooks": profile.get("state_hooks", []),
                "gap_sensitive": bool(profile.get("gap_sensitive", False)),
            }
            for profile in NIGHTMARE_INDEX_PROFILES
        ],
        "profile_summaries": profile_summaries,
        "coverage_gaps": coverage_gaps,
        "work_summaries": work_summaries,
        "lookup": {
            "artifacts_by_need": artifacts_by_need,
            "artifacts_by_source": artifacts_by_source,
        },
        "artifacts": artifacts,
    }


def validate_nightmare_index(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    artifacts = payload.get("artifacts", [])
    profiles = payload.get("profiles", [])
    if not isinstance(profiles, list) or not profiles:
        errors.append("corpus index payload must contain a non-empty profiles array")
    if not isinstance(artifacts, list) or not artifacts:
        errors.append("corpus index payload must contain a non-empty artifacts array")
        return errors
    profile_ids = {str(profile.get("need_id", "")) for profile in profiles if isinstance(profile, dict)}
    known_actions = existing_actions()
    for index, artifact in enumerate(artifacts):
        if not isinstance(artifact, dict):
            errors.append("artifacts[%d] must be an object" % index)
            continue
        for key in ("id", "need_id", "role", "source_id", "source_title", "line_start", "line_end", "room_need", "nightmare_use", "suggested_actions", "state_hooks"):
            if key not in artifact:
                errors.append("artifacts[%d] missing %s" % (index, key))
        if profile_ids and str(artifact.get("need_id", "")) not in profile_ids:
            errors.append("artifacts[%d] references unknown need_id %s" % (index, artifact.get("need_id", "")))
        if int(artifact.get("line_start", 0)) <= 0 or int(artifact.get("line_end", 0)) < int(artifact.get("line_start", 0)):
            errors.append("artifacts[%d] has invalid line span" % index)
        for action_id in artifact.get("suggested_actions", []):
            action_family = str(action_id).split(":", 1)[0]
            if action_family not in known_actions:
                errors.append("artifacts[%d] suggests unhandled action %s" % (index, action_id))
    return errors


def validate_motifs(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    works = payload.get("works", [])
    if not isinstance(works, list) or not works:
        errors.append("motifs payload must contain a non-empty works array")
        return errors
    for index, work in enumerate(works):
        if not isinstance(work, dict):
            errors.append("works[%d] must be an object" % index)
            continue
        for key in ("source_id", "title", "author", "local_path", "top_motifs", "motif_groups"):
            if key not in work:
                errors.append("works[%d] missing %s" % (index, key))
        if int(work.get("word_count_without_gutenberg_boilerplate", 0)) <= 0:
            errors.append("works[%d] has no body words" % index)
    return errors


def validate_seeds(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    known_rooms = set(get_room_ids())
    known_actions = existing_actions()
    seeds = payload.get("seeds", [])
    if not isinstance(seeds, list) or not seeds:
        errors.append("seeds payload must contain a non-empty seeds array")
        return errors
    for index, seed in enumerate(seeds):
        if not isinstance(seed, dict):
            errors.append("seeds[%d] must be an object" % index)
            continue
        for key in ("id", "source_id", "motif_id", "fleshpunk_seed", "mechanic_direction", "suggested_rooms", "suggested_existing_actions"):
            if key not in seed:
                errors.append("seeds[%d] missing %s" % (index, key))
        if not isinstance(seed.get("suggested_rooms", []), list) or not seed.get("suggested_rooms", []):
            errors.append("seeds[%d] needs at least one suggested room" % index)
        else:
            for room_id in seed.get("suggested_rooms", []):
                if str(room_id) not in known_rooms:
                    errors.append("seeds[%d] suggests unknown room %s" % (index, room_id))
        if not isinstance(seed.get("suggested_existing_actions", []), list) or not seed.get("suggested_existing_actions", []):
            errors.append("seeds[%d] needs at least one suggested action" % index)
        else:
            for action_id in seed.get("suggested_existing_actions", []):
                action_family = str(action_id).split(":", 1)[0]
                if action_family not in known_actions:
                    errors.append("seeds[%d] suggests unhandled action %s" % (index, action_id))
    return errors


def cmd_context(_: argparse.Namespace) -> int:
    sources = get_sources()
    existing_texts = 0
    total_bytes = 0
    for work in sources:
        path = ROOT / str(work.get("local_path", ""))
        if path.exists():
            existing_texts += 1
            total_bytes += path.stat().st_size
    print("Corpus context")
    print("--------------")
    print(f"Sources: {len(sources)}")
    print(f"Local texts: {existing_texts}")
    print(f"Bytes: {total_bytes}")
    print(f"Manifest: {SOURCES_PATH.relative_to(ROOT)}")
    print(f"Motifs output: {MOTIFS_PATH.relative_to(ROOT)}")
    print(f"Seeds output: {SEEDS_PATH.relative_to(ROOT)}")
    print("\nWorks")
    for work in sources:
        print("- %s, %s (#%s)" % (work.get("author", ""), work.get("title", ""), work.get("ebook_number", "")))
    return 0


def cmd_extract(args: argparse.Namespace) -> int:
    payload = build_motifs_payload(args.limit)
    errors = validate_motifs(payload)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    out_path = Path(args.out) if args.out else MOTIFS_PATH
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    write_json(out_path, payload)
    print("wrote %s" % out_path.relative_to(ROOT))
    print("works=%d" % len(payload.get("works", [])))
    return 0


def cmd_transform(args: argparse.Namespace) -> int:
    motifs_path = Path(args.motifs) if args.motifs else MOTIFS_PATH
    if not motifs_path.is_absolute():
        motifs_path = ROOT / motifs_path
    if not motifs_path.exists():
        payload = build_motifs_payload(0)
        write_json(motifs_path, payload)
    motifs_payload = load_json(motifs_path)
    motif_errors = validate_motifs(motifs_payload)
    if motif_errors:
        for error in motif_errors:
            print(error, file=sys.stderr)
        return 1
    seeds_payload = build_seeds_payload(motifs_payload, max(args.max_per_work, 1))
    seed_errors = validate_seeds(seeds_payload)
    if seed_errors:
        for error in seed_errors:
            print(error, file=sys.stderr)
        return 1
    out_path = Path(args.out) if args.out else SEEDS_PATH
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    write_json(out_path, seeds_payload)
    print("wrote %s" % out_path.relative_to(ROOT))
    print("seeds=%d" % len(seeds_payload.get("seeds", [])))
    return 0


def cmd_nightmare_fragments(args: argparse.Namespace) -> int:
    payload = build_nightmare_fragments_payload(
        max_per_profile=max(args.max_per_profile, 1),
        window_lines=max(args.window_lines, 6),
        step_lines=max(args.step_lines, 1),
    )
    errors = validate_nightmare_fragments(payload)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    out_path = Path(args.out) if args.out else NIGHTMARE_FRAGMENTS_PATH
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    write_json(out_path, payload)
    print("wrote %s" % out_path.relative_to(ROOT))
    print("fragments=%d" % len(payload.get("fragments", [])))
    return 0


def cmd_nightmare_context(args: argparse.Namespace) -> int:
    target = Path(args.path) if args.path else NIGHTMARE_FRAGMENTS_PATH
    if not target.is_absolute():
        target = ROOT / target
    if not target.exists():
        payload = build_nightmare_fragments_payload(max_per_profile=1)
    else:
        payload = load_json(target)
    errors = validate_nightmare_fragments(payload)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    fragments = payload.get("fragments", [])
    print("Nightmare Voyage corpus fragments")
    print("----------------------------------")
    print("Path: %s" % target.relative_to(ROOT))
    print("Fragments: %d" % len(fragments))
    print("Rule: room ideas start from a source circumstance, then recontextualize procedure, evidence, escalation, and cost.")
    print("")
    for fragment in fragments[:max(args.limit, 1)]:
        print("- %s" % fragment.get("id", "fragment"))
        print("  Source: %s, %s" % (fragment.get("source_author", ""), fragment.get("source_title", "")))
        print("  Lines: %s-%s" % (fragment.get("line_start", ""), fragment.get("line_end", "")))
        print("  Source circumstance: %s" % fragment.get("source_circumstance", ""))
        print("  Nightmare seed: %s" % fragment.get("nightmare_room_seed", ""))
        print("  Escalation: %s" % " -> ".join(str(step) for step in fragment.get("escalation_thread", [])))
        print("  Hooks: %s" % ", ".join(str(hook) for hook in fragment.get("ship_state_hooks", [])))
    return 0


def cmd_nightmare_index(args: argparse.Namespace) -> int:
    payload = build_nightmare_index_payload(
        max_hits_per_need_per_work=max(args.max_hits_per_need_per_work, 1),
        window_lines=max(args.window_lines, 6),
        step_lines=max(args.step_lines, 1),
        min_score=max(args.min_score, 1),
    )
    errors = validate_nightmare_index(payload)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    out_path = Path(args.out) if args.out else NIGHTMARE_INDEX_PATH
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    write_json(out_path, payload)
    print("wrote %s" % out_path.relative_to(ROOT))
    print("artifacts=%d" % len(payload.get("artifacts", [])))
    print("gaps=%d" % len(payload.get("coverage_gaps", [])))
    return 0


def _load_or_build_index(path: Path) -> dict[str, Any]:
    if path.exists():
        return load_json(path)
    return build_nightmare_index_payload()


def cmd_nightmare_index_context(args: argparse.Namespace) -> int:
    target = Path(args.path) if args.path else NIGHTMARE_INDEX_PATH
    if not target.is_absolute():
        target = ROOT / target
    payload = _load_or_build_index(target)
    errors = validate_nightmare_index(payload)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    need_filter = str(args.need or "").strip()
    source_filter = str(args.source or "").strip()
    role_filter = str(args.role or "").strip()
    artifacts = [artifact for artifact in payload.get("artifacts", []) if isinstance(artifact, dict)]
    if need_filter:
        artifacts = [artifact for artifact in artifacts if str(artifact.get("need_id", "")) == need_filter]
    if source_filter:
        artifacts = [artifact for artifact in artifacts if str(artifact.get("source_id", "")) == source_filter]
    if role_filter:
        artifacts = [artifact for artifact in artifacts if str(artifact.get("role", "")) == role_filter]

    print("Nightmare Voyage corpus index")
    print("------------------------------")
    print("Path: %s" % target.relative_to(ROOT))
    print("Artifacts: %d" % len(payload.get("artifacts", [])))
    print("Profiles: %d" % len(payload.get("profiles", [])))
    print("Coverage gaps: %d" % len(payload.get("coverage_gaps", [])))
    print("Rule: use indexed artifacts as lookup anchors; combine premise, procedure/evidence, and consequence artifacts for longer branches.")
    print("")

    if args.gaps:
        print("Coverage gaps")
        for gap in payload.get("coverage_gaps", []):
            print("- %s [%s]: %s" % (gap.get("need_id", ""), gap.get("coverage_status", ""), gap.get("room_need", "")))
            print("  Note: %s" % gap.get("gap_note", ""))
        return 0

    for artifact in artifacts[:max(args.limit, 1)]:
        print("- %s" % artifact.get("id", "artifact"))
        print("  Need: %s / %s" % (artifact.get("need_id", ""), artifact.get("role", "")))
        print("  Source: %s, %s" % (artifact.get("source_author", ""), artifact.get("source_title", "")))
        print("  Lines: %s-%s" % (artifact.get("line_start", ""), artifact.get("line_end", "")))
        print("  Use: %s" % artifact.get("nightmare_use", ""))
        print("  Hooks: %s" % ", ".join(str(hook) for hook in artifact.get("state_hooks", [])))
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    target = Path(args.path)
    if not target.is_absolute():
        target = ROOT / target
    payload = load_json(target)
    if "artifacts" in payload and "profiles" in payload:
        errors = validate_nightmare_index(payload)
    elif "fragments" in payload:
        errors = validate_nightmare_fragments(payload)
    else:
        errors = validate_seeds(payload) if "seeds" in payload else validate_motifs(payload)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("ok: %s" % target.relative_to(ROOT))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    context = sub.add_parser("context", help="Print corpus source context.")
    context.set_defaults(func=cmd_context)

    extract = sub.add_parser("extract", help="Extract deterministic motif counts from source texts.")
    extract.add_argument("--limit", type=int, default=0, help="Limit number of works processed.")
    extract.add_argument("--out", help="Output motifs JSON path.")
    extract.set_defaults(func=cmd_extract)

    transform = sub.add_parser("transform", help="Transform motifs into Fleshpunk design seeds.")
    transform.add_argument("--motifs", help="Input motifs JSON path. Defaults to generated/corpus/motifs.json.")
    transform.add_argument("--max-per-work", type=int, default=4, help="Maximum seeds to produce per source work.")
    transform.add_argument("--out", help="Output seeds JSON path.")
    transform.set_defaults(func=cmd_transform)

    nightmare_fragments = sub.add_parser("nightmare-fragments", help="Extract Nightmare Voyage room fragments from source incidents.")
    nightmare_fragments.add_argument("--max-per-profile", type=int, default=3, help="Maximum source hits selected for each fragment profile.")
    nightmare_fragments.add_argument("--window-lines", type=int, default=18, help="Source line window size for retrieval.")
    nightmare_fragments.add_argument("--step-lines", type=int, default=6, help="Line step between source windows.")
    nightmare_fragments.add_argument("--out", help="Output fragment JSON path.")
    nightmare_fragments.set_defaults(func=cmd_nightmare_fragments)

    nightmare_context = sub.add_parser("nightmare-context", help="Print selected Nightmare Voyage corpus fragment context.")
    nightmare_context.add_argument("--path", help="Fragment JSON path. Defaults to generated/corpus/nightmare_voyage_fragments.json.")
    nightmare_context.add_argument("--limit", type=int, default=12, help="Number of fragments to print.")
    nightmare_context.set_defaults(func=cmd_nightmare_context)

    nightmare_index = sub.add_parser("nightmare-index", help="Build a reusable Nightmare Voyage lookup index over all corpus texts.")
    nightmare_index.add_argument("--max-hits-per-need-per-work", type=int, default=4, help="Maximum source windows kept per need per work.")
    nightmare_index.add_argument("--window-lines", type=int, default=24, help="Source line window size for index retrieval.")
    nightmare_index.add_argument("--step-lines", type=int, default=12, help="Line step between indexed source windows.")
    nightmare_index.add_argument("--min-score", type=int, default=4, help="Minimum keyword score for an indexed artifact.")
    nightmare_index.add_argument("--out", help="Output corpus index JSON path.")
    nightmare_index.set_defaults(func=cmd_nightmare_index)

    nightmare_index_context = sub.add_parser("nightmare-index-context", help="Print lookup context from the Nightmare Voyage corpus index.")
    nightmare_index_context.add_argument("--path", help="Index JSON path. Defaults to generated/corpus/nightmare_voyage_corpus_index.json.")
    nightmare_index_context.add_argument("--need", help="Filter to a corpus need id.")
    nightmare_index_context.add_argument("--source", help="Filter to a corpus source id.")
    nightmare_index_context.add_argument("--role", help="Filter to an artifact role.")
    nightmare_index_context.add_argument("--limit", type=int, default=12, help="Number of artifacts to print.")
    nightmare_index_context.add_argument("--gaps", action="store_true", help="Print coverage gaps instead of artifacts.")
    nightmare_index_context.set_defaults(func=cmd_nightmare_index_context)

    validate = sub.add_parser("validate", help="Validate motifs or seeds JSON.")
    validate.add_argument("path")
    validate.set_defaults(func=cmd_validate)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130
    except json.JSONDecodeError as exc:
        print(textwrap.fill(f"JSON error: {exc}", width=88), file=sys.stderr)
        return 1
    except OSError as exc:
        print(textwrap.fill(f"file error: {exc}", width=88), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
