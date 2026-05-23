extends SceneTree

const RunManagerScript := preload("res://run_manager.gd")


func _init() -> void:
	var run_manager := RunManagerScript.new()
	root.add_child(run_manager)
	run_manager.start_new_run()

	if str(run_manager.content_track) != "revelation_packets_v1":
		push_error("RunManager did not load Revelation packet content track.")
		quit(1)
		return

	var opening: Dictionary = run_manager.get_current_encounter()
	if str(opening.get("event_id", "")) != "captain_initial_report":
		push_error("Opening encounter was not captain_initial_report.")
		quit(1)
		return

	var starter_rooms: Array = run_manager.deck_config.get("starter_rooms", [])
	if starter_rooms.is_empty():
		push_error("Deck config has no starter rooms.")
		quit(1)
		return
	var room_id := str(starter_rooms[0])
	var room_events: Array = run_manager.room_events_by_room.get(room_id, [])
	if room_events.is_empty():
		push_error("%s has no events." % room_id)
		quit(1)
		return
	var branch_followups: Dictionary = room_events[0].get("story_followups", {})
	var expected_branch_keys := [
		"intercept:success",
		"intercept:partial",
		"intercept:failure",
		"destroy:success",
		"destroy:partial",
		"destroy:failure"
	]
	var branch_event_ids := {}
	for branch_key in expected_branch_keys:
		if not branch_followups.has(branch_key):
			push_error("Borrowed separation is missing branch follow-up `%s`." % branch_key)
			quit(1)
			return
		var branch_followup: Dictionary = branch_followups.get(branch_key, {})
		var branch_event_id := str(branch_followup.get("event_id", ""))
		if branch_event_id == "" or not run_manager.special_events.has(branch_event_id):
			push_error("Borrowed separation branch `%s` points to missing event `%s`." % [branch_key, branch_event_id])
			quit(1)
			return
		branch_event_ids[branch_event_id] = true
	if branch_event_ids.size() < 4:
		push_error("Borrowed separation branches reconverged too early; expected distinct clean/residual/active resolution events.")
		quit(1)
		return
	for cooldown_id in [
		"cooldown_borrowed_separation_clean",
		"cooldown_borrowed_separation_residual",
		"cooldown_borrowed_separation_active"
	]:
		var cooldown_event: Dictionary = run_manager.special_events.get(cooldown_id, {})
		var choices: Array = cooldown_event.get("choices", [])
		var choice_effects: Array = cooldown_event.get("choice_effects", [])
		var followup_hooks: Array = cooldown_event.get("followup_hooks", [])
		if choices.is_empty() or choice_effects.size() != choices.size():
			push_error("%s does not give every debrief choice a state effect." % cooldown_id)
			quit(1)
			return
		if followup_hooks.size() < 3:
			push_error("%s does not leave enough future follow-up hooks." % cooldown_id)
			quit(1)
			return
		for effect_variant in choice_effects:
			if not effect_variant is Dictionary:
				push_error("%s has a malformed debrief choice effect." % cooldown_id)
				quit(1)
				return
			var effect: Dictionary = effect_variant
			var state_changes: Array = effect.get("environment_state_changes", [])
			var resource_changes: Dictionary = effect.get("resource_changes", {})
			var pressure_changes: Dictionary = effect.get("pressure_changes", {})
			if state_changes.is_empty() or (resource_changes.is_empty() and pressure_changes.is_empty()):
				push_error("%s has a debrief choice effect without both a hook and a stat/pressure change." % cooldown_id)
				quit(1)
				return

	var room_data: Dictionary = run_manager.get_room_data(room_id)
	var first_packet: Dictionary = run_manager.call("_build_room_encounter", room_id, room_events[0])
	var first_lines: Array = first_packet.get("lines", [])
	if first_lines.size() < 4 or str(first_lines[0]) != "SITREP:":
		push_error("First Revelation mission did not start with a SITREP.")
		quit(1)
		return
	if not first_lines.has(str(room_data.get("first_visit_description", ""))):
		push_error("First Revelation mission did not include its first_visit_description.")
		quit(1)
		return
	var detection_index := first_lines.find("DETECTION: %s" % str(room_data.get("detection_report", "")))
	var description_index := first_lines.find(str(room_data.get("first_visit_description", "")))
	var current_index := first_lines.find("CURRENT: %s" % str(room_data.get("current_situation", "")))
	if detection_index < 0 or description_index < 0 or current_index < 0 or not (detection_index < description_index and description_index < current_index):
		push_error("First Revelation mission SITREP order was not chronological: detection, deployment, current.")
		quit(1)
		return

	var return_packet: Dictionary = run_manager.call("_build_room_encounter", room_id, room_events[0])
	var return_lines: Array = return_packet.get("lines", [])
	if return_lines.is_empty() or str(return_lines[0]) != str(room_data.get("return_description", "")):
		push_error("Second Revelation mission did not use its return_description.")
		quit(1)
		return

	var opening_flow_manager := RunManagerScript.new()
	root.add_child(opening_flow_manager)
	opening_flow_manager.start_new_run()
	opening_flow_manager.consume_current_event("intercept")
	var configured_first_room: Dictionary = opening_flow_manager.advance_to_next_encounter()
	if str(configured_first_room.get("room_id", "")) != room_id:
		push_error("Configured first room after opening was not honored; got `%s`, expected `%s`." % [
			str(configured_first_room.get("room_id", "")),
			room_id
		])
		quit(1)
		return
	opening_flow_manager.queue_free()

	run_manager.consume_current_event("intercept")
	run_manager._pending_room_id_after_transition = room_id
	var live_packet: Dictionary = run_manager.advance_to_next_encounter()
	if str(live_packet.get("room_id", "")) != room_id:
		push_error("Forced starter mission did not appear in live flow.")
		quit(1)
		return
	if not run_manager.consumed_rooms.has(room_id):
		push_error("Live Revelation mission room was not consumed on entry.")
		quit(1)
		return
	if not run_manager.call("_get_eligible_events_for_room", room_id).is_empty():
		push_error("Consumed Revelation mission still had eligible events.")
		quit(1)
		return

	var ross: Dictionary = run_manager.officer_state.get("agent_caleb_ross", {})
	ross["availability"] = 0
	run_manager.officer_state["agent_caleb_ross"] = ross
	var backup_event := {
		"id": "backup_smoke",
		"type": "choice",
		"line_1": "Backup smoke.",
		"buttons": [
			{
				"label": "Send Ross",
				"action": "ross_plan",
				"voice_aliases": ["ross"]
			}
		],
		"operation_plans": [
			{
				"action": "ross_plan",
				"officer_id": "agent_caleb_ross",
				"primary_skill": "security",
				"base_success": 0.7,
				"intent": "Ross takes the threshold.",
				"risk": "The backup has less context.",
				"outcomes": {
					"success": {
						"lines": ["The reassigned operator holds the threshold."]
					},
					"failure": {
						"lines": ["The reassigned operator loses the threshold."]
					}
				}
			}
		]
	}
	var backup_buttons: Array = run_manager.call("_build_buttons", backup_event)
	if backup_buttons.is_empty() or not str(backup_buttons[0].get("label", "")).begins_with("Backup:"):
		push_error("Unavailable officer did not produce a backup plan button.")
		quit(1)
		return
	var backup_result: Dictionary = run_manager.call("_resolve_operation_action_result", "ross_plan", backup_event)
	if backup_result.get("lines", []).is_empty():
		push_error("Backup operation plan did not resolve.")
		quit(1)
		return

	run_manager.call("_apply_environment_state_changes", ["agent_caleb_ross.availability: suspended pending Institute review"])
	var updated_ross: Dictionary = run_manager.officer_state.get("agent_caleb_ross", {})
	if int(updated_ross.get("availability", 100)) > 0:
		push_error("Text availability state write did not affect officer availability.")
		quit(1)
		return

	print("REVELATION_PACKET_ROOM_SMOKE_OK")
	quit(0)
