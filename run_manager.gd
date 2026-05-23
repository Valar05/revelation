extends Node

const ROOMS_PATH := "res://room_dialogue.json"
const EVENTS_PATH := "res://events.json"
const DECKS_PATH := "res://encounter_decks.json"
const POST_UPDATE_ROOMS_PATH := "res://rooms_post_update.json"
const POST_UPDATE_EVENTS_PATH := "res://events_post_update.json"
const POST_UPDATE_DECKS_PATH := "res://encounter_decks_post_update.json"
const ENEMIES_PATH := "res://enemies.json"
const MUTATIONS_PATH := "res://mutations.json"
const SYMBIOTES_PATH := "res://symbiotes.json"
const ARTIFACTS_PATH := "res://artifacts.json"
const HEART_MANAGER_PATH := "/root/HeartManager"
const REVELATION_PRESSURE_DEFAULTS := {
	"institute_scrutiny": 0,
	"squad_cohesion": 5,
	"public_exposure": 0,
	"symbolic_contamination": 0,
	"artifact_burden": 0,
	"doctrine_fracture": 0,
	"casualty_strain": 0,
	"closure_debt": 0
}
const REVELATION_PRESSURE_LABELS := {
	"institute_scrutiny": "Institute scrutiny",
	"squad_cohesion": "Squad cohesion",
	"public_exposure": "Public exposure",
	"symbolic_contamination": "Symbolic contamination",
	"artifact_burden": "Artifact burden",
	"doctrine_fracture": "Doctrine fracture",
	"casualty_strain": "Casualty strain",
	"closure_debt": "Closure debt"
}

signal run_started
signal encounter_changed(encounter: Dictionary)

var rooms_by_id: Dictionary = {}
var room_events_by_room: Dictionary = {}
var special_events: Dictionary = {}
var deck_config: Dictionary = {}
var content_track := "legacy"
var enemies_by_id: Dictionary = {}
var mutations_by_id: Dictionary = {}
var symbiotes_by_id: Dictionary = {}
var artifacts_by_id: Dictionary = {}

var current_encounter: Dictionary = {}
var current_room_id := ""
var active_deck_cards: Array[Dictionary] = []
var active_deck_room_ids: Array[String] = []
var base_deck_room_ids: Array[String] = []
var consumed_rooms: Dictionary = {}
var consumed_room_events: Dictionary = {}
var permanently_consumed_events: Dictionary = {}
var room_visit_counts: Dictionary = {}
var rooms_cleared := 0
var biomass := 0
var corruption := 0
var danger := 0
var food := 8
var fuel := 8
var water := 8
var crew_morale := 6
var crew_unrest := 0
var merchant_refusals := 0
var merchant_claim := 0
var baffle_mutes := 0
var marked_route_streak := 0
var pressure_counts: Dictionary = {}
var revelation_pressure: Dictionary = {}
var environment_state: Dictionary = {}
var ending_pressure := ""
var owned_mutations: Array[String] = []
var owned_symbiotes: Array[String] = []
var owned_artifacts: Array[String] = []
var symbiote_health: Dictionary = {}
var symbiote_cooldowns: Dictionary = {}
var active_symbiotes: Dictionary = {}
var player_state: Dictionary = {}
var officer_state: Dictionary = {}
var department_state: Dictionary = {}
var ship_system_state: Dictionary = {}

var _merchant_triggered_at_rooms: Dictionary = {}
var _symbiote_triggered_at_rooms: Dictionary = {}
var _merchant_reckoning_triggered := false
var _corruption_spike_triggers := 0
var _danger_notice_triggers := 0
var _director_triggered_warnings: Dictionary = {}
var _pending_director_events: Array[String] = []
var _pending_story_events: Array[Dictionary] = []
var _triggered_story_events: Dictionary = {}
var _ending_locks: Dictionary = {}
var _hunter_reckoning_triggered := false
var _corruption_claim_triggered := false
var _named_ending_triggered := false
var _pending_room_id_after_transition := ""
var _pending_encounter_after_overlay: Dictionary = {}
var _last_action_result: Dictionary = {}
var _merchant_purchase_made := false
var _merchant_due_before_redraw := false
var _rng := RandomNumberGenerator.new()


func _ready() -> void:
	_rng.randomize()
	_load_all_data()


func start_new_run() -> void:
	_load_all_data()
	rooms_cleared = 0
	biomass = 0
	corruption = 0
	danger = 0
	food = 8
	fuel = 8
	water = 8
	crew_morale = 6
	crew_unrest = 0
	merchant_refusals = 0
	merchant_claim = 0
	baffle_mutes = 0
	marked_route_streak = 0
	pressure_counts.clear()
	revelation_pressure = _build_revelation_pressure_defaults()
	environment_state.clear()
	ending_pressure = ""
	owned_mutations.clear()
	owned_symbiotes.clear()
	owned_artifacts.clear()
	symbiote_health.clear()
	symbiote_cooldowns.clear()
	active_symbiotes.clear()
	active_deck_cards.clear()
	consumed_rooms.clear()
	consumed_room_events.clear()
	permanently_consumed_events.clear()
	room_visit_counts.clear()
	_merchant_triggered_at_rooms.clear()
	_symbiote_triggered_at_rooms.clear()
	_merchant_reckoning_triggered = false
	_corruption_spike_triggers = 0
	_danger_notice_triggers = 0
	_director_triggered_warnings.clear()
	_pending_director_events.clear()
	_pending_story_events.clear()
	_triggered_story_events.clear()
	_ending_locks.clear()
	_hunter_reckoning_triggered = false
	_corruption_claim_triggered = false
	_named_ending_triggered = false
	_pending_room_id_after_transition = ""
	_pending_encounter_after_overlay.clear()
	_last_action_result.clear()
	_merchant_purchase_made = false
	_merchant_due_before_redraw = false
	player_state = _build_base_player_state()
	_build_base_operation_state()
	base_deck_room_ids = _build_base_deck_room_ids()
	_reset_active_deck()
	current_room_id = str(deck_config.get("opening_room_id", "bridge_initial_descent"))
	current_encounter = _build_opening_encounter(current_room_id)
	_pending_room_id_after_transition = str(deck_config.get("first_room_after_opening", ""))
	var opening_event_data: Dictionary = current_encounter.get("event_data", {})
	if str(opening_event_data.get("type", "")) == "symbiote":
		_remove_symbiote_cards_from_active_deck()
	_sync_heart_rate()
	run_started.emit()
	encounter_changed.emit(get_current_encounter())


func get_current_encounter() -> Dictionary:
	return current_encounter.duplicate(true)


func get_last_action_result() -> Dictionary:
	return _last_action_result.duplicate(true)


func get_director_state() -> Dictionary:
	return {
			"pressure_counts": pressure_counts.duplicate(true),
			"revelation_pressure": revelation_pressure.duplicate(true),
			"revelation_pressure_labels": REVELATION_PRESSURE_LABELS.duplicate(true),
			"environment_state": environment_state.duplicate(true),
		"officer_state": officer_state.duplicate(true),
		"department_state": department_state.duplicate(true),
		"ship_system_state": ship_system_state.duplicate(true),
		"artifacts_by_id": artifacts_by_id.duplicate(true),
		"owned_artifacts": owned_artifacts.duplicate(true),
		"ending_pressure": ending_pressure,
		"ending_locks": _ending_locks.duplicate(true),
		"balanced_eligible": _is_balanced_eligible(),
		"merchant_claim": merchant_claim,
		"baffle_mutes": baffle_mutes,
		"marked_route_streak": marked_route_streak,
		"food": food,
		"fuel": fuel,
			"water": water,
			"crew_morale": crew_morale,
			"crew_unrest": crew_unrest
		}


func get_room_data(room_id: String) -> Dictionary:
	return rooms_by_id.get(room_id, {}).duplicate(true)


func get_player_combat_stats(fallback_stats: Dictionary = {}) -> Dictionary:
	var stats := fallback_stats.duplicate(true)
	for key in player_state.keys():
		stats[key] = player_state[key]

	var danger_multiplier := 1.0 + float(danger) * 0.5
	stats["damage"] = int(round(float(stats.get("damage", 0)) * danger_multiplier))
	_apply_owned_mutation_combat_effects(stats)
	return stats


func prepare_enemy_combat_stats(enemy_stats: Dictionary) -> Dictionary:
	var stats := enemy_stats.duplicate(true)
	if active_symbiotes.has("pheromones"):
		var symbiote_data: Dictionary = symbiotes_by_id.get("pheromones", {})
		var initiative_delta := float(symbiote_data.get("enemy_initiative_delta", -1.0))
		stats["initiative"] = clamp(float(stats.get("initiative", 0.5)) + initiative_delta, 0.0, 1.0)
		stats["speed"] = max(float(stats.get("speed", 1.0)) + initiative_delta, 0.01)
		active_symbiotes.erase("pheromones")
		_start_symbiote_cooldown("pheromones", 3)
	return stats


func activate_symbiote(symbiote_id: String) -> Dictionary:
	if symbiote_id == "" or not owned_symbiotes.has(symbiote_id) or not symbiotes_by_id.has(symbiote_id):
		return _build_symbiote_activation_result([
			"Nothing under my skin answers that shape.",
			"I keep moving."
		])
	if int(symbiote_health.get(symbiote_id, 0)) <= 0:
		return _build_symbiote_activation_result([
			"The symbiote is dead tissue now.",
			"I get no use from it."
		])
	if active_symbiotes.has(symbiote_id):
		return _build_symbiote_activation_result([
			"It's already awake.",
			"I feel it waiting under the skin."
		])

	var symbiote_data: Dictionary = symbiotes_by_id.get(symbiote_id, {})
	var symbiote_name := str(symbiote_data.get("name", symbiote_id))
	match symbiote_id:
		"impermeable_barrier":
			var armor_pool := int(symbiote_data.get("armor", 8))
			active_symbiotes[symbiote_id] = {"armor": armor_pool}
			return _with_director_lines(_build_symbiote_activation_result([
				"%s plates over me. %d armor waiting for the next hit." % [symbiote_name, armor_pool],
				"If the full layer breaks, it gets hurt."
			]), _record_action_pattern("activate_symbiote", {}))
		"pheromones":
			active_symbiotes[symbiote_id] = true
			return _with_director_lines(_build_symbiote_activation_result([
				"%s bleeds scent into the air." % symbiote_name,
				"It lasts this room. Then it needs two rooms quiet."
			]), _record_action_pattern("activate_symbiote", {}))
		"mitosis_unit":
			active_symbiotes[symbiote_id] = true
			return _with_director_lines(_build_symbiote_activation_result([
				"%s is already counting my organs." % symbiote_name,
				"If I die, it dies first."
			]), _record_action_pattern("activate_symbiote", {}))

	return _with_director_lines(_build_symbiote_activation_result([
		"%s twitches, but I don't know how to use it yet." % symbiote_name,
		"I leave it dormant."
	]), _record_action_pattern("activate_symbiote", {}))


func get_merchant_shop_offer() -> Dictionary:
	var lines: Array[String] = [
		"The merchant sets out eggs like weights on a scale.",
		"Biomass: %d. One placed mass buys one change. Withdrawal leaves him counting." % biomass
	]
	var buttons: Array[Dictionary] = []
	for mutation_id_variant in mutations_by_id.keys():
		var mutation_id := str(mutation_id_variant)
		if owned_mutations.has(mutation_id):
			continue
		var mutation_data: Dictionary = mutations_by_id.get(mutation_id, {})
		var mutation_name := str(mutation_data.get("name", mutation_id))
		var mutation_cost := _get_mutation_cost(mutation_data)
		buttons.append({
			"label": "%s - %d biomass" % [mutation_name, mutation_cost],
			"action": "buy_mutation:%s" % mutation_id,
			"voice_aliases": _build_mutation_voice_aliases(mutation_id, mutation_data)
		})

	if buttons.is_empty():
		lines.append("Nothing here wants me twice.")
	buttons.append({
		"label": "Withdraw",
		"action": "leave_merchant",
		"voice_aliases": ["withdraw", "leave", "walk away", "back off", "retreat"]
	})
	return {
		"lines": lines,
		"buttons": buttons
	}


func buy_shop_mutation(mutation_id: String) -> Dictionary:
	if mutation_id == "" or not mutations_by_id.has(mutation_id):
		return {
			"lines": [
				"The scale has no place for that shape.",
				"I keep my biomass close."
			],
			"buttons": [
				{
					"label": "Back to scales",
					"action": "browse_wares",
					"voice_aliases": ["back", "back to scales", "scales", "merchant", "trade"]
				},
				{
					"label": "Withdraw",
					"action": "leave_merchant",
					"voice_aliases": ["withdraw", "leave", "walk away", "back off", "retreat"]
				}
			]
		}

	var mutation_data: Dictionary = mutations_by_id.get(mutation_id, {})
	var mutation_name := str(mutation_data.get("name", mutation_id))
	if owned_mutations.has(mutation_id):
		return {
			"lines": [
				"%s is already written into me." % mutation_name,
				"The merchant's scale stays still."
			],
			"buttons": [
				{
					"label": "Back to scales",
					"action": "browse_wares",
					"voice_aliases": ["back", "back to scales", "scales", "merchant", "trade"]
				},
				{
					"label": "Withdraw",
					"action": "leave_merchant",
					"voice_aliases": ["withdraw", "leave", "walk away", "back off", "retreat"]
				}
			]
		}

	var mutation_cost := _get_mutation_cost(mutation_data)
	if biomass < mutation_cost:
		return {
			"lines": [
				"The scale wants %d biomass for %s." % [mutation_cost, mutation_name],
				"I only have %d." % biomass
			],
			"buttons": [
				{
					"label": "Back to scales",
					"action": "browse_wares",
					"voice_aliases": ["back", "back to scales", "scales", "merchant", "trade"]
				},
				{
					"label": "Withdraw",
					"action": "leave_merchant",
					"voice_aliases": ["withdraw", "leave", "walk away", "back off", "retreat"]
				}
			]
		}

	biomass -= mutation_cost
	owned_mutations.append(mutation_id)
	_merchant_purchase_made = true
	_add_corruption(1)
	_apply_owned_mutation_state_bounds()
	return _with_director_lines({
		"lines": [
			"I feed the scale. The egg lunges before I finish stepping back.",
			"It bursts across my legs and crawls inward.",
			"%s settles into me. Biomass: %d. Corruption: %d." % [mutation_name, biomass, corruption]
		],
		"buttons": [
			{
				"label": "Back to scales",
				"action": "browse_wares",
				"voice_aliases": ["back", "back to scales", "scales", "merchant", "trade"]
			},
			{
				"label": "Withdraw",
				"action": "leave_merchant",
				"voice_aliases": ["withdraw", "leave", "walk away", "back off", "retreat"]
			}
		]
	}, _record_action_pattern("buy_mutation", {}))


func consume_current_event(action_id: String = "") -> void:
	if current_encounter.is_empty() or bool(current_encounter.get("consumed", false)):
		return

	var result_snapshot_before := _build_result_snapshot()
	var room_id := str(current_encounter.get("room_id", ""))
	var event_id := str(current_encounter.get("event_id", ""))
	var event_data: Dictionary = current_encounter.get("event_data", {})

	if room_id != "" and event_id != "":
		if not consumed_room_events.has(room_id):
			consumed_room_events[room_id] = {}
		consumed_room_events[room_id][event_id] = true

		if not bool(event_data.get("reactivate_on_reshuffle", true)):
			permanently_consumed_events[event_id] = true

	_last_action_result = _apply_action_effects(action_id, event_data)
	if action_id.begins_with("debrief_choice:") or action_id.begins_with("use_artifact:"):
		_last_action_result = _apply_structured_action_effects(action_id, event_data, _last_action_result, _last_action_result)
	_last_action_result = _apply_event_action_result(action_id, event_data, _last_action_result)
	_apply_event_memory_flags(event_data)
	_last_action_result = _with_director_lines(_last_action_result, _enqueue_story_followup(action_id, event_data, _last_action_result))
	_last_action_result = _with_director_lines(_last_action_result, _record_action_pattern(action_id, event_data))
	_last_action_result = _with_result_delta_lines(_last_action_result, result_snapshot_before)
	_last_action_result["_tts_event_id"] = event_id
	_last_action_result["_tts_action_id"] = action_id
	_last_action_result["_tts_room_id"] = room_id
	current_encounter["consumed"] = true


func advance_to_next_encounter() -> Dictionary:
	if not current_encounter.is_empty() and bool(current_encounter.get("counts_as_room", false)):
		rooms_cleared += 1
		_advance_symbiote_room_state()

	var next_encounter := _build_next_encounter()
	current_encounter = next_encounter
	current_room_id = str(next_encounter.get("room_id", current_room_id))
	encounter_changed.emit(get_current_encounter())
	return get_current_encounter()


func apply_combat_result(combat_result: Dictionary, enemy_data: Dictionary) -> Dictionary:
	var adjusted_result := combat_result.duplicate(true)
	if int(adjusted_result.get("player_remaining_health", player_state.get("health", 0))) <= 0 and _can_mitosis_trigger():
		_kill_symbiote("mitosis_unit")
		adjusted_result["player_remaining_health"] = 1
		adjusted_result["enemy_won"] = false
		adjusted_result["mitosis_triggered"] = true

	player_state["health"] = int(max(int(adjusted_result.get("player_remaining_health", player_state.get("health", 0))), 0))
	player_state["shield"] = int(max(int(adjusted_result.get("player_remaining_shield", player_state.get("shield", 0))), 0))
	if bool(adjusted_result.get("player_won", false)):
		biomass += int(enemy_data.get("biomass_reward", 0))
	return adjusted_result


func get_danger_bpm() -> float:
	return float(deck_config.get("base_bpm", 20.0)) + float(danger) * float(deck_config.get("danger_bpm_step", 5.0))


func _load_all_data() -> void:
	var rooms_path := POST_UPDATE_ROOMS_PATH if FileAccess.file_exists(POST_UPDATE_ROOMS_PATH) else ROOMS_PATH
	var events_path := POST_UPDATE_EVENTS_PATH if FileAccess.file_exists(POST_UPDATE_EVENTS_PATH) else EVENTS_PATH
	var decks_path := POST_UPDATE_DECKS_PATH if FileAccess.file_exists(POST_UPDATE_DECKS_PATH) else DECKS_PATH
	var rooms_payload := _load_json(rooms_path)
	content_track = str(rooms_payload.get("content_track", "legacy"))
	if content_track == "" and rooms_path == POST_UPDATE_ROOMS_PATH:
		content_track = "revelation_packets_v1"

	rooms_by_id = _index_rooms(rooms_payload)
	var events_payload: Dictionary = _load_json(events_path)
	room_events_by_room = _index_room_events(events_payload.get("room_events", {}))
	special_events = _index_special_events(events_payload.get("special_events", {}))
	deck_config = _load_json(decks_path)
	enemies_by_id = _index_simple_map(_load_json(ENEMIES_PATH).get("enemies", []))
	mutations_by_id = _index_simple_map(_load_json(MUTATIONS_PATH).get("mutations", []))
	symbiotes_by_id = _index_simple_map(_load_json(SYMBIOTES_PATH).get("symbiotes", []))
	artifacts_by_id = _index_simple_map(_load_json(ARTIFACTS_PATH).get("artifacts", []))


