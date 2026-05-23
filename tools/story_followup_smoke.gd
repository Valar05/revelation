extends SceneTree

const RunManagerScript := preload("res://run_manager.gd")


func _init() -> void:
	var run_manager := RunManagerScript.new()
	root.add_child(run_manager)
	run_manager.start_new_run()

	var opening: Dictionary = run_manager.get_current_encounter()
	if str(opening.get("event_id", "")) != "captain_initial_report":
		push_error("Opening event was not captain_initial_report.")
		quit(1)
		return

	run_manager.consume_current_event("intercept")
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
	var root_event: Dictionary = room_events[0]
	var root_action := _first_button_action(root_event)
	if root_action == "":
		push_error("Starter room has no commandable root action.")
		quit(1)
		return

	run_manager._pending_room_id_after_transition = room_id
	var mission: Dictionary = run_manager.advance_to_next_encounter()
	if str(mission.get("room_id", "")) != room_id:
		push_error("Forced starter mission did not appear.")
		quit(1)
		return
	if _buttons_expose_hidden_numbers(mission.get("buttons", [])):
		push_error("Mission buttons expose hidden percentages or morale/resource deltas.")
		quit(1)
		return

	run_manager.consume_current_event(root_action)
	var root_action_result: Dictionary = run_manager.get_last_action_result()
	var root_followup_id := _followup_id_for_action_result(root_event, root_action, root_action_result)
	if root_followup_id == "":
		push_error("Starter room root action has no story follow-up for its operation outcome.")
		quit(1)
		return
	var result_lines: Array = run_manager.get_last_action_result().get("lines", [])
	if result_lines.is_empty():
		push_error("Mission result produced no result lines.")
		quit(1)
		return

	var resolution: Dictionary = run_manager.advance_to_next_encounter()
	if str(resolution.get("event_id", "")) != root_followup_id:
		push_error("Expected root story follow-up `%s` immediately after the mission, got `%s` in room `%s`." % [
			root_followup_id,
			str(resolution.get("event_id", "")),
			str(resolution.get("room_id", ""))
		])
		quit(1)
		return
	if bool(resolution.get("counts_as_room", true)):
		push_error("Story follow-up should not count as a normal mission clear.")
		quit(1)
		return
	if _buttons_expose_hidden_numbers(resolution.get("buttons", [])):
		push_error("Resolution buttons expose hidden percentages or morale/resource deltas.")
		quit(1)
		return

	var resolution_event: Dictionary = resolution.get("event_data", {})
	var resolution_action := _first_button_action(resolution_event)
	if resolution_action == "":
		push_error("Resolution has no commandable action.")
		quit(1)
		return
	var cooldown_id := _followup_id_for_action(resolution_event, resolution_action)
	if cooldown_id == "":
		push_error("Resolution action has no cooldown follow-up.")
		quit(1)
		return

	run_manager.consume_current_event(resolution_action)
	var result_lines_after_resolution: Array = run_manager.get_last_action_result().get("lines", [])
	if result_lines_after_resolution.is_empty():
		push_error("Resolution result produced no result lines.")
		quit(1)
		return

	var followup: Dictionary = run_manager.advance_to_next_encounter()
	if str(followup.get("event_id", "")) != cooldown_id:
		push_error("Expected cooldown immediately after resolving the anomaly.")
		quit(1)
		return
	if _buttons_expose_hidden_numbers(followup.get("buttons", [])):
		push_error("Cooldown buttons expose hidden percentages or morale/resource deltas.")
		quit(1)
		return

	print("STORY_FOLLOWUP_SMOKE_OK")
	quit(0)


func _lines_contain(lines: Array, needle: String) -> bool:
	for line in lines:
		if str(line).contains(needle):
			return true
	return false


func _first_button_action(event_data: Dictionary) -> String:
	var buttons: Array = event_data.get("buttons", [])
	for button in buttons:
		if button is Dictionary:
			var action := str(button.get("action", ""))
			if action != "":
				return action
	return ""


func _followup_id_for_action(event_data: Dictionary, action: String) -> String:
	return _followup_id_for_action_result(event_data, action, {})


func _followup_id_for_action_result(event_data: Dictionary, action: String, action_result: Dictionary) -> String:
	var followups = event_data.get("story_followups", {})
	if followups is String:
		return str(followups)
	if not followups is Dictionary:
		return ""
	var followup_map: Dictionary = followups
	var base_action := action
	if action.contains(":"):
		base_action = str(action.split(":", false, 1)[0])
	var operation_band := str(action_result.get("_tts_operation_band", ""))
	var keys: Array[String] = []
	if operation_band != "":
		keys.append("%s:%s" % [action, operation_band])
		if base_action != action:
			keys.append("%s:%s" % [base_action, operation_band])
	keys.append(action)
	keys.append(base_action)
	keys.append("default")
	for key in keys:
		if not followup_map.has(key):
			continue
		var value = followup_map.get(key)
		if value is String:
			return str(value)
		if value is Dictionary:
			return str(value.get("event_id", ""))
	return ""


func _buttons_expose_hidden_numbers(buttons: Array) -> bool:
	for button in buttons:
		if not button is Dictionary:
			continue
		var label := str(button.get("label", ""))
		if label.contains("%") or label.contains("+") or label.contains("Morale") or label.contains("Food") or label.contains("Fuel") or label.contains("Water"):
			return true
	return false