func _build_revelation_pressure_defaults() -> Dictionary:
	return REVELATION_PRESSURE_DEFAULTS.duplicate(true)


func _build_base_player_state() -> Dictionary:
	var stats: Dictionary = deck_config.get("base_player_stats", {}).duplicate(true)
	if stats.is_empty():
		stats = {
			"damage": 8,
			"armor": 2,
			"shield": 6,
			"health": 30,
			"ambush_chance": 0.15,
			"initiative": 0.6
		}
	return stats


func _build_base_operation_state() -> void:
	officer_state = {
		"torah": _build_officer_state("Torah", "Symbolic Asset", {"resonance": 17, "control": 12, "command": 7, "security": 5}, 8, 6),
		"brooks": _build_officer_state("Brooks", "Squad Leader", {"command": 15, "security": 14, "logistics": 9, "medicine": 5}, 10, 8),
		"lt_mara_owen": _build_officer_state("Lt. Mara Owen", "Containment Lead", {"command": 13, "security": 12, "logistics": 10, "science": 7}, 9, 8),
		"dr_samira_iyad": _build_officer_state("Dr. Samira Iyad", "Field Researcher", {"science": 16, "medicine": 9, "resonance": 12, "command": 6}, 12, 9),
		"agent_caleb_ross": _build_officer_state("Agent Caleb Ross", "Tactical Security", {"security": 16, "command": 8, "logistics": 7, "medicine": 4}, 9, 7),
		"specialist_mina_park": _build_officer_state("Specialist Mina Park", "Evidence Systems", {"science": 12, "logistics": 14, "resonance": 8, "command": 5}, 8, 9),
		"dr_lenora_saye": _build_officer_state("Dr. Lenora Saye", "Medical Liaison", {"medicine": 16, "science": 11, "command": 8, "resonance": 5}, 9, 10)
	}
	department_state = {
		"medical": _build_department_state(10, 10),
		"field_research": _build_department_state(12, 9),
		"tactical_security": _build_department_state(9, 8),
		"containment": _build_department_state(10, 8),
		"logistics": _build_department_state(8, 8),
		"operations": _build_department_state(8, 8)
	}
	ship_system_state = {
		"quarantine_screens": _build_ship_system_state(8, 0),
		"resonance_meters": _build_ship_system_state(6, 0),
		"containment_seals": _build_ship_system_state(8, 0),
		"field_comms": _build_ship_system_state(6, 0),
		"evidence_storage": _build_ship_system_state(5, 0)
	}


func _build_officer_state(officer_name: String, role: String, skills: Dictionary, stress: int, fatigue: int) -> Dictionary:
	return {
		"name": officer_name,
		"role": role,
		"skills": skills.duplicate(true),
		"morale": 70,
		"mental_state": "steady",
		"stress": stress,
		"fatigue": fatigue,
		"injury": 0,
		"contamination": 0,
		"loyalty": 70,
		"availability": 100
	}


func _build_department_state(stress: int, fatigue: int) -> Dictionary:
	return {
		"stress": stress,
		"fatigue": fatigue,
		"casualties": 0,
		"contamination": 0,
		"efficiency": 78
	}


func _build_ship_system_state(stress: int, anomaly: int) -> Dictionary:
	return {
		"condition": 78,
		"stress": stress,
		"anomaly": anomaly
	}


func _build_base_deck_room_ids() -> Array[String]:
	var chosen_rooms: Array[String] = []
	for starter_room in deck_config.get("starter_rooms", []):
		var room_id := str(starter_room)
		if room_id != "" and not chosen_rooms.has(room_id):
			chosen_rooms.append(room_id)

	for rule_variant in deck_config.get("draw_rules", []):
		if not rule_variant is Dictionary:
			continue

		var rule: Dictionary = rule_variant
		var pool_name := str(rule.get("pool", ""))
		var count := int(rule.get("count", 0))
		var pool_variant = deck_config.get("room_pools", {}).get(pool_name, [])
		if not pool_variant is Array:
			continue

		var pool_ids: Array[String] = []
		for value in pool_variant:
			pool_ids.append(str(value))

		for _index in count:
			var room_choice := _draw_room_from_pool(pool_ids, chosen_rooms)
			if room_choice != "":
				chosen_rooms.append(room_choice)

	_ensure_room_type_in_deck(chosen_rooms, "combat")
	return chosen_rooms


func _build_active_deck_cards() -> Array[Dictionary]:
	var cards: Array[Dictionary] = []

	var enemy_count := int(max(1 + danger, 1))
	enemy_count += int(_get_pressure_count("avoid_combat") / 2)
	if _is_ending_locked("hunter"):
		enemy_count += 2
	var max_enemy_cards := int(deck_config.get("max_enemy_cards_per_deck", 4))
	if max_enemy_cards > 0:
		enemy_count = min(enemy_count, max_enemy_cards)
	_append_room_cards(cards, _get_room_pool_ids("enemy"), enemy_count, "combat", [])

	var branch_count := _rng.randi_range(
		int(deck_config.get("branch_cards_min", 1)),
		int(deck_config.get("branch_cards_max", 2))
	)
	_append_room_cards(cards, _get_room_pool_ids("branch"), branch_count, "", ["combat", "boss", "symbiote"])

	var straight_count := _rng.randi_range(
		int(deck_config.get("straight_cards_min", 2)),
		int(deck_config.get("straight_cards_max", 4))
	)
	_append_room_cards(cards, _get_room_pool_ids("straight_noncombat"), straight_count, "", ["combat", "boss", "symbiote"])

	if bool(deck_config.get("symbiote_card_per_deck", true)) and not _get_available_symbiote_ids().is_empty():
		cards.append({"kind": "symbiote"})

	_shuffle_deck_cards(cards)
	return cards


func _get_room_pool_ids(pool_name: String) -> Array[String]:
	var pool_variant = deck_config.get("room_pools", {}).get(pool_name, [])
	var pool_ids: Array[String] = []
	if not pool_variant is Array:
		return pool_ids
	for value in pool_variant:
		var room_id := str(value)
		if room_id != "":
			pool_ids.append(room_id)
	return pool_ids


func _append_room_cards(cards: Array[Dictionary], pool_ids: Array[String], count: int, preferred_type: String = "", excluded_types: Array[String] = []) -> void:
	var available_ids := pool_ids.duplicate()
	var chosen_ids: Array[String] = []
	for existing_card in cards:
		if existing_card is Dictionary:
			var existing_room_id := str(existing_card.get("room_id", ""))
			if existing_room_id != "" and not chosen_ids.has(existing_room_id):
				chosen_ids.append(existing_room_id)

	for _index in range(max(count, 0)):
		var room_id := _draw_room_from_pool(available_ids, chosen_ids)
		if room_id == "":
			return
		if _get_eligible_events_for_room(room_id, preferred_type, excluded_types).is_empty():
			available_ids.erase(room_id)
			continue
		chosen_ids.append(room_id)
		cards.append({
			"kind": "room",
			"room_id": room_id,
			"event_type": preferred_type,
			"excluded_types": excluded_types.duplicate()
		})


func _shuffle_deck_cards(cards: Array[Dictionary]) -> void:
	for index in range(cards.size() - 1, 0, -1):
		var swap_index := _rng.randi_range(0, index)
		var temp := cards[index]
		cards[index] = cards[swap_index]
		cards[swap_index] = temp


func _remove_symbiote_cards_from_active_deck() -> void:
	for index in range(active_deck_cards.size() - 1, -1, -1):
		if str(active_deck_cards[index].get("kind", "")) == "symbiote":
			active_deck_cards.remove_at(index)


func _ensure_room_type_in_deck(chosen_rooms: Array[String], event_type: String) -> void:
	for room_id in chosen_rooms:
		if _room_has_event_type(room_id, event_type):
			return

	var eligible_rooms := _get_rooms_with_event_type(event_type)
	if eligible_rooms.is_empty():
		return

	var replacement_room := eligible_rooms[_rng.randi_range(0, eligible_rooms.size() - 1)]
	if chosen_rooms.has(replacement_room):
		return

	for index in range(chosen_rooms.size() - 1, -1, -1):
		var room_id := chosen_rooms[index]
		if room_id == str(deck_config.get("opening_room_id", "")):
			continue
		if not _room_has_event_type(room_id, event_type):
			chosen_rooms[index] = replacement_room
			return

	chosen_rooms.append(replacement_room)


func _get_rooms_with_event_type(event_type: String) -> Array[String]:
	var room_ids: Array[String] = []
	for room_id_variant in room_events_by_room.keys():
		var room_id := str(room_id_variant)
		if room_id != "" and _room_has_event_type(room_id, event_type):
			room_ids.append(room_id)
	return room_ids


func _room_has_event_type(room_id: String, event_type: String) -> bool:
	var room_events: Array = room_events_by_room.get(room_id, [])
	for event_variant in room_events:
		if not event_variant is Dictionary:
			continue
		if str(event_variant.get("type", "")) == event_type:
			return true
	return false


func _reset_active_deck() -> void:
	active_deck_cards = _build_active_deck_cards()
	active_deck_room_ids = base_deck_room_ids.duplicate(true)
	consumed_room_events.clear()
	_merchant_due_before_redraw = false


func _build_opening_encounter(room_id: String) -> Dictionary:
	var opening_event_id := str(deck_config.get("opening_event_id", ""))
	if opening_event_id != "" and special_events.has(opening_event_id):
		return _build_special_encounter(opening_event_id, room_id, get_room_data(room_id))

	var room_events: Array = room_events_by_room.get(room_id, [])
	for event_variant in room_events:
		if event_variant is Dictionary and str(event_variant.get("id", "")) == opening_event_id:
			return _build_room_encounter(room_id, event_variant)

	return _build_next_encounter()


func _build_next_encounter() -> Dictionary:
	if not _pending_encounter_after_overlay.is_empty():
		var pending_encounter := _pending_encounter_after_overlay.duplicate(true)
		_pending_encounter_after_overlay.clear()
		return pending_encounter

	if _pending_room_id_after_transition != "":
		return _build_pending_room_encounter()

	var story_event_id := _pop_available_story_event_id()
	if story_event_id != "":
		return _build_special_encounter(story_event_id)

	if not _pending_director_events.is_empty():
		var director_event_id := str(_pending_director_events.pop_front())
		if special_events.has(director_event_id):
			return _build_special_encounter(director_event_id)

	var named_ending_event_id := _pick_named_ending_event_id()
	if named_ending_event_id != "":
		_named_ending_triggered = true
		return _build_special_encounter(named_ending_event_id)

	if _should_offer_corruption_claim():
		_corruption_claim_triggered = true
		return _build_special_encounter("corruption_claim")

	if _should_offer_hunter_reckoning():
		_hunter_reckoning_triggered = true
		return _build_special_encounter("hunter_reckoning")

	if _should_offer_merchant_reckoning():
		_merchant_reckoning_triggered = true
		return _build_special_encounter("merchant_reckoning")

	if _should_offer_merchant():
		_merchant_triggered_at_rooms[rooms_cleared] = true
		return _build_special_encounter("merchant_arrival", current_room_id, get_room_data(current_room_id))

	if _should_offer_symbiote_host():
		_symbiote_triggered_at_rooms[rooms_cleared] = true
		return _build_symbiote_encounter()

	if _should_offer_corruption_spike_room():
		_corruption_spike_triggers += 1
		return _build_corruption_spike_encounter()

	if _should_offer_danger_notice():
		_danger_notice_triggers += 1
		return _build_special_encounter("danger_spike_notice")

	return _draw_room_encounter()


func _should_offer_merchant() -> bool:
	var merchant_every := int(deck_config.get("merchant_every", 5))
	if merchant_every <= 0 or rooms_cleared <= 0:
		return false
	if rooms_cleared % merchant_every != 0:
		return false
	return not _merchant_triggered_at_rooms.has(rooms_cleared)


func _should_offer_merchant_reckoning() -> bool:
	if _merchant_reckoning_triggered:
		return false
	if not special_events.has("merchant_reckoning"):
		return false
	var refusal_limit := int(deck_config.get("merchant_refusal_limit", 0))
	var claim_limit := int(deck_config.get("merchant_claim_limit", 3))
	var refusal_due := refusal_limit > 0 and merchant_refusals >= refusal_limit
	var claim_due := claim_limit > 0 and merchant_claim >= claim_limit
	return refusal_due or claim_due


func _should_offer_hunter_reckoning() -> bool:
	if _hunter_reckoning_triggered:
		return false
	if not special_events.has("hunter_reckoning"):
		return false
	if not _can_offer_terminal_pressure_event():
		return false
	return _is_ending_locked("hunter")


func _should_offer_corruption_claim() -> bool:
	if _corruption_claim_triggered:
		return false
	if not special_events.has("corruption_claim"):
		return false
	if not _can_offer_terminal_pressure_event():
		return false
	return _is_ending_locked("corruption")


func _can_offer_terminal_pressure_event() -> bool:
	var minimum_rooms := int(deck_config.get("ending_reckoning_min_rooms", 12))
	return rooms_cleared >= max(minimum_rooms, 0)


func _pick_named_ending_event_id() -> String:
	if _named_ending_triggered:
		return ""
	if not _can_offer_terminal_pressure_event():
		return ""

	if special_events.has("ending_merchant_debt"):
		var claim_limit := int(deck_config.get("merchant_claim_limit", 3))
		if claim_limit > 0 and merchant_claim >= claim_limit:
			return "ending_merchant_debt"

	var threshold := int(deck_config.get("named_ending_state_threshold", 3))
	var best_event_id := ""
	var best_score := 0
	var candidates := [
		{
			"event_id": "ending_soft_captain_transit",
			"patterns": ["rib_lock", "soft_captain", "ferry", "toll"]
		},
		{
			"event_id": "ending_pell_white_route",
			"patterns": ["marrow", "pell", "survey"]
		},
		{
			"event_id": "ending_operator_component",
			"patterns": ["operator", "silt", "procedure"]
		},
		{
			"event_id": "ending_opened_hunt_route",
			"patterns": ["hunt", "scar", "red_guard", "red_hunter", "pursuit", "red_lane"]
		},
		{
			"event_id": "ending_merchant_debt",
			"patterns": ["merchant_claim", "larder", "credit", "hunger", "ledger"]
		},
		{
			"event_id": "ending_lumen_wet_claim",
			"patterns": ["harbor", "wet_marker", "intake_rhythm"]
		},
		{
			"event_id": "ending_mother_chancel_tool",
			"patterns": ["rite", "mother", "chancel"]
		},
		{
			"event_id": "ending_commandant_launch",
			"patterns": ["launch", "commandant", "route_packet"]
		}
	]

	for candidate in candidates:
		var event_id := str(candidate.get("event_id", ""))
		if event_id == "" or not special_events.has(event_id):
			continue
		var score := _count_environment_state_matches(candidate.get("patterns", []))
		if event_id == "ending_merchant_debt":
			score += merchant_claim
		if score > best_score:
			best_score = score
			best_event_id = event_id

	if best_score >= threshold:
		return best_event_id
	return ""


func _count_environment_state_matches(patterns_variant: Variant) -> int:
	var patterns: Array[String] = []
	if patterns_variant is Array:
		for pattern_variant in patterns_variant:
			var pattern := str(pattern_variant)
			if pattern != "":
				patterns.append(pattern)
	if patterns.is_empty():
		return 0

	var count := 0
	for state_key_variant in environment_state.keys():
		var state_key := str(state_key_variant)
		for pattern in patterns:
			if state_key.contains(pattern):
				count += 1
				break
	return count


func _should_offer_danger_notice() -> bool:
	var threshold := int(deck_config.get("danger_notice_threshold", 2))
	if threshold <= 0:
		return false
	if not special_events.has("danger_spike_notice"):
		return false
	return danger >= threshold * (_danger_notice_triggers + 1)


func _should_offer_corruption_spike_room() -> bool:
	var threshold := int(deck_config.get("corruption_spike_threshold", 3))
	if threshold <= 0:
		return false
	if not special_events.has("corruption_spike_room"):
		return false
	return corruption >= threshold * (_corruption_spike_triggers + 1)


func _should_offer_symbiote_host() -> bool:
	var offer_limit := int(deck_config.get("symbiote_offer_limit", 0))
	if offer_limit > 0 and _symbiote_triggered_at_rooms.size() >= offer_limit:
		return false
	var first_after_rooms := int(deck_config.get("symbiote_first_after_rooms", -1))
	if first_after_rooms >= 0:
		if rooms_cleared != first_after_rooms:
			return false
		if _symbiote_triggered_at_rooms.has(rooms_cleared):
			return false
		if not special_events.has("symbiote_host_offer"):
			return false
		return not _get_available_symbiote_ids().is_empty()
	var symbiote_every := int(deck_config.get("symbiote_every", 3))
	if symbiote_every <= 0 or rooms_cleared <= 0:
		return false
	if rooms_cleared % symbiote_every != 0:
		return false
	if _symbiote_triggered_at_rooms.has(rooms_cleared):
		return false
	if not special_events.has("symbiote_host_offer"):
		return false
	return not _get_available_symbiote_ids().is_empty()


func _build_symbiote_encounter() -> Dictionary:
	var available_symbiote_ids := _get_available_symbiote_ids()
	if available_symbiote_ids.is_empty():
		return _draw_room_encounter()

	var event_data: Dictionary = special_events.get("symbiote_host_offer", {}).duplicate(true)
	if event_data.is_empty():
		return _draw_room_encounter()

	var choice_count := int(event_data.get("symbiote_choice_count", 3))
	event_data["symbiote_choices"] = _draw_symbiote_choices(available_symbiote_ids, choice_count)
	event_data["line_1"] = "Chorus, dying host ahead. Several symbiotes still clinging to it."
	event_data["line_2"] = "One bond makes one dependency. The shock kills the rest."

	return {
		"kind": "special_event",
		"room_id": current_room_id,
		"room_data": get_room_data(current_room_id),
		"event_id": str(event_data.get("id", "symbiote_host_offer")),
		"event_data": event_data,
		"scene_path": str(event_data.get("scene_path", "")),
		"lines": _build_lines({}, event_data, false),
		"buttons": _build_buttons(event_data),
		"enemy_data": _resolve_enemy_data(event_data),
		"counts_as_room": false,
		"consumed": false
	}


func _build_corruption_spike_encounter() -> Dictionary:
	var room_id := "spiked_red_corridor"
	var event_data: Dictionary = special_events.get("corruption_spike_room", {}).duplicate(true)
	if event_data.is_empty():
		return _draw_room_encounter()

	return {
		"kind": "special_event",
		"room_id": room_id,
		"room_data": get_room_data(room_id),
		"event_id": str(event_data.get("id", "corruption_spike_room")),
		"event_data": event_data,
		"scene_path": str(event_data.get("scene_path", "")),
		"lines": _build_lines(get_room_data(room_id), event_data),
		"buttons": _build_buttons(event_data),
		"enemy_data": _resolve_enemy_data(event_data),
		"counts_as_room": true,
		"consumed": false
	}


func _draw_room_encounter() -> Dictionary:
	var fail_safe := 0
	while fail_safe < 128:
		fail_safe += 1
		if active_deck_cards.is_empty():
			if _merchant_due_before_redraw:
				_reset_active_deck()
			elif rooms_cleared > 0 and special_events.has("merchant_arrival"):
				_merchant_due_before_redraw = true
				_merchant_triggered_at_rooms[rooms_cleared] = true
				return _build_special_encounter("merchant_arrival", current_room_id, get_room_data(current_room_id))
			else:
				_reset_active_deck()

		if active_deck_cards.is_empty():
			return _build_fallback_encounter("active deck empty after reset")

		var card: Dictionary = active_deck_cards.pop_front()
		if str(card.get("kind", "")) == "symbiote":
			return _build_symbiote_encounter()

		var room_id := str(card.get("room_id", ""))
		var preferred_type := str(card.get("event_type", ""))
		var excluded_types: Array[String] = _normalize_string_array(card.get("excluded_types", []))
		var eligible_events := _get_eligible_events_for_room(room_id, preferred_type, excluded_types)
		if eligible_events.is_empty():
			continue

		var event_data: Dictionary = eligible_events[_rng.randi_range(0, eligible_events.size() - 1)]
		_consume_room_on_entry(room_id)
		return _build_room_encounter(room_id, event_data)

	return _build_fallback_encounter("no eligible event after 128 draw attempts")


func _build_pending_room_encounter() -> Dictionary:
	var room_id := _pending_room_id_after_transition
	_pending_room_id_after_transition = ""
	if room_id == "":
		return _draw_room_encounter()

	var eligible_events := _get_eligible_events_for_room(room_id)
	if eligible_events.is_empty():
		active_deck_room_ids.erase(room_id)
		return _draw_room_encounter()

	var event_data: Dictionary = eligible_events[_rng.randi_range(0, eligible_events.size() - 1)]
	_consume_room_on_entry(room_id)
	return _build_room_encounter(room_id, event_data)


func _pick_preview_room_id() -> String:
	var candidate_room_ids: Array[String] = []
	for room_id in active_deck_room_ids:
		if not _get_eligible_events_for_room(room_id).is_empty():
			candidate_room_ids.append(room_id)

	if candidate_room_ids.is_empty():
		return ""

	return candidate_room_ids[_rng.randi_range(0, candidate_room_ids.size() - 1)]


func _get_eligible_events_for_room(room_id: String, preferred_type: String = "", excluded_types: Array[String] = []) -> Array[Dictionary]:
	if _is_room_consumed(room_id):
		return []
	var eligible_events := _collect_eligible_events_for_room(room_id, preferred_type, excluded_types, false)
	if eligible_events.is_empty() and ["post_update_text_only", "nightmare_voyage_packets_v1"].has(content_track):
		eligible_events = _collect_eligible_events_for_room(room_id, preferred_type, excluded_types, true)
	return eligible_events


func _consume_room_on_entry(room_id: String) -> void:
	if not _should_consume_room_on_entry(room_id):
		return
	consumed_rooms[room_id] = true


func _is_room_consumed(room_id: String) -> bool:
	return bool(consumed_rooms.get(room_id, false))


func _should_consume_room_on_entry(room_id: String) -> bool:
	if room_id == "" or content_track != "revelation_packets_v1":
		return false
	var room_data: Dictionary = rooms_by_id.get(room_id, {})
	return str(room_data.get("type", "")) == "mission"


func _collect_eligible_events_for_room(room_id: String, preferred_type: String = "", excluded_types: Array[String] = [], ignore_consumed: bool = false) -> Array[Dictionary]:
	var eligible_events: Array[Dictionary] = []
	var room_events: Array = room_events_by_room.get(room_id, [])
	var consumed_for_room: Dictionary = consumed_room_events.get(room_id, {})

	for event_variant in room_events:
		if not event_variant is Dictionary:
			continue

		var event_data: Dictionary = event_variant
		var event_id := str(event_data.get("id", ""))
		if event_id == "":
			continue

		if not ignore_consumed and consumed_for_room.has(event_id):
			continue

		if not ignore_consumed and permanently_consumed_events.has(event_id):
			continue

		var event_type := str(event_data.get("type", ""))
		if preferred_type != "" and event_type != preferred_type:
			continue
		if excluded_types.has(event_type):
			continue

		eligible_events.append(event_data)

	return eligible_events


func _build_room_encounter(room_id: String, event_data: Dictionary) -> Dictionary:
	var room_data := get_room_data(room_id)
	var prepared_event_data := _prepare_event_data(event_data)
	var enemy_data := _resolve_enemy_data(prepared_event_data)
	var scene_path := str(prepared_event_data.get("scene_path", ""))
	if scene_path == "" and str(prepared_event_data.get("type", "")) == "combat":
		scene_path = str(enemy_data.get("scene_path", ""))
	return {
		"kind": "room_event",
		"room_id": room_id,
		"room_data": room_data,
		"event_id": str(prepared_event_data.get("id", "")),
		"event_data": prepared_event_data,
		"scene_path": scene_path,
		"lines": _build_lines(room_data, prepared_event_data),
		"buttons": _build_buttons(prepared_event_data),
		"enemy_data": enemy_data,
		"counts_as_room": true,
		"consumed": false
	}


func _prepare_event_data(event_data: Dictionary) -> Dictionary:
	var prepared_event_data := _apply_state_overrides(event_data)
	if prepared_event_data.has("symbiote_choice_count") and not prepared_event_data.has("symbiote_choices"):
		var available_symbiote_ids := _get_available_symbiote_ids()
		var choice_count := int(prepared_event_data.get("symbiote_choice_count", 3))
		prepared_event_data["symbiote_choices"] = _draw_symbiote_choices(available_symbiote_ids, choice_count)
	if content_track == "revelation_packets_v1" and str(prepared_event_data.get("type", "")) == "interlude":
		prepared_event_data = _prepare_debrief_choice_buttons(prepared_event_data)
	return prepared_event_data


func _prepare_debrief_choice_buttons(event_data: Dictionary) -> Dictionary:
	var choices_variant = event_data.get("choices", [])
	if not choices_variant is Array or choices_variant.is_empty():
		return event_data

	var prepared := event_data.duplicate(true)
	var event_id := str(prepared.get("id", "debrief"))
	var buttons: Array[Dictionary] = []
	for index in range(choices_variant.size()):
		var choice_text := str(choices_variant[index]).strip_edges()
		if choice_text == "":
			continue
		buttons.append({
			"label": _compact_button_label(choice_text, 96, 0),
			"action": "debrief_choice:%s:%d" % [event_id, index],
			"voice_aliases": _build_debrief_choice_aliases(choice_text, index)
		})
	if not buttons.is_empty():
		prepared["buttons"] = buttons
	return prepared


func _compact_button_label(text: String, max_chars: int = 42, max_words: int = 6) -> String:
	var compact := text.replace("\n", " ").strip_edges()
	while compact.find("  ") != -1:
		compact = compact.replace("  ", " ")
	var words := compact.split(" ", false)
	if max_words > 0 and words.size() > max_words:
		var trimmed_words: Array[String] = []
		for index in range(max_words):
			trimmed_words.append(str(words[index]))
		compact = " ".join(trimmed_words).trim_suffix(",").trim_suffix(";").trim_suffix(":") + "…"
	if compact.length() <= max_chars:
		return compact
	return compact.substr(0, max_chars - 1).strip_edges() + "…"


func _build_debrief_choice_aliases(choice_text: String, index: int) -> Array[String]:
	var aliases: Array[String] = [
		"choice %d" % (index + 1),
		"option %d" % (index + 1)
	]
	var lowered := choice_text.to_lower()
	for word in lowered.split(" ", false):
		var clean := str(word).strip_edges()
		if clean.length() >= 4 and not aliases.has(clean):
			aliases.append(clean)
		if aliases.size() >= 5:
			break
	return aliases


func _apply_state_overrides(event_data: Dictionary) -> Dictionary:
	var prepared_event_data := event_data.duplicate(true)
	var overrides_variant = event_data.get("state_overrides", [])
	if not overrides_variant is Array:
		return prepared_event_data

	for override_variant in overrides_variant:
		if not override_variant is Dictionary:
			continue
		var override: Dictionary = override_variant
		if not _state_override_matches(override):
			continue

		var event_override_variant = override.get("event", {})
		if event_override_variant is Dictionary:
			var event_override: Dictionary = event_override_variant
			for key in event_override.keys():
				prepared_event_data[key] = event_override[key]

		var consume_keys := _normalize_string_array(override.get("consume_state_keys", []))
		if consume_keys.is_empty() and bool(override.get("consume_state", false)):
			consume_keys = _state_override_keys(override)
		for state_key in consume_keys:
			environment_state.erase(state_key)
		return prepared_event_data

	return prepared_event_data


func _state_override_matches(override: Dictionary) -> bool:
	var any_keys := _state_override_keys(override)
	var all_keys := _normalize_string_array(override.get("all_state_keys", []))
	if any_keys.is_empty() and all_keys.is_empty():
		return false

	for state_key in all_keys:
		if not environment_state.has(state_key):
			return false
	if not all_keys.is_empty():
		return true

	for state_key in any_keys:
		if environment_state.has(state_key):
			return true
	return false


func _state_override_keys(override: Dictionary) -> Array[String]:
	var keys := _normalize_string_array(override.get("state_keys", []))
	var state_key := str(override.get("state_key", ""))
	if state_key != "" and not keys.has(state_key):
		keys.append(state_key)
	return keys


func _build_special_encounter(event_id: String, room_id_override: String = "", room_data_override: Dictionary = {}) -> Dictionary:
	var event_data: Dictionary = _prepare_event_data(special_events.get(event_id, {}))
	var room_id := room_id_override if room_id_override != "" else str(event_data.get("room_id", current_room_id))
	var room_data := room_data_override if not room_data_override.is_empty() else get_room_data(room_id)
	return {
		"kind": "special_event",
		"room_id": room_id,
		"room_data": room_data,
		"event_id": event_id,
		"event_data": event_data,
		"scene_path": str(event_data.get("scene_path", "")),
		"lines": _build_lines({}, event_data, false),
		"buttons": _build_buttons(event_data),
		"enemy_data": _resolve_enemy_data(event_data),
		"counts_as_room": false,
		"consumed": false
	}


func _build_fallback_encounter(reason: String) -> Dictionary:
	var room_id := current_room_id if current_room_id != "" else str(deck_config.get("opening_room_id", "bridge_initial_descent"))
	var event_data := {
		"id": "fallback_empty_draw",
		"type": "narrative",
		"speaker": "Captain",
		"line_1": "The encounter deck returned no valid operation.",
		"line_2": "Debug: %s. The bridge resets the draw and continues descent." % reason,
		"buttons": [{
			"label": "Force the route open",
			"action": "proceed",
			"voice_aliases": ["proceed", "advance", "move on", "go forward", "step through"]
		}]
	}
	_reset_active_deck()
	return {
		"kind": "fallback_event",
		"room_id": room_id,
		"room_data": get_room_data(room_id),
		"event_id": "fallback_empty_draw",
		"event_data": event_data,
		"scene_path": "",
		"lines": _build_lines({}, event_data, false),
		"buttons": _build_buttons(event_data),
		"enemy_data": {},
		"counts_as_room": false,
		"consumed": false
	}


func _build_lines(room_data: Dictionary, event_data: Dictionary, include_room_description: bool = true) -> Array[String]:
	var lines: Array[String] = []
	if include_room_description:
		lines.append_array(_build_room_description_lines(room_data))

	var line_1 := str(event_data.get("line_1", room_data.get("ui_text", {}).get("line_1", "")))
	var line_2 := str(event_data.get("line_2", room_data.get("ui_text", {}).get("line_2", "")))

	if line_1 != "":
		lines.append(line_1)
	if line_2 != "":
		lines.append(line_2)

	lines.append_array(_build_operation_plan_lines(event_data))
	return lines


func _build_room_description_lines(room_data: Dictionary) -> Array[String]:
	var room_id := str(room_data.get("id", ""))
	if room_id == "":
		return []

	var visit_count := int(room_visit_counts.get(room_id, 0))
	room_visit_counts[room_id] = visit_count + 1
	var description := ""
	if visit_count <= 0:
		description = str(room_data.get("first_visit_description", ""))
	else:
		description = str(room_data.get("return_description", ""))

	if description == "":
		description = str(room_data.get("description", ""))
	if description == "":
		return _build_room_sitrep_lines(room_data, visit_count)
	var chronological_sitrep_lines := _build_chronological_room_sitrep_lines(room_data, description, visit_count)
	if not chronological_sitrep_lines.is_empty():
		return chronological_sitrep_lines

	var lines := _build_room_sitrep_lines(room_data, visit_count)
	lines.append(description)
	return lines


func _build_chronological_room_sitrep_lines(room_data: Dictionary, description: String, visit_count: int) -> Array[String]:
	if content_track != "revelation_packets_v1" or visit_count > 0:
		return []
	if str(room_data.get("type", "")) != "mission":
		return []

	var detection_report := str(room_data.get("detection_report", "")).strip_edges()
	var current_situation := str(room_data.get("current_situation", "")).strip_edges()
	if detection_report == "" and current_situation == "":
		return []

	var lines: Array[String] = ["SITREP:"]
	if detection_report != "":
		lines.append("DETECTION: %s" % detection_report)
	lines.append(description)
	if current_situation != "":
		lines.append("CURRENT: %s" % current_situation)
	return lines


func _build_room_sitrep_lines(room_data: Dictionary, visit_count: int) -> Array[String]:
	if content_track != "revelation_packets_v1" or visit_count > 0:
		return []
	if str(room_data.get("type", "")) != "mission":
		return []

	var lines: Array[String] = ["SITREP:"]
	var detection_report := str(room_data.get("detection_report", "")).strip_edges()
	var current_situation := str(room_data.get("current_situation", "")).strip_edges()
	if detection_report != "":
		lines.append("DETECTION: %s" % detection_report)
	if current_situation != "":
		lines.append("CURRENT: %s" % current_situation)
	if lines.size() <= 1:
		return []
	return lines


func _build_buttons(event_data: Dictionary) -> Array:
	if event_data.has("symbiote_choices"):
		return _build_symbiote_choice_buttons(event_data)

	var buttons_variant = event_data.get("buttons", [])
	var buttons: Array = []
	if buttons_variant is Array and not buttons_variant.is_empty():
		buttons = buttons_variant.duplicate(true)
	else:
		buttons = [_default_proceed_button()]
	buttons = _annotate_operation_buttons(buttons, event_data)
	if buttons.is_empty():
		buttons = [{
			"label": "Delay for reassignment",
			"action": "observe",
			"voice_aliases": ["delay", "reassign", "wait for reassignment"]
		}]
	if content_track != "revelation_packets_v1":
		buttons = _annotate_resource_buttons(buttons, event_data)
	if content_track == "revelation_packets_v1":
		buttons = _append_artifact_option_buttons(buttons, event_data)
	return _append_symbiote_activation_buttons(buttons, event_data)


func _build_operation_plan_lines(event_data: Dictionary) -> Array[String]:
	var plans := _operation_plans_for_event(event_data)
	if plans.is_empty():
		return []

	var lines: Array[String] = []
	lines.append("Proposals:" if content_track == "revelation_packets_v1" else "Operation estimates:")
	for plan in plans:
		var action_id := str(plan.get("action", ""))
		if action_id == "":
			continue
		var resolved_plan := _operation_plan_for_action(action_id, event_data)
		if not resolved_plan.is_empty():
			plan = resolved_plan
		var officer_id := str(plan.get("officer_id", ""))
		var officer := _get_officer_state(officer_id)
		var officer_name := str(plan.get("officer_name", officer.get("name", officer_id)))
		var plan_text := str(plan.get("intent", plan.get("tactical_step", plan.get("yield", "unlisted plan"))))
		var yield_text := str(plan.get("yield", "unknown yield"))
		var risk_text := str(plan.get("risk", "unlisted risk"))
		var condition := _condition_for_record(officer)
		if content_track == "revelation_packets_v1":
			if plan.has("backup_for"):
				var primary_name := str(plan.get("primary_unavailable_name", plan.get("backup_for", "primary operator")))
				var backup_text := str(plan.get("backup_intent", plan_text))
				lines.append("%s unavailable; %s covers: %s Risk: %s." % [primary_name, officer_name, backup_text, risk_text])
				continue
			if not _is_operation_plan_available(plan):
				lines.append("%s: unavailable. %s Risk: %s." % [officer_name, plan_text, risk_text])
				continue
			lines.append("%s: %s Risk: %s." % [officer_name, plan_text, risk_text])
			continue
		if not _is_operation_plan_available(plan):
			lines.append("%s: unavailable. Yield: %s. Risk: %s. Condition: %s." % [officer_name, yield_text, risk_text, condition])
			continue
		var estimate := int(round(_calculate_operation_chance(plan) * 100.0))
		lines.append("%s: %d%%. Yield: %s. Risk: %s. Condition: %s." % [officer_name, estimate, yield_text, risk_text, condition])
	return lines


func _annotate_operation_buttons(buttons: Array, event_data: Dictionary) -> Array:
	if _operation_plans_for_event(event_data).is_empty():
		return buttons

	var updated_buttons: Array = []
	for button_variant in buttons:
		if not button_variant is Dictionary:
			updated_buttons.append(button_variant)
			continue
		var button: Dictionary = button_variant.duplicate(true)
		var plan := _operation_plan_for_action(str(button.get("action", "")), event_data)
		if not plan.is_empty():
			if not _is_operation_plan_available(plan):
				continue
			if content_track == "revelation_packets_v1" and plan.has("backup_for"):
				button["label"] = "Backup: %s" % str(button.get("label", ""))
			if content_track != "revelation_packets_v1":
				var estimate := int(round(_calculate_operation_chance(plan) * 100.0))
				button["label"] = "%s (%d%%)" % [str(button.get("label", "")), estimate]
		updated_buttons.append(button)
	return updated_buttons


func _annotate_resource_buttons(buttons: Array, event_data: Dictionary) -> Array:
	var updated_buttons: Array = []
	for button_variant in buttons:
		if not button_variant is Dictionary:
			updated_buttons.append(button_variant)
			continue
		var button: Dictionary = button_variant.duplicate(true)
		var action_result := _get_event_action_result(str(button.get("action", "")), event_data)
		var preview := _resource_preview_for_action_result(action_result)
		if preview != "":
			var label := str(button.get("label", ""))
			button["label"] = "%s [%s]" % [label, preview]
		updated_buttons.append(button)
	return updated_buttons


func _append_artifact_option_buttons(buttons: Array, event_data: Dictionary) -> Array:
	var options_variant = event_data.get("artifact_options", [])
	if not options_variant is Array or options_variant.is_empty():
		return buttons

	var updated_buttons := buttons.duplicate(true)
	for index in range(options_variant.size()):
		var option_variant = options_variant[index]
		if not option_variant is Dictionary:
			continue
		var option: Dictionary = option_variant
		var artifact_id := str(option.get("artifact_id", "")).strip_edges()
		if artifact_id == "" or not owned_artifacts.has(artifact_id):
			continue
		if not _artifact_option_state_matches(option):
			continue
		var artifact_data: Dictionary = artifacts_by_id.get(artifact_id, {})
		var label := str(option.get("label", "Use %s" % str(artifact_data.get("name", artifact_id)))).strip_edges()
		updated_buttons.append({
			"label": label,
			"action": "use_artifact:%s:%d" % [artifact_id, index],
			"voice_aliases": _artifact_option_aliases(artifact_id, artifact_data, option)
		})
	return updated_buttons


func _artifact_option_state_matches(option: Dictionary) -> bool:
	for state_key in _normalize_string_array(option.get("requires_all_state_keys", [])):
		if not environment_state.has(state_key):
			return false
	var any_keys := _normalize_string_array(option.get("requires_any_state_keys", []))
	if any_keys.is_empty():
		return true
	for state_key in any_keys:
		if environment_state.has(state_key):
			return true
	return false


func _artifact_option_aliases(artifact_id: String, artifact_data: Dictionary, option: Dictionary) -> Array[String]:
	var aliases: Array[String] = ["artifact", "use artifact", artifact_id.replace("_", " ")]
	var artifact_name := str(artifact_data.get("name", "")).to_lower()
	if artifact_name != "":
		aliases.append(artifact_name)
	var label := str(option.get("label", "")).to_lower()
	for word in label.split(" ", false):
		var clean := str(word).strip_edges()
		if clean.length() >= 4 and not aliases.has(clean):
			aliases.append(clean)
		if aliases.size() >= 7:
			break
	return aliases


func _resource_preview_for_action_result(action_result: Dictionary) -> String:
	if action_result.is_empty():
		return ""
	var deltas: Dictionary = {}
	var resource_changes_variant = action_result.get("resource_changes", {})
	if resource_changes_variant is Dictionary:
		var resource_changes: Dictionary = resource_changes_variant
		for key_variant in resource_changes.keys():
			var label := _resource_label_for_resource_key(str(key_variant))
			var delta := _resource_delta_from_value(resource_changes.get(key_variant))
			if label != "" and delta != 0:
				deltas[label] = int(deltas.get(label, 0)) + delta
	for change_variant in action_result.get("environment_state_changes", []):
		if not change_variant is Dictionary:
			continue
		var change: Dictionary = change_variant
		var key := str(change.get("key", change.get("state_key", "")))
		var delta := int(change.get("delta", 0))
		var label := _resource_label_for_delta_key(key)
		if label == "" or delta == 0:
			continue
		deltas[label] = int(deltas.get(label, 0)) + delta
	var parts: Array[String] = []
	for label in ["Food", "Fuel", "Water", "Morale", "Unrest"]:
		var delta := int(deltas.get(label, 0))
		if delta != 0:
			parts.append("%s %s" % [label, _format_signed_delta(delta)])
	return ", ".join(parts)


func _resource_label_for_resource_key(key: String) -> String:
	match key:
		"food", "resource.food", "resources.food":
			return "Food"
		"fuel", "resource.fuel", "resources.fuel":
			return "Fuel"
		"water", "resource.water", "resources.water":
			return "Water"
		"morale", "crew_morale", "squad.morale", "crew.morale":
			return "Morale"
		"unrest", "crew_unrest", "squad.refusal_risk", "squad.mutiny_risk", "crew.unrest":
			return "Unrest"
	return ""


func _resource_label_for_delta_key(key: String) -> String:
	match key:
		"resource.food", "resources.food":
			return "Food"
		"resource.fuel", "resources.fuel":
			return "Fuel"
		"resource.water", "resources.water":
			return "Water"
		"squad.morale", "crew.morale":
			return "Morale"
		"squad.refusal_risk", "squad.mutiny_risk", "crew.unrest":
			return "Unrest"
	return ""


func _resource_delta_from_value(value: Variant) -> int:
	if value is int or value is float:
		return int(value)
	var text := str(value).strip_edges()
	if text == "":
		return 0
	var token := str(text.split(" ", false)[0])
	if token.is_valid_int():
		return int(token)
	if token.begins_with("+"):
		var plus_text := token.substr(1)
		if plus_text.is_valid_int():
			return int(plus_text)
	return 0


func _operation_plans_for_event(event_data: Dictionary) -> Array[Dictionary]:
	var plans_variant = event_data.get("operation_plans", [])
	var plans: Array[Dictionary] = []
	if plans_variant is Array:
		for plan_variant in plans_variant:
			if plan_variant is Dictionary:
				plans.append(plan_variant)
	elif plans_variant is Dictionary:
		var plan_map: Dictionary = plans_variant
		for action_id_variant in plan_map.keys():
			var plan_variant = plan_map[action_id_variant]
			if plan_variant is Dictionary:
				var plan: Dictionary = plan_variant.duplicate(true)
				plan["action"] = str(plan.get("action", action_id_variant))
				plans.append(plan)
	return plans


func _operation_plan_for_action(action_id: String, event_data: Dictionary) -> Dictionary:
	var base_action := _base_action_id(action_id)
	var unavailable_plan: Dictionary = {}
	for plan in _operation_plans_for_event(event_data):
		var plan_action := str(plan.get("action", ""))
		if plan_action == action_id or plan_action == base_action:
			if _is_operation_plan_available(plan):
				return plan
			if unavailable_plan.is_empty():
				unavailable_plan = plan
	if not unavailable_plan.is_empty():
		if content_track == "revelation_packets_v1":
			var backup_plan := _build_backup_operation_plan(unavailable_plan)
			if not backup_plan.is_empty():
				return backup_plan
		return unavailable_plan
	return {}


func _build_backup_operation_plan(primary_plan: Dictionary) -> Dictionary:
	var backup_officer_id := _select_backup_officer_id(primary_plan)
	if backup_officer_id == "":
		return {}

	var backup := primary_plan.duplicate(true)
	var primary_officer_id := str(primary_plan.get("officer_id", ""))
	var primary_officer := _get_officer_state(primary_officer_id)
	var backup_officer := _get_officer_state(backup_officer_id)
	backup["backup_for"] = primary_officer_id
	backup["officer_id"] = backup_officer_id
	backup["officer_name"] = str(backup_officer.get("name", backup_officer_id))
	backup["primary_unavailable_name"] = str(primary_officer.get("name", primary_officer_id))
	backup["base_success"] = max(float(primary_plan.get("base_success", 0.6)) - float(primary_plan.get("backup_success_penalty", 0.08)), 0.05)
	if not backup.has("backup_intent"):
		backup["backup_intent"] = str(primary_plan.get("intent", primary_plan.get("tactical_step", "the squad reassigns the task")))
	return backup


func _select_backup_officer_id(primary_plan: Dictionary) -> String:
	var primary_officer_id := str(primary_plan.get("officer_id", ""))
	var skill_id := str(primary_plan.get("primary_skill", ""))
	var best_id := ""
	var best_score := -100000.0
	for officer_id_variant in officer_state.keys():
		var officer_id := str(officer_id_variant)
		if officer_id == "" or officer_id == primary_officer_id:
			continue
		var candidate := primary_plan.duplicate(true)
		candidate["officer_id"] = officer_id
		if not _is_operation_plan_available(candidate):
			continue
		var officer: Dictionary = officer_state.get(officer_id, {})
		var skills: Dictionary = officer.get("skills", {})
		var score := float(skills.get(skill_id, 8)) * 10.0
		score += float(officer.get("availability", 100))
		score += float(officer.get("morale", 70)) * 0.25
		score -= float(officer.get("stress", 0))
		score -= float(officer.get("fatigue", 0)) * 0.75
		score -= float(officer.get("injury", 0)) * 1.5
		score -= float(officer.get("contamination", 0))
		if score > best_score:
			best_score = score
			best_id = officer_id
	return best_id


func _build_symbiote_choice_buttons(event_data: Dictionary) -> Array:
	var buttons: Array = []
	var choices: Array[String] = _normalize_symbiote_choices(event_data.get("symbiote_choices", []))
	for symbiote_id in choices:
		if not symbiotes_by_id.has(symbiote_id):
			continue
		if owned_symbiotes.has(symbiote_id):
			continue
		var symbiote_data: Dictionary = symbiotes_by_id.get(symbiote_id, {})
		buttons.append({
			"label": _describe_symbiote_bond_label(symbiote_id, symbiote_data),
			"action": "take_symbiote:%s" % symbiote_id,
			"voice_aliases": _build_symbiote_voice_aliases(symbiote_id, symbiote_data)
		})

	var fallback_buttons = event_data.get("buttons", [])
	if fallback_buttons is Array:
		for button in fallback_buttons:
			if button is Dictionary:
				buttons.append(button.duplicate(true))

	if buttons.is_empty():
		buttons.append({
			"label": "Leave them",
			"action": "leave_symbiote",
			"voice_aliases": ["leave", "leave them", "walk away", "retreat", "decline"]
		})
	return buttons


func _append_symbiote_activation_buttons(buttons: Array, event_data: Dictionary) -> Array:
	var event_type := str(event_data.get("type", ""))
	if event_type == "merchant" or event_type == "symbiote":
		return buttons
	for symbiote_id in owned_symbiotes:
		if not _can_activate_symbiote(symbiote_id):
			continue
		var symbiote_data: Dictionary = symbiotes_by_id.get(symbiote_id, {})
		buttons.append({
			"label": "Activate: %s" % str(symbiote_data.get("name", symbiote_id)),
			"action": "activate_symbiote:%s" % symbiote_id,
			"voice_aliases": _build_symbiote_voice_aliases(symbiote_id, symbiote_data)
		})
	return buttons


func _build_symbiote_voice_aliases(symbiote_id: String, symbiote_data: Dictionary) -> Array[String]:
	var aliases: Array[String] = []
	match symbiote_id:
		"impermeable_barrier":
			aliases = ["barrier", "shield", "armor shield", "impermeable", "impenetrable", "impenetrible"]
		"pheromones":
			aliases = ["pheromones", "scent", "scent trail", "weaken enemies"]
		"mitosis_unit":
			aliases = ["mitosis", "split", "clone", "death save"]
		_:
			aliases = [symbiote_id.replace("_", " ")]

	var symbiote_name := str(symbiote_data.get("name", symbiote_id)).strip_edges().to_lower()
	if symbiote_name != "" and not aliases.has(symbiote_name):
		aliases.append(symbiote_name)

	return aliases


func _build_mutation_voice_aliases(mutation_id: String, mutation_data: Dictionary) -> Array[String]:
	var aliases: Array[String] = []
	var mutation_name := str(mutation_data.get("name", mutation_id)).strip_edges().to_lower()
	match mutation_id:
		_:
			aliases = ["buy", "purchase", "take mutation", "mutation", "claim"]

	if mutation_name != "" and not aliases.has(mutation_name):
		aliases.append(mutation_name)
	if mutation_id != "" and not aliases.has(mutation_id.replace("_", " ")):
		aliases.append(mutation_id.replace("_", " "))

	return aliases


func _default_proceed_button() -> Dictionary:
	return {
		"label": "Proceed.",
		"action": "proceed",
		"voice_aliases": ["proceed", "advance", "move on", "go forward", "step through"]
	}


func _can_activate_symbiote(symbiote_id: String) -> bool:
	if not symbiotes_by_id.has(symbiote_id):
		return false
	if int(symbiote_health.get(symbiote_id, 0)) <= 0:
		return false
	if symbiote_id == "mitosis_unit":
		return false
	if int(symbiote_cooldowns.get(symbiote_id, 0)) > 0:
		return false
	if active_symbiotes.has(symbiote_id):
		return false
	return true


func _describe_symbiote_bond_label(symbiote_id: String, symbiote_data: Dictionary) -> String:
	var symbiote_name := str(symbiote_data.get("name", symbiote_id))
	match symbiote_id:
		"impermeable_barrier":
			return "Bond: %s, armor shield" % symbiote_name
		"pheromones":
			return "Bond: %s, weaken enemies" % symbiote_name
		"mitosis_unit":
			return "Bond: %s, one death save" % symbiote_name
	return "Bond: %s" % symbiote_name


func _build_symbiote_activation_result(lines: Array[String]) -> Dictionary:
	var buttons: Array = [_default_proceed_button()]
	var event_data: Dictionary = current_encounter.get("event_data", {})
	if not event_data.is_empty() and not bool(current_encounter.get("consumed", false)) and not event_data.has("symbiote_choices"):
		buttons = _build_buttons(event_data)
	return {"lines": lines, "buttons": buttons}


func _get_enemy_tier() -> int:
	var pressure_tier_bonus := int(_get_pressure_count("avoid_combat") / 3)
	if _is_ending_locked("hunter"):
		pressure_tier_bonus += 1
	return int(max(1 + _merchant_triggered_at_rooms.size() + danger + pressure_tier_bonus, 1))


func _apply_enemy_tier(enemy_data: Dictionary) -> Dictionary:
	var tier := _get_enemy_tier()
	var tier_steps := tier - 1
	enemy_data["tier"] = tier
	enemy_data["armor"] = int(enemy_data.get("armor", 0))
	enemy_data["shield"] = int(enemy_data.get("shield", 0)) + tier_steps * 2
	enemy_data["damage"] = int(enemy_data.get("damage", 1)) + tier_steps
	enemy_data["health"] = int(enemy_data.get("health", 5)) + tier_steps * 5
	enemy_data["speed"] = float(enemy_data.get("speed", 1.0))
	enemy_data["visual_scale"] = 1.0 + float(tier_steps) * 0.12
	return enemy_data


func _resolve_enemy_data(event_data: Dictionary) -> Dictionary:
	var enemy_id := str(event_data.get("enemy_id", ""))
	if enemy_id == "":
		return {}
	var enemy_data: Dictionary = enemies_by_id.get(enemy_id, {}).duplicate(true)
	if enemy_data.is_empty():
		return {}
	return _apply_enemy_tier(enemy_data)


func _resolve_debrief_choice(action_id: String, event_data: Dictionary) -> Dictionary:
	var parts := action_id.split(":")
	if parts.size() < 3:
		return {}
	var index_text := str(parts[2])
	if not index_text.is_valid_int():
		return {}
	var index := int(index_text)
	var choices_variant = event_data.get("choices", [])
	var outcomes_variant = event_data.get("outcomes", [])
	if not choices_variant is Array or index < 0 or index >= choices_variant.size():
		return {}

	var choice_text := str(choices_variant[index]).strip_edges()
	var outcome_text := ""
	if outcomes_variant is Array and index < outcomes_variant.size():
		outcome_text = str(outcomes_variant[index]).strip_edges()
	var lines: Array[String] = []
	if choice_text != "":
		lines.append("Debrief decision filed: %s." % choice_text)
	if outcome_text != "":
		lines.append(outcome_text)
	else:
		lines.append("The debrief record is updated. Personnel respond in the next packet.")

	var result := {
		"lines": lines,
		"environment_state_changes": [
			{
				"key": "debrief.%s.choice" % str(event_data.get("id", "unknown")),
				"value": index
			}
		]
	}
	var effects_variant = event_data.get("choice_effects", [])
	if effects_variant is Array and index < effects_variant.size() and effects_variant[index] is Dictionary:
		var effects: Dictionary = effects_variant[index]
		for key in effects.keys():
			result[key] = effects[key]
	return result


func _resolve_artifact_option(action_id: String, event_data: Dictionary) -> Dictionary:
	var parts := action_id.split(":")
	if parts.size() < 3:
		return {}
	var artifact_id := str(parts[1])
	var index_text := str(parts[2])
	if artifact_id == "" or not owned_artifacts.has(artifact_id) or not index_text.is_valid_int():
		return {}
	var options_variant = event_data.get("artifact_options", [])
	var index := int(index_text)
	if not options_variant is Array or index < 0 or index >= options_variant.size():
		return {}
	if not options_variant[index] is Dictionary:
		return {}
	var option: Dictionary = options_variant[index]
	if str(option.get("artifact_id", "")) != artifact_id:
		return {}
	if not _artifact_option_state_matches(option):
		return {}

	var result: Dictionary = option.get("result", {}).duplicate(true) if option.get("result", {}) is Dictionary else {}
	if not result.has("lines"):
		var artifact_data: Dictionary = artifacts_by_id.get(artifact_id, {})
		result["lines"] = [
			"Artifact applied: %s." % str(artifact_data.get("name", artifact_id)),
			str(option.get("effect_line", "The custody item changes the available procedure."))
		]
	if bool(option.get("consume_artifact", false)):
		owned_artifacts.erase(artifact_id)
		environment_state["artifact.%s.consumed" % artifact_id] = true
	return result


func _apply_action_effects(action_id: String, event_data: Dictionary) -> Dictionary:
	if action_id.begins_with("debrief_choice:"):
		return _resolve_debrief_choice(action_id, event_data)
	if action_id.begins_with("use_artifact:"):
		return _resolve_artifact_option(action_id, event_data)
	if action_id.begins_with("take_symbiote:"):
		return _take_symbiote_from_event(action_id.substr("take_symbiote:".length()), event_data)

	match action_id:
		"take_mutation":
			var mutation_id := str(event_data.get("mutation_id", ""))
			if mutation_id != "" and owned_mutations.has(mutation_id):
				return {
					"lines": [
						"The mutation is already in me.",
						"I leave the growth twitching behind."
					]
				}
			if mutation_id != "" and not owned_mutations.has(mutation_id):
				owned_mutations.append(mutation_id)
			_add_corruption(1)
			return {
				"play_animation": "open",
				"lines": [
					"The flesh opens and the mutation takes hold.",
					"Corruption rises to %d." % corruption
				]
			}
		"take_symbiote":
			return _take_symbiote_from_event(str(event_data.get("symbiote_id", "")), event_data)
		"leave_symbiote":
			var remaining_symbiotes := _describe_symbiote_choices(_normalize_symbiote_choices(event_data.get("symbiote_choices", [])))
			return {
				"lines": [
					"I leave the host and its symbiotes behind.",
					"%s do not follow." % (remaining_symbiotes if remaining_symbiotes != "" else "They")
				]
			}
		"leave_mutation":
			return {
				"lines": [
					"I left the mutation where it twitched.",
					"I should keep moving."
				]
			}
		"drink_pool":
			var restored_health := _restore_player_health(int(event_data.get("heal", 8)))
			_add_corruption(1)
			return {
				"lines": [
					"The pool knits %d health back into place." % restored_health,
					"Something of it lingers. Corruption rises to %d." % corruption
				]
			}
		"study_pool":
			var reduced_corruption := _add_corruption(-1)
			return {
				"lines": [
					"I study the current instead of stepping into it.",
					"Corruption settles to %d." % reduced_corruption
				]
			}
		"retreat":
			return {
				"lines": [
					"I back away before the room can learn my shape.",
					"Better to keep moving."
				]
			}
		"harvest_eggs":
			_add_biomass(int(event_data.get("biomass", 5)))
			_add_corruption(1)
			return {
				"lines": [
					"I split the sacs and strip out fresh biomass.",
					"Biomass: %d. Corruption: %d." % [biomass, corruption]
				]
			}
		"cauterize_eggs":
			return _build_damage_result(int(event_data.get("damage", 6)), [
				"I burn a lane through the nest and the sacs burst against me."
			], "I make it through, singed but breathing.")
		"slip_between_eggs":
			return {
				"lines": [
					"I thread between the sacs and leave them unbroken.",
					"Nothing gained. Nothing owed."
				]
			}
		"inspect_cracked_egg":
			_add_biomass(int(event_data.get("biomass", 3)))
			return {
				"lines": [
					"I check the cracked shell and scrape warm residue from the split.",
					"Biomass: %d." % biomass
				]
			}
		"track_hatchling":
			var hatchling_damage := _apply_player_damage(int(event_data.get("damage", 3)))
			_add_biomass(int(event_data.get("biomass", 6)))
			_add_danger(1)
			return {
				"lines": [
					"I follow the drag marks until the hatchling doubles back.",
					_build_damage_summary(int(event_data.get("damage", 3)), hatchling_damage),
					"Biomass: %d. Danger rises to %d." % [biomass, danger]
				]
			}
		"siphon_amber":
			var amber_damage := _apply_player_damage(int(event_data.get("damage", 2)))
			_add_biomass(int(event_data.get("biomass", 7)))
			return {
				"lines": [
					"I carve amber clot from the wall and pocket the mass.",
					_build_damage_summary(int(event_data.get("damage", 2)), amber_damage),
					"Biomass: %d." % biomass
				]
			}
		"break_amber_cache":
			var cache_damage := _apply_player_damage(int(event_data.get("damage", 3)))
			_add_biomass(int(event_data.get("biomass", 5)))
			return {
				"lines": [
					"I crack the amber shell and pull the hard piece loose.",
					_build_damage_summary(int(event_data.get("damage", 3)), cache_damage),
					"Biomass: %d." % biomass
				]
			}
		"probe_amber_cache":
			var probed_shield := _restore_player_shield(int(event_data.get("shield", 2)))
			_add_danger(-1)
			return {
				"lines": [
					"I test the shell until it gives me a clean path around the pressure.",
					"Shield restored: %d. Danger settles to %d." % [probed_shield, danger]
				]
			}
		"seal_amber_wound":
			var restored_shield := _restore_player_shield(int(event_data.get("shield", 5)))
			_add_corruption(1)
			return {
				"lines": [
					"The amber hardens over me and restores %d shield." % restored_shield,
					"Corruption rises to %d." % corruption
				]
			}
		"leave_amber":
			return {
				"lines": [
					"I leave the amber sealed in the wall.",
					"It watches me go."
				]
			}
		"slip_green_spores":
			_add_danger(-1)
			return {
				"lines": [
					"I hold my breath and pass under the spore drift clean.",
					"Danger settles to %d." % danger
				]
			}
		"disturb_green_spores":
			var spore_heal := _restore_player_health(int(event_data.get("heal", 3)))
			_add_corruption(1)
			_add_danger(1)
			return {
				"lines": [
					"I stir the spores and let the green dust knit into the cuts.",
					"Health restored: %d. Corruption: %d. Danger: %d." % [spore_heal, corruption, danger]
				]
			}
		"take_green_tunnel":
			var green_heal := _restore_player_health(int(event_data.get("heal", 4)))
			_add_corruption(1)
			return {
				"lines": [
					"The soft tunnel carries me forward and mends %d health." % green_heal,
					"It leaves residue behind. Corruption: %d." % corruption
				]
			}
		"cut_green_spine":
			var green_damage := _apply_player_damage(int(event_data.get("damage", 4)))
			_add_biomass(int(event_data.get("biomass", 5)))
			return {
				"lines": [
					"I cut through the rigid spine and tear biomass free.",
					_build_damage_summary(int(event_data.get("damage", 4)), green_damage),
					"Biomass: %d." % biomass
				]
			}
		"listen_at_green_split":
			_add_danger(-1)
			return {
				"lines": [
					"I wait, listen, and pick the calmer pulse.",
					"Danger settles to %d." % danger
				]
			}
		"cut_red_wall":
			var wall_damage := _apply_player_damage(int(event_data.get("damage", 3)))
			_add_biomass(int(event_data.get("biomass", 4)))
			_add_corruption(1)
			return {
				"lines": [
					"I cut the breathing wall open before it can close around the blade.",
					_build_damage_summary(int(event_data.get("damage", 3)), wall_damage),
					"Biomass: %d. Corruption: %d." % [biomass, corruption]
				]
			}
		"listen_red_wall":
			_add_danger(-1)
			return {
				"lines": [
					"I tap once and wait until the corridor answers.",
					"Danger settles to %d." % danger
				]
			}
		"open_red_artery":
			_add_biomass(int(event_data.get("biomass", 6)))
			_add_corruption(1)
			return {
				"lines": [
					"I open the swollen artery and collect what spills out.",
					"Biomass: %d. Corruption: %d." % [biomass, corruption]
				]
			}
		"brace_through_red_split":
			return _build_damage_result(int(event_data.get("damage", 4)), [
				"I force the dry lane open with my body."
			], "The junction yields, but it costs me flesh.")
		"mark_red_branch":
			_add_danger(-1)
			return {
				"lines": [
					"I trace the pulse pattern and choose the safer branch.",
					"Danger settles to %d." % danger
				]
			}
		"rush_red_split":
			var rush_damage := _apply_player_damage(int(event_data.get("damage", 4)))
			_add_danger(1)
			return {
				"lines": [
					"I rush the split before the wall decides where to burst.",
					_build_damage_summary(int(event_data.get("damage", 4)), rush_damage),
					"Danger rises to %d." % danger
				]
			}
		"vent_red_split":
			var vent_damage := _apply_player_damage(int(event_data.get("damage", 2)))
			_add_biomass(int(event_data.get("biomass", 4)))
			_add_danger(-1)
			return {
				"lines": [
					"I cut a vent and let the pressure bleed out hot.",
					_build_damage_summary(int(event_data.get("damage", 2)), vent_damage),
					"Biomass: %d. Danger settles to %d." % [biomass, danger]
				]
			}
		"push_through_spikes":
			return _build_damage_result(int(event_data.get("damage", 8)), [
				"The corridor closes until I force myself through the spikes."
			], "The passage opens only after it has taken its cut.")
		"break_spike_lane":
			var spike_break_damage := int(event_data.get("break_damage", 5))
			var spike_damage := _apply_player_damage(spike_break_damage)
			_add_biomass(int(event_data.get("biomass", 4)))
			return {
				"lines": [
					"I break the spike line one joint at a time.",
					_build_damage_summary(spike_break_damage, spike_damage),
					"Biomass: %d." % biomass
				]
			}
		"observe_organ_chamber":
			var observed_shield := _restore_player_shield(int(event_data.get("shield", 3)))
			_add_danger(-1)
			return {
				"lines": [
					"I slow my breathing until the chamber loses the rhythm.",
					"Shield restored: %d. Danger settles to %d." % [observed_shield, danger]
				]
			}
		"cut_heart_cords":
			var cord_damage := _apply_player_damage(int(event_data.get("damage", 4)))
			_add_biomass(int(event_data.get("biomass", 6)))
			_add_corruption(1)
			return {
				"lines": [
					"I cut the hanging cords and catch what spills before it clots.",
					_build_damage_summary(int(event_data.get("damage", 4)), cord_damage),
					"Biomass: %d. Corruption: %d." % [biomass, corruption]
				]
			}
		"scavenge_bones":
			var bone_damage := _apply_player_damage(int(event_data.get("damage", 2)))
			_add_biomass(int(event_data.get("biomass", 5)))
			return {
				"lines": [
					"I strip the pile before the marrow nerves finish waking.",
					_build_damage_summary(int(event_data.get("damage", 2)), bone_damage),
					"Biomass: %d." % biomass
				]
			}
		"probe_bones":
			_add_danger(-1)
			return {
				"lines": [
					"I probe the heap from a distance and find the quiet route through.",
					"Danger settles to %d." % danger
				]
			}
		"disturb_pool":
			var pool_heal := _restore_player_health(int(event_data.get("heal", 10)))
			_add_corruption(2)
			return {
				"lines": [
					"I break the surface and let the pool answer first.",
					"Health restored: %d. Corruption rises to %d." % [pool_heal, corruption]
				]
			}
		"pay_resin_toll":
			var toll_cost := int(event_data.get("biomass_cost", 5))
			if biomass < toll_cost:
				merchant_claim += 1
				_add_danger(1)
				return {
					"lines": [
						"I press my palm to the resin slot. It wants %d biomass. I only have %d." % [toll_cost, biomass],
						"The slot closes on the debt. Claim: %d. Danger rises to %d." % [merchant_claim, danger]
					]
				}
			biomass -= toll_cost
			_add_danger(-1)
			return {
				"lines": [
					"I feed %d biomass into the amber toll and the corridor quiets." % toll_cost,
					"Biomass: %d. Danger settles to %d." % [biomass, danger]
				]
			}
		"skip_resin_toll":
			merchant_claim += 1
			_add_danger(1)
			return {
				"lines": [
					"I leave the toll hungry. Resin clicks behind me like teeth counting.",
					"Tally lines crawl under the plaque. Claim: %d. Danger rises to %d." % [merchant_claim, danger]
				]
			}
		"turn_baffle":
			baffle_mutes += 1
			var baffle_drop := 2 if baffle_mutes == 1 else 1
			_add_danger(-baffle_drop)
			var baffle_lines: Array[String] = [
				"I twist the baffle until the lane stops carrying my scent.",
				"Danger settles to %d." % danger
			]
			if baffle_mutes >= 2:
				if _enqueue_director_event_once("smother_hunter_arrival", "smother_hunter"):
					baffle_lines.append("The air stays too still behind me. Thin diaphragms tighten in the vents.")
			return {"lines": baffle_lines}
		"break_baffle":
			var baffle_damage := _apply_player_damage(int(event_data.get("damage", 2)))
			baffle_mutes = 0
			_add_biomass(int(event_data.get("biomass", 3)))
			_add_danger(1)
			return {
				"lines": [
					"I break the baffle wheel and tear out its wet hinge.",
					_build_damage_summary(int(event_data.get("damage", 2)), baffle_damage),
					"Biomass: %d. Danger rises to %d." % [biomass, danger]
				]
			}
		"follow_marked_plates":
			marked_route_streak += 1
			_add_danger(-1)
			var plate_lines: Array[String] = [
				"I follow the clean plate line and let the corridor think I obey.",
				"Danger settles to %d. Marked route streak: %d." % [danger, marked_route_streak]
			]
			if marked_route_streak >= 2:
				plate_lines.append("Minute teeth in the seams turn to match my stride.")
			if marked_route_streak >= 3:
				if _enqueue_director_event_once("plate_snare", "plate_snare"):
					plate_lines.append("The plates remember the shape of my steps.")
			return {"lines": plate_lines}
		"break_marked_pattern":
			var pattern_damage := _apply_player_damage(int(event_data.get("damage", 2)))
			marked_route_streak = 0
			_add_danger(-1)
			return {
				"lines": [
					"I step wrong on purpose and let the plates bite air.",
					_build_damage_summary(int(event_data.get("damage", 2)), pattern_damage),
					"Danger settles to %d. The marked streak breaks." % danger
				]
			}
		"leave_merchant":
			if _merchant_purchase_made:
				_merchant_purchase_made = false
				return {
					"lines": [
						"I leave with his bargain still moving under my skin.",
						"He lets the scale close."
					]
				}
			merchant_refusals += 1
			_add_danger(1)
			return {
				"lines": [
					"I leave the merchant to its clicking teeth.",
					"Danger rises to %d. He remembers the refusal." % danger
				]
			}
		"run":
			_add_danger(1)
			return {
				"lines": [
					"I run for the next chamber without looking back.",
					"Danger rises to %d." % danger
				]
			}
		"intercept":
			return {}
		"avoid":
			return {}
		"observe":
			return {}
		"destroy":
			return {}
		"dock":
			return {}
		"recover":
			return {}
		"quarantine":
			return {}
		"jettison":
			return {}
		"repair":
			return {}
		"reroute":
			return {}
		"seal":
			return {}
		"vent":
			return {}
		"ration":
			return {}
		"wake_officer":
			return {}
		"send_party":
			return {}
		"recall_party":
			return {}
		"brooks_handles":
			return {}
		"clear_iyad":
			return {}
		"clinic":
			return {}
		"continue_analysis":
			return {}
		"extend_eval":
			return {}
		"full_disclosure":
			return {}
		"hold_iyad":
			return {}
		"report_word_gap":
			return {}
		"return_ross":
			return {}
		"support_owen":
			return {}
		"torah_speaks":
			return {}
		"watch_quietly":
			return {}
		_:
			return {}

	return {}


func _with_director_lines(result: Dictionary, director_lines: Array[String]) -> Dictionary:
	if director_lines.is_empty():
		return result

	var updated := result.duplicate(true)
	var lines: Array = []
	var existing_lines = updated.get("lines", [])
	if existing_lines is Array:
		lines = existing_lines.duplicate()

	for line in director_lines:
		if line != "":
			lines.append(line)
	updated["lines"] = lines
	return updated


func _build_result_snapshot() -> Dictionary:
	return {
		"health": int(player_state.get("health", 0)),
		"shield": int(player_state.get("shield", 0)),
		"biomass": biomass,
		"danger": danger,
		"corruption": corruption,
		"merchant_claim": merchant_claim,
		"food": food,
		"fuel": fuel,
		"water": water,
		"crew_morale": crew_morale,
		"crew_unrest": crew_unrest,
		"revelation_pressure": revelation_pressure.duplicate(true)
	}


func _with_result_delta_lines(result: Dictionary, snapshot_before: Dictionary) -> Dictionary:
	var deltas: Array[String] = []
	_append_result_delta(deltas, "Health", snapshot_before, "health", int(player_state.get("health", 0)))
	_append_result_delta(deltas, "Shield", snapshot_before, "shield", int(player_state.get("shield", 0)))
	_append_result_delta(deltas, "Biomass", snapshot_before, "biomass", biomass)
	_append_result_delta(deltas, "Danger", snapshot_before, "danger", danger)
	_append_result_delta(deltas, "Corruption", snapshot_before, "corruption", corruption)
	_append_result_delta(deltas, "Claim", snapshot_before, "merchant_claim", merchant_claim)
	_append_result_delta(deltas, "Morale", snapshot_before, "crew_morale", crew_morale)
	_append_result_delta(deltas, "Unrest", snapshot_before, "crew_unrest", crew_unrest)
	_append_revelation_pressure_deltas(deltas, snapshot_before)
	if deltas.is_empty():
		return result

	var updated := result.duplicate(true)
	var lines: Array = []
	var existing_lines = updated.get("lines", [])
	if existing_lines is Array:
		lines = existing_lines.duplicate()
	lines.append("Result: %s." % ". ".join(deltas))
	updated["lines"] = lines
	return updated


func _append_result_delta(deltas: Array[String], label: String, snapshot_before: Dictionary, key: String, current_value: int) -> void:
	var previous_value := int(snapshot_before.get(key, current_value))
	var delta := current_value - previous_value
	if delta == 0:
		return
	deltas.append("%s %s" % [label, _format_signed_delta(delta)])


func _append_revelation_pressure_deltas(deltas: Array[String], snapshot_before: Dictionary) -> void:
	if content_track != "revelation_packets_v1":
		return
	var previous_pressure: Dictionary = snapshot_before.get("revelation_pressure", {})
	for pressure_id in REVELATION_PRESSURE_DEFAULTS.keys():
		var previous_value := int(previous_pressure.get(pressure_id, int(REVELATION_PRESSURE_DEFAULTS.get(pressure_id, 0))))
		var current_value := int(revelation_pressure.get(pressure_id, previous_value))
		var delta := current_value - previous_value
		if delta == 0:
			continue
		deltas.append(_revelation_pressure_delta_phrase(str(pressure_id), delta))


func _revelation_pressure_delta_phrase(pressure_id: String, delta: int) -> String:
	var rising := delta > 0
	match pressure_id:
		"institute_scrutiny":
			return "command review tightens" if rising else "command review eases"
		"squad_cohesion":
			return "squad steadies" if rising else "squad trust thins"
		"public_exposure":
			return "civilian attention spreads" if rising else "public noise recedes"
		"symbolic_contamination":
			return "symbolic residue deepens" if rising else "symbolic residue clears"
		"artifact_burden":
			return "custody weight increases" if rising else "custody weight eases"
		"doctrine_fracture":
			return "doctrine strain widens" if rising else "doctrine strain narrows"
		"casualty_strain":
			return "clinic load worsens" if rising else "clinic load eases"
		"closure_debt":
			return "closure debt grows" if rising else "closure debt recedes"
	return "%s shifts" % str(REVELATION_PRESSURE_LABELS.get(pressure_id, pressure_id))


func _format_signed_delta(delta: int) -> String:
	if delta > 0:
		return "+%d" % delta
	return "%d" % delta


func _apply_event_action_result(action_id: String, event_data: Dictionary, base_result: Dictionary) -> Dictionary:
	var action_result := _resolve_operation_action_result(action_id, event_data)
	if action_result.is_empty():
		action_result = _get_event_action_result(action_id, event_data)
	if action_result.is_empty():
		return base_result

	var updated := base_result.duplicate(true)
	var override_lines := _normalize_string_array(action_result.get("lines", []))
	if not override_lines.is_empty():
		updated["lines"] = override_lines
	if action_result.has("_tts_operation_band"):
		updated["_tts_operation_band"] = str(action_result.get("_tts_operation_band", ""))
	return _apply_structured_action_effects(action_id, event_data, action_result, updated)


func _apply_structured_action_effects(action_id: String, event_data: Dictionary, action_result: Dictionary, result: Dictionary) -> Dictionary:
	if action_result.is_empty():
		return result

	var effect := _with_revelation_pressure_changes(action_id, event_data, action_result)
	_apply_resource_changes(effect.get("resource_changes", {}))
	_apply_environment_state_changes(effect.get("environment_state_changes", []))
	var memory_changes := _normalize_string_array(effect.get("environment_memory_flags", []))
	for state_key in memory_changes:
		environment_state[state_key] = true
	_apply_operation_state_changes(effect.get("stress_changes", []))
	_apply_revelation_pressure_changes(effect.get("pressure_changes", {}))

	var updated := result.duplicate(true)
	_append_result_lines(updated, _apply_artifact_rewards(effect.get("artifact_rewards", [])))
	return updated


func _with_revelation_pressure_changes(action_id: String, event_data: Dictionary, action_result: Dictionary) -> Dictionary:
	if content_track != "revelation_packets_v1":
		return action_result

	var updated := action_result.duplicate(true)
	var combined := _normalize_pressure_changes(action_result.get("pressure_changes", {}))
	var inferred := _infer_revelation_pressure_changes(action_id, event_data, action_result)
	for pressure_id in inferred.keys():
		combined[pressure_id] = int(combined.get(pressure_id, 0)) + int(inferred.get(pressure_id, 0))
	if not combined.is_empty():
		updated["pressure_changes"] = combined
	return updated


func _infer_revelation_pressure_changes(action_id: String, event_data: Dictionary, action_result: Dictionary) -> Dictionary:
	var changes: Dictionary = {}
	var base_action := _base_action_id(action_id)
	var event_type := str(event_data.get("type", ""))
	var event_id := str(event_data.get("id", ""))
	var state_keys := _normalize_string_array(action_result.get("environment_state_changes", []))
	var outcome_text := " ".join(state_keys).to_lower()

	if outcome_text.contains(".failure") or outcome_text.contains("failure"):
		_add_pressure_change(changes, "closure_debt", 2)
		_add_pressure_change(changes, "institute_scrutiny", 1)
		_add_pressure_change(changes, "casualty_strain", 1)
	elif outcome_text.contains(".partial") or outcome_text.contains("partial"):
		_add_pressure_change(changes, "closure_debt", 1)
		_add_pressure_change(changes, "institute_scrutiny", 1)
	elif outcome_text.contains(".success") or outcome_text.contains("success"):
		if event_type == "resolution" or event_id.begins_with("resolution_"):
			_add_pressure_change(changes, "closure_debt", -1)

	if _has_artifact_rewards(action_result):
		_add_pressure_change(changes, "artifact_burden", 1)

	match base_action:
		"intercept", "destroy", "breach", "hard_shutdown", "evacuate":
			_add_pressure_change(changes, "casualty_strain", 1)
		"torah_speaks", "use_artifact":
			_add_pressure_change(changes, "symbolic_contamination", 1)
		"full_disclosure", "report_word_gap", "return_ross":
			_add_pressure_change(changes, "institute_scrutiny", 1)
			_add_pressure_change(changes, "doctrine_fracture", 1)
		"concede", "hold_line", "hold_iyad", "support_owen":
			_add_pressure_change(changes, "squad_cohesion", 1)
		"watch_quietly", "extend_eval":
			_add_pressure_change(changes, "squad_cohesion", -1)

	var resource_changes_variant = action_result.get("resource_changes", {})
	if resource_changes_variant is Dictionary:
		var resource_changes: Dictionary = resource_changes_variant
		for key_variant in resource_changes.keys():
			var key := str(key_variant)
			var delta := _resource_delta_from_value(resource_changes.get(key_variant))
			if key.begins_with("character.") and (key.ends_with(".stress") or key.ends_with(".fatigue") or key.ends_with(".injury")) and delta > 0:
				_add_pressure_change(changes, "casualty_strain", 1)
			if key.begins_with("character.") and key.ends_with(".morale") and delta > 0:
				_add_pressure_change(changes, "squad_cohesion", 1)
	return changes


func _normalize_pressure_changes(changes_variant: Variant) -> Dictionary:
	var changes: Dictionary = {}
	if changes_variant is Dictionary:
		var raw_changes: Dictionary = changes_variant
		for key_variant in raw_changes.keys():
			var pressure_id := str(key_variant)
			var amount := _resource_delta_from_value(raw_changes.get(key_variant))
			_add_pressure_change(changes, pressure_id, amount)
	elif changes_variant is Array:
		for change_variant in changes_variant:
			if not change_variant is Dictionary:
				continue
			var change: Dictionary = change_variant
			var pressure_id := str(change.get("id", change.get("key", "")))
			var amount := _resource_delta_from_value(change.get("amount", change.get("delta", 0)))
			_add_pressure_change(changes, pressure_id, amount)
	return changes


func _add_pressure_change(changes: Dictionary, pressure_id: String, amount: int) -> void:
	if amount == 0 or not REVELATION_PRESSURE_DEFAULTS.has(pressure_id):
		return
	changes[pressure_id] = int(changes.get(pressure_id, 0)) + amount


func _has_artifact_rewards(action_result: Dictionary) -> bool:
	var rewards_variant = action_result.get("artifact_rewards", [])
	if rewards_variant is String:
		return str(rewards_variant).strip_edges() != ""
	if rewards_variant is Array:
		return not rewards_variant.is_empty()
	if rewards_variant is Dictionary:
		return not rewards_variant.is_empty()
	return false


func _apply_revelation_pressure_changes(changes_variant: Variant) -> void:
	if content_track != "revelation_packets_v1":
		return
	var changes := _normalize_pressure_changes(changes_variant)
	for pressure_id in changes.keys():
		var current := int(revelation_pressure.get(pressure_id, int(REVELATION_PRESSURE_DEFAULTS.get(pressure_id, 0))))
		var next_value := int(clamp(current + int(changes.get(pressure_id, 0)), 0, 10))
		revelation_pressure[pressure_id] = next_value
		_apply_revelation_pressure_side_effect(pressure_id, current, next_value)


func _apply_revelation_pressure_side_effect(pressure_id: String, previous_value: int, next_value: int) -> void:
	if next_value == previous_value:
		return
	if next_value >= 3 and previous_value < 3:
		environment_state["pressure.%s.watch" % pressure_id] = true
		_queue_revelation_pressure_story_trigger(pressure_id, "watch")
	if next_value >= 7 and previous_value < 7:
		environment_state["pressure.%s.high" % pressure_id] = true
		_queue_revelation_pressure_story_trigger(pressure_id, "high")
	if next_value >= 9 and previous_value < 9:
		environment_state["pressure.%s.critical" % pressure_id] = true
		_queue_revelation_pressure_story_trigger(pressure_id, "critical")
	match pressure_id:
		"squad_cohesion":
			if next_value <= 2 and previous_value > 2:
				_add_crew_unrest(1)
				_queue_revelation_pressure_story_trigger(pressure_id, "low")
			elif next_value >= 8 and previous_value < 8:
				_add_crew_morale(1)
		"institute_scrutiny":
			if next_value >= 7 and previous_value < 7:
				_add_crew_unrest(1)
		"casualty_strain":
			if next_value >= 7 and previous_value < 7:
				_add_crew_morale(-1)


func _queue_revelation_pressure_story_trigger(pressure_id: String, threshold: String) -> void:
	var event_id := _revelation_pressure_story_event_id(pressure_id)
	if event_id == "":
		return
	var trigger_key := "revelation_pressure:%s:%s" % [pressure_id, threshold]
	_queue_story_event_once(event_id, trigger_key, 0)


func _revelation_pressure_story_event_id(pressure_id: String) -> String:
	match pressure_id:
		"institute_scrutiny", "doctrine_fracture":
			return "pressure_command_review"
		"artifact_burden":
			return "pressure_artifact_custody"
		"symbolic_contamination":
			return "pressure_symbolic_contamination"
		"squad_cohesion":
			return "pressure_squad_fracture"
		"closure_debt":
			return "pressure_closure_debt"
		"casualty_strain":
			return "pressure_clinic"
		"public_exposure":
			return "pressure_public_exposure"
	return ""


func _append_result_lines(result: Dictionary, extra_lines: Array[String]) -> void:
	if extra_lines.is_empty():
		return
	var lines: Array = []
	var existing_lines = result.get("lines", [])
	if existing_lines is Array:
		lines = existing_lines.duplicate()
	for line in extra_lines:
		if line != "":
			lines.append(line)
	result["lines"] = lines


func _apply_artifact_rewards(rewards_variant: Variant) -> Array[String]:
	var rewards: Array[String] = []
	if rewards_variant is String:
		rewards.append(str(rewards_variant))
	elif rewards_variant is Array:
		for reward_variant in rewards_variant:
			if reward_variant is Dictionary:
				var reward_id := str(reward_variant.get("id", reward_variant.get("artifact_id", ""))).strip_edges()
				if reward_id != "":
					rewards.append(reward_id)
			else:
				var reward_id := str(reward_variant).strip_edges()
				if reward_id != "":
					rewards.append(reward_id)
	elif rewards_variant is Dictionary:
		var reward_id := str(rewards_variant.get("id", rewards_variant.get("artifact_id", ""))).strip_edges()
		if reward_id != "":
			rewards.append(reward_id)

	var lines: Array[String] = []
	for artifact_id in rewards:
		if owned_artifacts.has(artifact_id):
			continue
		owned_artifacts.append(artifact_id)
		environment_state["artifact.%s.acquired" % artifact_id] = true
		var artifact_data: Dictionary = artifacts_by_id.get(artifact_id, {})
		var artifact_name := str(artifact_data.get("name", artifact_id))
		lines.append("Custody item secured: %s." % artifact_name)
	return lines


func _apply_environment_state_changes(changes_variant: Variant) -> void:
	if not changes_variant is Array:
		return
	for change_variant in changes_variant:
		if change_variant is Dictionary:
			_apply_structured_environment_change(change_variant)
			continue
		var state_key := str(change_variant)
		if state_key != "":
			if _apply_text_environment_state_change(state_key):
				continue
			environment_state[state_key] = true
			_apply_environment_state_effect(state_key)


func _apply_resource_changes(changes_variant: Variant) -> void:
	if not changes_variant is Dictionary:
		return
	var changes: Dictionary = changes_variant
	for key_variant in changes.keys():
		var key := str(key_variant)
		var delta := _resource_delta_from_value(changes.get(key_variant))
		if delta == 0:
			continue
		match key:
			"food", "resource.food", "resources.food":
				_add_food(delta)
			"fuel", "resource.fuel", "resources.fuel":
				_add_fuel(delta)
			"water", "resource.water", "resources.water":
				_add_water(delta)
			"morale", "crew_morale", "squad.morale", "crew.morale":
				_add_crew_morale(delta)
			"unrest", "crew_unrest", "squad.refusal_risk", "squad.mutiny_risk", "crew.unrest":
				_add_crew_unrest(delta)


func _apply_structured_environment_change(change: Dictionary) -> void:
	var key := str(change.get("key", change.get("state_key", "")))
	if key == "":
		return

	if key.begins_with("character.") and change.has("value"):
		var key_parts := key.split(".")
		if key_parts.size() >= 3:
			var character_id := str(key_parts[1])
			var field := str(key_parts[2])
			if officer_state.has(character_id):
				var character: Dictionary = officer_state.get(character_id, {})
				character[field] = change.get("value")
				officer_state[character_id] = character
				environment_state["%s_set" % key] = true
				return

	var delta := int(change.get("delta", 0))
	if delta != 0:
		_apply_environment_delta(key, delta)
		environment_state["%s_delta_%s%d" % [key, "plus" if delta > 0 else "minus", abs(delta)]] = true
		return

	if change.has("value"):
		var value: Variant = change.get("value")
		if value is bool and not value:
			environment_state.erase(key)
			environment_state["%s_false" % key] = true
			return
		environment_state[key] = value
		environment_state["%s_set" % key] = true
		return

	environment_state[key] = true
	_apply_environment_state_effect(key)


func _apply_text_environment_state_change(raw_state: String) -> bool:
	var text := raw_state.strip_edges()
	var separator_index := text.find(":")
	if separator_index <= 0:
		return false

	var key := text.substr(0, separator_index).strip_edges()
	var value_text := text.substr(separator_index + 1).strip_edges()
	if key == "":
		return false

	var key_parts := key.split(".")
	var character_id := ""
	var field := ""
	if key_parts.size() >= 3 and str(key_parts[0]) == "character":
		character_id = str(key_parts[1])
		field = str(key_parts[2])
	elif key_parts.size() >= 2:
		character_id = str(key_parts[0])
		field = str(key_parts[1])

	if character_id == "" or field == "" or not officer_state.has(character_id):
		environment_state[key] = value_text
		environment_state["%s_set" % key] = true
		return true

	var officer: Dictionary = officer_state.get(character_id, {})
	officer[field] = _coerce_officer_state_value(field, value_text, officer.get(field))
	officer_state[character_id] = officer
	environment_state[key] = value_text
	environment_state["%s_set" % key] = true
	return true


func _coerce_officer_state_value(field: String, value_text: String, fallback: Variant) -> Variant:
	var lower := value_text.to_lower()
	var first_token := str(lower.split(" ", false)[0]).strip_edges().trim_suffix(",")
	if first_token.is_valid_int():
		return int(first_token)

	match field:
		"availability":
			if lower.contains("suspended") or lower.contains("unavailable") or lower.contains("withdrawn"):
				return 0
			if lower.contains("restricted") or lower.contains("limited"):
				return 20
			if lower.contains("available") or lower.contains("cleared") or lower.contains("restored"):
				return 100
			return fallback
		"injury", "stress", "fatigue", "contamination":
			if lower.contains("critical"):
				return 90
			if lower.contains("severe"):
				return 75
			if lower.contains("high"):
				return 55
			if lower.contains("elevated") or lower.contains("moderate"):
				return 35
			if lower.contains("minor") or lower.contains("low"):
				return 20
			if lower.contains("clear") or lower.contains("none"):
				return 0
			return fallback
		"morale", "loyalty":
			if lower.contains("reduced") or lower.contains("conditional"):
				return 45
			if lower.contains("stable") or lower.contains("steady"):
				return 70
			if lower.contains("vindicated") or lower.contains("improved"):
				return 78
			return fallback
		"mental_state":
			for state in ["dissociated", "ritualizing", "withdrawn", "fixated", "strained", "spooked", "angry", "defiant", "recovering", "unfit", "steady"]:
				if lower.contains(state):
					return state
			return value_text
	return value_text


func _apply_environment_delta(key: String, delta: int) -> void:
	if key.begins_with("character."):
		var key_parts := key.split(".")
		if key_parts.size() >= 3:
			var character_id := str(key_parts[1])
			var field := str(key_parts[2])
			if officer_state.has(character_id):
				var minimum := 0
				var maximum := 100
				if field == "stress" or field == "fatigue" or field == "injury" or field == "contamination":
					minimum = 0
					maximum = 100
				_apply_record_delta(officer_state, "character", character_id, field, delta, minimum, maximum)
				return

	match key:
		"resource.food", "resources.food":
			_add_food(delta)
		"resource.fuel", "resources.fuel":
			_add_fuel(delta)
		"resource.water", "resources.water":
			_add_water(delta)
		"medical.fatigue":
			_apply_record_delta(department_state, "department", "medical", "fatigue", delta, 0, 100)
		"systems.overstrain":
			_apply_record_delta(ship_system_state, "system", "containment_seals", "stress", delta * 8, 0, 100)
		"squad.morale", "crew.morale":
			_add_crew_morale(delta)
		"squad.refusal_risk", "squad.mutiny_risk", "crew.unrest":
			_add_crew_unrest(delta)
		"discipline.fracture_risk", "navigation.uncertainty", "crew.tension_science_engineering":
			_add_danger(max(delta, 0))


func _resolve_operation_action_result(action_id: String, event_data: Dictionary) -> Dictionary:
	var plan := _operation_plan_for_action(action_id, event_data)
	if plan.is_empty():
		return {}

	var chance := _calculate_operation_chance(plan)
	var roll := _rng.randf()
	var band := _operation_band_for_roll(chance, roll, plan)
	var outcome := _operation_outcome_for_band(plan, band)
	if outcome.is_empty():
		return {}

	var result := outcome.duplicate(true)
	result["_tts_operation_band"] = band
	if ["success", "strong_success"].has(band):
		var success_action_result := _get_event_action_result(action_id, event_data)
		if success_action_result.has("artifact_rewards") and not result.has("artifact_rewards"):
			result["artifact_rewards"] = success_action_result.get("artifact_rewards", [])
	var stress_changes: Array = []
	var plan_stress = plan.get("stress_targets", [])
	if plan_stress is Array:
		stress_changes.append_array(plan_stress)
	var outcome_stress = result.get("stress_changes", [])
	if outcome_stress is Array:
		stress_changes.append_array(outcome_stress)
	result["stress_changes"] = stress_changes

	var flags := _normalize_string_array(result.get("operation_state_changes", []))
	flags.append("operation_%s_%s" % [str(plan.get("action", action_id)), band])
	for flag in flags:
		environment_state[flag] = true

	return result


func _calculate_operation_chance(plan: Dictionary) -> float:
	var chance := float(plan.get("base_success", 0.6))
	var skill_id := str(plan.get("primary_skill", ""))
	var officer := _get_officer_state(str(plan.get("officer_id", "")))
	if not officer.is_empty() and skill_id != "":
		var skills: Dictionary = officer.get("skills", {})
		var skill_value := float(skills.get(skill_id, 10))
		chance += (skill_value - 10.0) * 0.018
		chance -= float(officer.get("stress", 0)) * 0.0025
		chance -= float(officer.get("fatigue", 0)) * 0.0015
		chance -= float(officer.get("injury", 0)) * 0.003
		chance -= float(officer.get("contamination", 0)) * 0.002
		chance += (float(officer.get("morale", 70)) - 70.0) * 0.0015
		chance += (float(officer.get("availability", 100)) - 100.0) * 0.002
		chance += _mental_state_chance_modifier(str(officer.get("mental_state", "steady")))

	var department := _get_department_state(str(plan.get("department_id", "")))
	if not department.is_empty():
		chance -= float(department.get("stress", 0)) * 0.0018
		chance -= float(department.get("fatigue", 0)) * 0.0012
		chance -= float(department.get("casualties", 0)) * 0.015
		chance -= float(department.get("contamination", 0)) * 0.002

	var ship_system := _get_ship_system_state(str(plan.get("system_id", "")))
	if not ship_system.is_empty():
		chance += (float(ship_system.get("condition", 75)) - 75.0) * 0.001
		chance -= float(ship_system.get("stress", 0)) * 0.0018
		chance -= float(ship_system.get("anomaly", 0)) * 0.002

	for state_bonus_variant in plan.get("state_bonuses", []):
		if not state_bonus_variant is Dictionary:
			continue
		var state_bonus: Dictionary = state_bonus_variant
		var state_key := str(state_bonus.get("state_key", ""))
		if state_key != "" and environment_state.has(state_key):
			chance += float(state_bonus.get("chance_delta", 0.0))

	chance -= float(plan.get("hazard", 0.0))
	return clamp(chance, 0.05, 0.95)


func _is_operation_plan_available(plan: Dictionary) -> bool:
	var officer_id := str(plan.get("officer_id", ""))
	if officer_id == "":
		return true
	var officer := _get_officer_state(officer_id)
	if officer.is_empty():
		return false
	if int(officer.get("availability", 100)) < int(plan.get("minimum_availability", 25)):
		return false
	if int(officer.get("injury", 0)) >= int(plan.get("maximum_injury", 90)):
		return false
	if int(officer.get("contamination", 0)) >= int(plan.get("maximum_contamination", 95)):
		return false
	var mental_state := str(officer.get("mental_state", "steady"))
	var blocked_states: Array[String] = _normalize_string_array(plan.get("blocked_mental_states", ["unfit", "dissociated"]))
	return not blocked_states.has(mental_state)


func _mental_state_chance_modifier(mental_state: String) -> float:
	match mental_state:
		"steady":
			return 0.04
		"recovering":
			return 0.02
		"strained":
			return -0.03
		"spooked":
			return -0.05
		"fixated":
			return -0.04
		"withdrawn":
			return -0.06
		"angry":
			return -0.04
		"dissociated":
			return -0.12
		"ritualizing":
			return -0.08
		"defiant":
			return -0.03
		"unfit":
			return -0.18
	return 0.0


func _operation_band_for_roll(chance: float, roll: float, plan: Dictionary) -> String:
	var margin := chance - roll
	var outcomes: Dictionary = plan.get("outcomes", {})
	if margin >= 0.25 and outcomes.has("strong_success"):
		return "strong_success"
	if margin >= 0.0:
		return "success"
	if margin >= -0.15 and outcomes.has("partial"):
		return "partial"
	if margin <= -0.35 and outcomes.has("catastrophe"):
		return "catastrophe"
	return "failure"


func _operation_outcome_for_band(plan: Dictionary, band: String) -> Dictionary:
	var outcomes_variant = plan.get("outcomes", {})
	if not outcomes_variant is Dictionary:
		return {}
	var outcomes: Dictionary = outcomes_variant
	for key in [band, "success", "partial", "failure"]:
		if outcomes.has(key) and outcomes[key] is Dictionary:
			return outcomes[key].duplicate(true)
	return {}


func _apply_operation_state_changes(changes_variant: Variant) -> void:
	if not changes_variant is Array:
		return
	for change_variant in changes_variant:
		if not change_variant is Dictionary:
			continue
		var change: Dictionary = change_variant
		var target_type := str(change.get("type", ""))
		var target_id := str(change.get("id", ""))
		var field := str(change.get("field", "stress"))
		var amount := _operation_change_amount(change.get("amount", 0))
		match target_type:
			"officer":
				_apply_record_delta(officer_state, target_type, target_id, field, amount, 0, 100)
			"department":
				_apply_record_delta(department_state, target_type, target_id, field, amount, 0, 100)
			"system":
				_apply_record_delta(ship_system_state, target_type, target_id, field, amount, 0, 100)


func _operation_change_amount(amount_variant: Variant) -> int:
	if amount_variant is Array and amount_variant.size() >= 2:
		return _rng.randi_range(int(amount_variant[0]), int(amount_variant[1]))
	return int(amount_variant)


func _apply_record_delta(records: Dictionary, target_type: String, record_id: String, field: String, amount: int, minimum: int, maximum: int) -> void:
	if record_id == "" or not records.has(record_id):
		return
	var record: Dictionary = records.get(record_id, {})
	var previous := int(record.get(field, 0))
	var next_value := int(clamp(previous + amount, minimum, maximum))
	record[field] = next_value
	records[record_id] = record
	_queue_pressure_story_trigger(target_type, record_id, field, previous, next_value)


func _queue_pressure_story_trigger(target_type: String, record_id: String, field: String, previous: int, next_value: int) -> void:
	if not ["stress", "fatigue"].has(field) or previous >= 25 or next_value < 25:
		return

	var event_id := _pressure_story_event_id(target_type, record_id)
	if event_id == "":
		return

	var trigger_key := "pressure_story:%s:%s:%s" % [target_type, record_id, field]
	_queue_story_event_once(event_id, trigger_key, 1)


func _queue_resource_story_triggers() -> void:
	if not _is_revelation_content_track() and water <= 3:
		_queue_story_event_once("story_water_ration_dispute", "resource:water_low", 1)
	if not _is_revelation_content_track() and food <= 3:
		_queue_story_event_once("story_food_store_shortfall", "resource:food_low", 1)
	if not _is_revelation_content_track() and fuel <= 3:
		_queue_story_event_once("story_fuel_trim_argument", "resource:fuel_low", 1)
	if crew_unrest >= 3 or crew_morale <= 3:
		_queue_story_event_once("story_crew_section_refusal", "crew:section_refusal", 1)
	if crew_unrest >= 5 or crew_morale <= 1:
		_queue_story_event_once("story_mutiny_concession_demand", "crew:mutiny_demand", 1)


func _is_revelation_content_track() -> bool:
	return content_track == "revelation_packets_v1"


func _pressure_story_event_id(target_type: String, record_id: String) -> String:
	match [target_type, record_id]:
		["department", "engineering_crews"]:
			return "story_engineering_overstrain"
		["system", "pressure_manifold"]:
			return "story_pressure_manifold_strain"
		["department", "medical_ward"]:
			return "story_medical_quarantine_fatigue"
		["system", "quarantine_screens"]:
			return "story_quarantine_watch_failure"
	return ""


func _queue_story_event_once(event_id: String, trigger_key: String, delay_rooms: int) -> bool:
	if event_id == "" or not special_events.has(event_id):
		return false
	if trigger_key == "":
		trigger_key = event_id
	if _triggered_story_events.has(trigger_key):
		return false

	_triggered_story_events[trigger_key] = true
	if not _pending_story_event_ids().has(event_id):
		_pending_story_events.append({
			"event_id": event_id,
			"available_after_rooms": _story_event_available_after(delay_rooms, false)
		})
	return true


func _get_officer_state(officer_id: String) -> Dictionary:
	if officer_id == "":
		return {}
	return officer_state.get(officer_id, {})


func _get_department_state(department_id: String) -> Dictionary:
	if department_id == "":
		return {}
	return department_state.get(department_id, {})


func _get_ship_system_state(system_id: String) -> Dictionary:
	if system_id == "":
		return {}
	return ship_system_state.get(system_id, {})


func _condition_for_record(record: Dictionary) -> String:
	if record.is_empty():
		return "unknown"
	var pressure: int = max(int(record.get("stress", 0)), int(record.get("fatigue", 0)), int(record.get("anomaly", 0)), int(record.get("contamination", 0)))
	if pressure >= 90:
		return "crisis"
	if pressure >= 75:
		return "breaking"
	if pressure >= 50:
		return "unstable"
	if pressure >= 25:
		return "strained"
	return "steady"


func _apply_event_memory_flags(event_data: Dictionary) -> void:
	for state_key in _normalize_string_array(event_data.get("environment_memory_flags", [])):
		environment_state[state_key] = true


func _apply_environment_state_effect(state_key: String) -> void:
	match state_key:
		"merchant_claim_up":
			merchant_claim += 1
		"merchant_claim_down":
			merchant_claim = max(merchant_claim - 1, 0)
		"pursuit_pressure_plus_one", "attention_tick", "global_attention_trade_up":
			_add_danger(1)
		"heal_instability_push":
			_add_corruption(1)
		"morale_minus_one", "morale_tick_minus1", "science_morale_tick_minus1", "morale_strain_quarantine_policy", "crew_pantries_morgue_slang", "quartermaster_resentment_plus_one", "discard_crate_theft_found", "marked_water_continues":
			_add_crew_morale(-1)
		"mess_accepts_salvage_law", "morale_recovers_after_waste_argument", "ward_cases_contained":
			_add_crew_morale(1)
		"crew_section_refusal", "watch_refuses_work", "mutiny_pressure_plus_one":
			_add_crew_unrest(1)


func _get_event_action_result(action_id: String, event_data: Dictionary) -> Dictionary:
	var action_results_variant = event_data.get("action_results", {})
	if not action_results_variant is Dictionary:
		return {}

	var action_results: Dictionary = action_results_variant
	var base_action := _base_action_id(action_id)
	for key in [action_id, base_action, "default"]:
		if action_results.has(key) and action_results[key] is Dictionary:
			return action_results[key].duplicate(true)
	return {}


func _record_action_pattern(action_id: String, event_data: Dictionary) -> Array[String]:
	var base_action := _base_action_id(action_id)
	var event_type := str(event_data.get("type", ""))
	var axes: Array[String] = []

	if (event_type == "combat" or event_type == "boss") and ["proceed", "run", "retreat"].has(base_action):
		_add_pressure_axis(axes, "avoid_combat")
		_add_pressure_axis(axes, "danger")
		if base_action == "proceed":
			_add_danger(1)

	match base_action:
		"combat":
			_add_pressure_axis(axes, "combat")
		"take_mutation", "buy_mutation":
			_add_pressure_axis(axes, "corruption")
		"take_symbiote", "activate_symbiote":
			_add_pressure_axis(axes, "dependence")
		"drink_pool", "disturb_pool", "seal_amber_wound", "take_green_tunnel", "disturb_green_spores", "harvest_eggs", "open_red_artery", "cut_red_wall", "cut_heart_cords":
			_add_pressure_axis(axes, "corruption")
		"run", "leave_merchant", "track_hatchling", "rush_red_split", "disturb_green_spores":
			_add_pressure_axis(axes, "danger")
		"skip_resin_toll", "break_baffle":
			_add_pressure_axis(axes, "danger")
			_add_pressure_axis(axes, "debt")
		"retreat":
			_add_pressure_axis(axes, "safety")
			_add_pressure_axis(axes, "danger")
			_add_danger(1)
		"harvest_eggs", "siphon_amber", "overdraw_amber", "break_amber_cache", "inspect_cracked_egg", "scavenge_bones", "open_red_artery", "cut_green_spine", "cut_red_wall", "vent_red_split", "cut_heart_cords":
			_add_pressure_axis(axes, "greed")
		"pay_resin_toll", "turn_baffle", "follow_marked_plates":
			_add_pressure_axis(axes, "safety")
		"study_pool", "listen_at_green_split", "mark_red_branch", "listen_red_wall", "probe_amber_cache", "slip_green_spores", "probe_bones", "observe_organ_chamber", "leave_amber", "leave_symbiote", "leave_mutation", "slip_between_eggs", "break_marked_pattern":
			_add_pressure_axis(axes, "safety")

	var lines: Array[String] = []
	for axis in axes:
		var count := _increment_pressure(axis)
		for line in _evaluate_pressure_axis(axis, count):
			lines.append(line)
	return lines


func _base_action_id(action_id: String) -> String:
	if action_id.begins_with("debrief_choice:"):
		return "debrief_choice"
	if action_id.begins_with("use_artifact:"):
		return "use_artifact"
	if action_id.begins_with("take_symbiote:"):
		return "take_symbiote"
	if action_id.begins_with("activate_symbiote:"):
		return "activate_symbiote"
	if action_id.begins_with("buy_mutation:"):
		return "buy_mutation"
	if action_id.contains(":"):
		return str(action_id.split(":", false, 1)[0])
	return action_id


func _add_pressure_axis(axes: Array[String], axis: String) -> void:
	if axis != "" and not axes.has(axis):
		axes.append(axis)


func _increment_pressure(axis: String) -> int:
	var count := int(pressure_counts.get(axis, 0)) + 1
	pressure_counts[axis] = count
	return count


func _get_pressure_count(axis: String) -> int:
	return int(pressure_counts.get(axis, 0))


func _evaluate_pressure_axis(axis: String, count: int) -> Array[String]:
	var lines: Array[String] = []
	var warning_threshold := int(deck_config.get("pressure_warning_threshold", 3))
	var lock_threshold := int(deck_config.get("pressure_lock_threshold", 6))

	match axis:
		"corruption":
			var corruption_warning_threshold := int(deck_config.get("corruption_warning_threshold", warning_threshold))
			if count >= warning_threshold or corruption >= corruption_warning_threshold:
				if _enqueue_director_event_once("director_corruption_warning", "corruption_warning"):
					lines.append("The walls accept the new shape too quickly.")
			var corruption_ending_threshold := int(deck_config.get("corruption_ending_threshold", 8))
			if count >= lock_threshold or corruption >= corruption_ending_threshold:
				if _lock_ending_pressure("corruption"):
					lines.append("The run tilts. Corruption has the stronger claim.")
		"danger", "avoid_combat":
			var danger_warning_threshold := int(deck_config.get("danger_warning_threshold", warning_threshold))
			if count >= warning_threshold or danger >= danger_warning_threshold or _get_pressure_count("avoid_combat") >= danger_warning_threshold:
				if _enqueue_director_event_once("director_danger_warning", "danger_warning"):
					lines.append("Something has learned the route behind me.")
			var hunter_ending_threshold := int(deck_config.get("hunter_ending_threshold", 8))
			var hunter_avoidance_threshold := int(deck_config.get("hunter_avoidance_threshold", 4))
			if count >= lock_threshold or danger >= hunter_ending_threshold or _get_pressure_count("avoid_combat") >= hunter_avoidance_threshold:
				if _lock_ending_pressure("hunter"):
					lines.append("The run tilts. The hunter has the scent.")
		"greed":
			if count >= warning_threshold:
				if _enqueue_director_event_once("director_greed_warning", "greed_warning"):
					lines.append("The organism starts pricing my appetite.")
			if count >= lock_threshold:
				_add_danger(1)
		"safety":
			if count >= warning_threshold:
				if _enqueue_director_event_once("director_safety_warning", "safety_warning"):
					lines.append("The quiet route is starting to close.")
			if count >= lock_threshold:
				_add_danger(1)
		"combat":
			if count >= warning_threshold:
				if _enqueue_director_event_once("director_combat_warning", "combat_warning"):
					lines.append("Killing through every room is making me loud.")
			if count >= lock_threshold:
				_add_danger(1)
		"dependence":
			if count >= warning_threshold:
				if _enqueue_director_event_once("director_dependence_warning", "dependence_warning"):
					lines.append("Too much under my skin is answering before I do.")
		"debt":
			if count >= warning_threshold:
				if _enqueue_director_event_once("director_debt_warning", "debt_warning"):
					lines.append("The ledger starts to breathe behind me.")

	return lines


func _enqueue_director_event_once(event_id: String, warning_key: String) -> bool:
	if _director_triggered_warnings.has(warning_key):
		return false
	_director_triggered_warnings[warning_key] = true
	if special_events.has(event_id) and not _pending_director_events.has(event_id):
		_pending_director_events.append(event_id)
	return true


func _enqueue_story_followup(action_id: String, event_data: Dictionary, action_result: Dictionary = {}) -> Array[String]:
	var followup: Dictionary = _resolve_story_followup(action_id, event_data, action_result)
	if followup.is_empty():
		return []

	var event_id := str(followup.get("event_id", ""))
	if event_id == "" or not special_events.has(event_id):
		return []

	var trigger_key := str(followup.get("trigger_key", event_id))
	if trigger_key == "":
		trigger_key = event_id
	if _triggered_story_events.has(trigger_key):
		return []

	_triggered_story_events[trigger_key] = true
	if not _pending_story_event_ids().has(event_id):
		var delay_rooms := int(followup.get("delay_rooms", deck_config.get("story_followup_default_delay_rooms", 1)))
		var immediate := bool(followup.get("immediate", false))
		var pending_entry := {
			"event_id": event_id,
			"available_after_rooms": _story_event_available_after(delay_rooms, immediate)
		}
		if immediate:
			_pending_story_events.push_front(pending_entry)
		else:
			_pending_story_events.append(pending_entry)

	var queued_line := str(followup.get("queued_line", ""))
	var lines: Array[String] = []
	if queued_line != "":
		lines.append(queued_line)
	return lines


func _story_event_available_after(delay_rooms: int, immediate: bool = false) -> int:
	if immediate:
		return rooms_cleared
	return rooms_cleared + max(delay_rooms, 0) + 1


func _resolve_story_followup(action_id: String, event_data: Dictionary, action_result: Dictionary = {}) -> Dictionary:
	var followups_variant = event_data.get("story_followups", {})
	if followups_variant is String:
		return {"event_id": str(followups_variant)}

	if followups_variant is Dictionary:
		var followups: Dictionary = followups_variant
		var base_action := _base_action_id(action_id)
		var operation_band := str(action_result.get("_tts_operation_band", ""))
		var keys: Array[String] = []
		if operation_band != "":
			keys.append("%s:%s" % [action_id, operation_band])
			if base_action != action_id:
				keys.append("%s:%s" % [base_action, operation_band])
		keys.append(action_id)
		keys.append(base_action)
		keys.append("default")
		for key in keys:
			if followups.has(key):
				return _normalize_story_followup(followups.get(key))

	if followups_variant is Array:
		var base_action := _base_action_id(action_id)
		for item in followups_variant:
			if not item is Dictionary:
				continue
			var actions_variant = item.get("actions", [])
			var actions: Array[String] = []
			if actions_variant is Array:
				for value in actions_variant:
					actions.append(str(value))
			elif actions_variant is String:
				actions.append(str(actions_variant))
			if actions.is_empty() or actions.has(action_id) or actions.has(base_action):
				return _normalize_story_followup(item)

	return {}


func _normalize_story_followup(value: Variant) -> Dictionary:
	if value is String:
		return {"event_id": str(value)}
	if value is Dictionary:
		return value.duplicate(true)
	return {}


func _pending_story_event_ids() -> Array[String]:
	var ids: Array[String] = []
	for pending_variant in _pending_story_events:
		if pending_variant is Dictionary:
			var pending: Dictionary = pending_variant
			var event_id := str(pending.get("event_id", ""))
			if event_id != "":
				ids.append(event_id)
	return ids


func _pop_available_story_event_id() -> String:
	for index in range(_pending_story_events.size()):
		var pending: Dictionary = _pending_story_events[index]
		var event_id := str(pending.get("event_id", ""))
		var available_after_rooms := int(pending.get("available_after_rooms", 0))
		if event_id != "" and rooms_cleared >= available_after_rooms:
			_pending_story_events.remove_at(index)
			if special_events.has(event_id):
				return event_id
	return ""


func _lock_ending_pressure(lock_id: String) -> bool:
	if _ending_locks.has(lock_id):
		return false
	_ending_locks[lock_id] = true
	if ending_pressure == "":
		ending_pressure = lock_id
	return true


func _is_ending_locked(lock_id: String) -> bool:
	return bool(_ending_locks.get(lock_id, false))


func _is_balanced_eligible() -> bool:
	if ending_pressure != "":
		return false
	var corruption_limit := int(deck_config.get("balanced_corruption_limit", 5))
	var danger_limit := int(deck_config.get("balanced_danger_limit", 5))
	var pressure_limit := int(deck_config.get("balanced_pressure_limit", 4))
	if corruption > corruption_limit or danger > danger_limit:
		return false
	for count_variant in pressure_counts.values():
		if int(count_variant) > pressure_limit:
			return false
	return true


func _get_available_symbiote_ids() -> Array[String]:
	var available_ids: Array[String] = []
	for symbiote_id_variant in symbiotes_by_id.keys():
		var symbiote_id := str(symbiote_id_variant)
		if symbiote_id != "" and not owned_symbiotes.has(symbiote_id):
			available_ids.append(symbiote_id)
	return available_ids


func _draw_symbiote_choices(available_ids: Array[String], choice_count: int) -> Array[String]:
	var pool := available_ids.duplicate()
	var choices: Array[String] = []
	var target_count = min(max(choice_count, 1), pool.size())
	while choices.size() < target_count and not pool.is_empty():
		var index := _rng.randi_range(0, pool.size() - 1)
		choices.append(pool[index])
		pool.remove_at(index)
	return choices


func _normalize_symbiote_choices(raw_choices: Variant) -> Array[String]:
	var choices: Array[String] = []
	if not raw_choices is Array:
		return choices
	for choice in raw_choices:
		var symbiote_id := str(choice)
		if symbiote_id != "" and not choices.has(symbiote_id):
			choices.append(symbiote_id)
	return choices


func _normalize_string_array(raw_values: Variant) -> Array[String]:
	var values: Array[String] = []
	if not raw_values is Array:
		return values
	for value in raw_values:
		var text := str(value)
		if text != "":
			values.append(text)
	return values


func _take_symbiote_from_event(symbiote_id: String, event_data: Dictionary) -> Dictionary:
	if symbiote_id == "" or not symbiotes_by_id.has(symbiote_id):
		return {
			"lines": [
				"The host spasms before I can find a clean bond.",
				"Nothing comes with me."
			]
		}

	var symbiote_data: Dictionary = symbiotes_by_id.get(symbiote_id, {})
	var symbiote_name := str(symbiote_data.get("name", symbiote_id))
	if owned_symbiotes.has(symbiote_id):
		return {
			"lines": [
				"%s recognizes what is already under my skin." % symbiote_name,
				"I leave the host twitching behind."
			]
		}

	owned_symbiotes.append(symbiote_id)
	symbiote_health[symbiote_id] = int(symbiote_data.get("max_health", 1))
	var choices := _normalize_symbiote_choices(event_data.get("symbiote_choices", []))
	var lost_choices: Array[String] = []
	for choice_id in choices:
		if choice_id != symbiote_id:
			lost_choices.append(choice_id)
	var lost_names := _describe_symbiote_choices(lost_choices)
	if lost_names == "":
		lost_names = "The others"

	return {
		"lines": [
			"%s latches on and sinks into me." % symbiote_name,
			"%s die with the host. One dependency comes with me." % lost_names
		],
		"buttons": [
			{
				"label": "Activate: %s" % symbiote_name,
				"action": "activate_symbiote:%s" % symbiote_id,
				"voice_aliases": _build_symbiote_voice_aliases(symbiote_id, symbiote_data)
			},
			{
				"label": "Carry the bond forward",
				"action": "proceed",
				"voice_aliases": ["proceed", "advance", "move on", "go forward", "step through"]
			}
		]
	}


func _describe_symbiote_choices(symbiote_ids: Array[String]) -> String:
	var names: Array[String] = []
	for symbiote_id in symbiote_ids:
		var symbiote_data: Dictionary = symbiotes_by_id.get(symbiote_id, {})
		names.append(str(symbiote_data.get("name", symbiote_id)))
	if names.is_empty():
		return ""
	if names.size() == 1:
		return names[0]
	if names.size() == 2:
		return "%s and %s" % [names[0], names[1]]

	var last_name: String = names.pop_back()
	return "%s, and %s" % [", ".join(names), last_name]


func _injure_symbiote(symbiote_id: String, amount: int) -> void:
	if not symbiote_health.has(symbiote_id):
		return
	var remaining_health := int(symbiote_health.get(symbiote_id, 0)) - int(max(amount, 0))
	if remaining_health <= 0:
		_kill_symbiote(symbiote_id)
	else:
		symbiote_health[symbiote_id] = remaining_health


func _kill_symbiote(symbiote_id: String) -> void:
	owned_symbiotes.erase(symbiote_id)
	symbiote_health.erase(symbiote_id)
	symbiote_cooldowns.erase(symbiote_id)
	active_symbiotes.erase(symbiote_id)


func _start_symbiote_cooldown(symbiote_id: String, rooms: int) -> void:
	if rooms <= 0 or not owned_symbiotes.has(symbiote_id):
		return
	symbiote_cooldowns[symbiote_id] = max(int(symbiote_cooldowns.get(symbiote_id, 0)), rooms)


func _tick_symbiote_cooldowns() -> void:
	var expired_ids: Array[String] = []
	for symbiote_id_variant in symbiote_cooldowns.keys():
		var symbiote_id := str(symbiote_id_variant)
		var remaining := int(symbiote_cooldowns.get(symbiote_id, 0)) - 1
		if remaining <= 0:
			expired_ids.append(symbiote_id)
		else:
			symbiote_cooldowns[symbiote_id] = remaining

	for symbiote_id in expired_ids:
		symbiote_cooldowns.erase(symbiote_id)


func _advance_symbiote_room_state() -> void:
	_tick_symbiote_cooldowns()
	if active_symbiotes.has("impermeable_barrier"):
		active_symbiotes.erase("impermeable_barrier")
		_start_symbiote_cooldown("impermeable_barrier", 4)
	if active_symbiotes.has("pheromones"):
		active_symbiotes.erase("pheromones")
		_start_symbiote_cooldown("pheromones", 2)


func _get_mutation_cost(mutation_data: Dictionary) -> int:
	return int(max(int(mutation_data.get("biomass_cost", 6)), 0))


func _apply_owned_mutation_combat_effects(stats: Dictionary) -> void:
	for mutation_id in owned_mutations:
		var mutation_data: Dictionary = mutations_by_id.get(str(mutation_id), {})
		var effects: Dictionary = mutation_data.get("effects", {})
		if effects.is_empty():
			continue

		if effects.has("damage_multiplier"):
			stats["damage"] = int(round(float(stats.get("damage", 0)) * float(effects.get("damage_multiplier", 1.0))))
		if effects.has("damage_delta"):
			stats["damage"] = int(max(int(stats.get("damage", 0)) + int(effects.get("damage_delta", 0)), 0))
		if effects.has("initiative_delta"):
			stats["initiative"] = clamp(float(stats.get("initiative", 0.0)) + float(effects.get("initiative_delta", 0.0)), 0.0, 1.0)
		if effects.has("speed_multiplier"):
			stats["speed"] = max(float(stats.get("speed", 1.0)) * float(effects.get("speed_multiplier", 1.0)), 0.01)
		if effects.has("contact_damage"):
			stats["contact_damage"] = int(stats.get("contact_damage", 0)) + int(effects.get("contact_damage", 0))
		if effects.has("battle_start_shield"):
			stats["shield"] = int(stats.get("shield", 0)) + int(effects.get("battle_start_shield", 0))
		if effects.has("max_health_delta"):
			stats["health"] = int(max(int(stats.get("health", 1)) + int(effects.get("max_health_delta", 0)), 1))


func _apply_owned_mutation_state_bounds() -> void:
	var max_health := int(deck_config.get("base_player_stats", {}).get("health", int(player_state.get("health", 1))))
	var max_shield := int(deck_config.get("base_player_stats", {}).get("shield", int(player_state.get("shield", 0))))
	for mutation_id in owned_mutations:
		var mutation_data: Dictionary = mutations_by_id.get(str(mutation_id), {})
		var effects: Dictionary = mutation_data.get("effects", {})
		max_health += int(effects.get("max_health_delta", 0))
		max_shield += int(effects.get("max_shield_delta", 0))

	player_state["health"] = int(clamp(int(player_state.get("health", 1)), 1, max(max_health, 1)))
	player_state["shield"] = int(clamp(int(player_state.get("shield", 0)), 0, max(max_shield, 0)))


func _add_biomass(amount: int) -> int:
	biomass = int(max(biomass + amount, 0))
	return biomass


func _add_food(amount: int) -> int:
	food = int(clamp(food + amount, 0, 20))
	_queue_resource_story_triggers()
	return food


func _add_fuel(amount: int) -> int:
	fuel = int(clamp(fuel + amount, 0, 20))
	_queue_resource_story_triggers()
	return fuel


func _add_water(amount: int) -> int:
	water = int(clamp(water + amount, 0, 20))
	_queue_resource_story_triggers()
	return water


func _add_crew_morale(amount: int) -> int:
	crew_morale = int(clamp(crew_morale + amount, 0, 10))
	if amount < 0:
		crew_unrest = int(clamp(crew_unrest + abs(amount), 0, 10))
	elif amount > 0:
		crew_unrest = int(clamp(crew_unrest - amount, 0, 10))
	_queue_resource_story_triggers()
	return crew_morale


func _add_crew_unrest(amount: int) -> int:
	crew_unrest = int(clamp(crew_unrest + amount, 0, 10))
	if amount > 0:
		crew_morale = int(clamp(crew_morale - amount, 0, 10))
	elif amount < 0:
		crew_morale = int(clamp(crew_morale + abs(amount), 0, 10))
	_queue_resource_story_triggers()
	return crew_unrest


func _add_corruption(amount: int) -> int:
	corruption = int(max(corruption + amount, 0))
	return corruption


func _apply_barrier_to_event_damage(raw_damage: int) -> Dictionary:
	var damage := int(max(raw_damage, 0))
	var result := {
		"remaining_damage": damage,
		"symbiote_blocked": 0,
		"symbiote_injured": false
	}
	if not active_symbiotes.has("impermeable_barrier"):
		return result

	var barrier_state: Dictionary = active_symbiotes.get("impermeable_barrier", {})
	var barrier_armor := int(barrier_state.get("armor", 0))
	if barrier_armor <= 0:
		active_symbiotes.erase("impermeable_barrier")
		return result

	var blocked: int = int(min(barrier_armor, damage))
	barrier_armor -= blocked
	result["symbiote_blocked"] = blocked
	result["remaining_damage"] = int(max(damage - blocked, 0))

	if barrier_armor <= 0:
		active_symbiotes.erase("impermeable_barrier")
		_injure_symbiote("impermeable_barrier", 1)
		_start_symbiote_cooldown("impermeable_barrier", 4)
		result["symbiote_injured"] = true
	else:
		barrier_state["armor"] = barrier_armor
		active_symbiotes["impermeable_barrier"] = barrier_state
	return result


func _apply_player_damage(raw_damage: int) -> Dictionary:
	var barrier_result := _apply_barrier_to_event_damage(raw_damage)
	var armor_value := int(player_state.get("armor", 0))
	var non_negative_damage: int = int(max(int(barrier_result.get("remaining_damage", raw_damage)), 0))
	var mitigated_by_armor: int = int(min(armor_value, non_negative_damage))
	var post_armor_damage: int = int(max(non_negative_damage - mitigated_by_armor, 0))
	var current_shield := int(player_state.get("shield", 0))
	var shield_lost: int = int(min(current_shield, post_armor_damage))
	player_state["shield"] = current_shield - shield_lost
	var remaining_damage: int = int(max(post_armor_damage - shield_lost, 0))
	var current_health := int(player_state.get("health", 0))
	var health_lost: int = int(min(current_health, remaining_damage))
	player_state["health"] = current_health - health_lost
	var mitosis_triggered := false
	if int(player_state["health"]) <= 0 and _can_mitosis_trigger():
		_kill_symbiote("mitosis_unit")
		player_state["health"] = 1
		mitosis_triggered = true
	return {
		"symbiote_blocked": int(barrier_result.get("symbiote_blocked", 0)),
		"symbiote_injured": bool(barrier_result.get("symbiote_injured", false)),
		"mitosis_triggered": mitosis_triggered,
		"mitigated_by_armor": mitigated_by_armor,
		"shield_lost": shield_lost,
		"health_lost": health_lost,
		"remaining_shield": int(player_state.get("shield", 0)),
		"remaining_health": int(player_state.get("health", 0))
	}


func _restore_player_health(amount: int) -> int:
	var current_health := int(player_state.get("health", 0))
	var max_health := int(deck_config.get("base_player_stats", {}).get("health", current_health))
	var missing_health: int = int(max(max_health - current_health, 0))
	var restored: int = int(clamp(amount, 0, missing_health))
	player_state["health"] = current_health + restored
	return restored


func _restore_player_shield(amount: int) -> int:
	var current_shield := int(player_state.get("shield", 0))
	var max_shield := int(deck_config.get("base_player_stats", {}).get("shield", current_shield))
	var missing_shield: int = int(max(max_shield - current_shield, 0))
	var restored: int = int(clamp(amount, 0, missing_shield))
	player_state["shield"] = current_shield + restored
	return restored


func _build_damage_result(raw_damage: int, intro_lines: Array[String], closing_line: String) -> Dictionary:
	var damage_result := _apply_player_damage(raw_damage)
	var lines := intro_lines.duplicate()
	lines.append(_build_damage_summary(raw_damage, damage_result))
	lines.append(closing_line)
	return {
		"lines": lines,
		"buttons": [_default_proceed_button()]
	}


func _build_damage_summary(raw_damage: int, damage_result: Dictionary) -> String:
	var summary := "%d damage hit. Barrier blocked %d, armor blocked %d, shield lost %d, health lost %d." % [
		raw_damage,
		int(damage_result.get("symbiote_blocked", 0)),
		int(damage_result.get("mitigated_by_armor", 0)),
		int(damage_result.get("shield_lost", 0)),
		int(damage_result.get("health_lost", 0))
	]
	if bool(damage_result.get("symbiote_injured", false)):
		summary += " Impermeable Barrier loses 1 health."
	if bool(damage_result.get("mitosis_triggered", false)):
		summary += " Mitosis Unit dies in my place."
	return summary


func _can_mitosis_trigger() -> bool:
	return owned_symbiotes.has("mitosis_unit") and int(symbiote_health.get("mitosis_unit", 0)) > 0 and active_symbiotes.has("mitosis_unit")


func _add_danger(amount: int) -> void:
	danger = int(max(danger + amount, 0))
	_sync_heart_rate()


func _sync_heart_rate() -> void:
	if not is_inside_tree():
		return
	var heart_manager := get_node_or_null(HEART_MANAGER_PATH)
	if heart_manager != null:
		heart_manager.set("bpm", get_danger_bpm())


func _index_rooms(payload: Dictionary) -> Dictionary:
	var indexed: Dictionary = {}
	var rooms_variant = payload.get("rooms", [])
	if not rooms_variant is Array:
		return indexed

	for room_variant in rooms_variant:
		if not room_variant is Dictionary:
			continue
		var room_data: Dictionary = room_variant
		var room_id := str(room_data.get("id", ""))
		if room_id != "":
			indexed[room_id] = room_data.duplicate(true)

	return indexed


func _index_room_events(payload: Variant) -> Dictionary:
	var indexed: Dictionary = {}
	if not payload is Dictionary:
		return indexed

	for room_id in payload.keys():
		var events_variant = payload[room_id]
		if not events_variant is Array:
			continue
		indexed[str(room_id)] = events_variant.duplicate(true)

	return indexed


func _index_special_events(payload: Variant) -> Dictionary:
	var indexed: Dictionary = {}
	if not payload is Dictionary:
		return indexed

	for event_id in payload.keys():
		var event_variant = payload[event_id]
		if event_variant is Dictionary:
			indexed[str(event_id)] = event_variant.duplicate(true)

	return indexed


func _index_simple_map(payload: Variant) -> Dictionary:
	var indexed: Dictionary = {}
	if not payload is Array:
		return indexed

	for item_variant in payload:
		if not item_variant is Dictionary:
			continue
		var item_data: Dictionary = item_variant
		var item_id := str(item_data.get("id", ""))
		if item_id != "":
			indexed[item_id] = item_data.duplicate(true)

	return indexed


func _draw_room_from_pool(pool_ids: Array[String], already_chosen: Array[String]) -> String:
	var available: Array[String] = []
	for room_id in pool_ids:
		if not _is_room_consumed(room_id) and not already_chosen.has(room_id):
			available.append(room_id)

	if available.is_empty():
		for room_id in pool_ids:
			if not _is_room_consumed(room_id):
				available.append(room_id)

	if available.is_empty():
		return ""

	return available[_rng.randi_range(0, available.size() - 1)]


func _load_json(path: String) -> Dictionary:
	if not FileAccess.file_exists(path):
		return {}

	var raw_json := FileAccess.get_file_as_string(path)
	var parsed = JSON.parse_string(raw_json)
	if parsed is Dictionary:
		return parsed

	return {}
