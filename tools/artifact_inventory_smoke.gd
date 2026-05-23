extends SceneTree

const RunManagerScript := preload("res://run_manager.gd")


func _init() -> void:
	var run_manager := RunManagerScript.new()
	root.add_child(run_manager)
	run_manager.start_new_run()

	if str(run_manager.content_track) != "revelation_packets_v1":
		push_error("RunManager did not load Revelation packet content.")
		quit(1)
		return

	var operation_event := {
		"id": "artifact_reward_operation_smoke",
		"type": "choice",
		"operation_plans": [
			{
				"action": "secure",
				"base_success": 0.95,
				"outcomes": {
					"success": {
						"lines": ["The custody transfer succeeds."]
					},
					"partial": {
						"lines": ["The custody transfer is delayed."]
					},
					"failure": {
						"lines": ["The custody transfer fails."]
					}
				}
			}
		],
		"action_results": {
			"secure": {
				"artifact_rewards": ["covenant_lock_remnant"]
			}
		}
	}
	for _attempt in range(50):
		var operation_result: Dictionary = run_manager.call("_apply_event_action_result", "secure", operation_event, {})
		if run_manager.owned_artifacts.has("covenant_lock_remnant"):
			var operation_lines: Array = operation_result.get("lines", [])
			if not operation_lines.has("Custody item secured: Covenant Lock Remnant."):
				push_error("Operation-plan artifact reward did not add a visible custody line.")
				quit(1)
				return
			break
	if not run_manager.owned_artifacts.has("covenant_lock_remnant"):
		push_error("Successful operation plan did not award its configured artifact.")
		quit(1)
		return

	var reward_lines: Array = run_manager.call("_apply_artifact_rewards", ["handwritten_authority_cards"])
	if reward_lines.is_empty() or not run_manager.owned_artifacts.has("handwritten_authority_cards"):
		push_error("Artifact reward did not enter custody inventory.")
		quit(1)
		return

	var artifact_event := _find_room_event(run_manager, "root_censers_seams")
	if artifact_event.is_empty():
		push_error("Could not find root_censers_seams for artifact option smoke.")
		quit(1)
		return

	var prepared_artifact_event: Dictionary = run_manager.call("_prepare_event_data", artifact_event)
	var artifact_buttons: Array = run_manager.call("_build_buttons", prepared_artifact_event)
	if not _has_action_prefix(artifact_buttons, "use_artifact:handwritten_authority_cards:"):
		push_error("Owned artifact did not create an alternate mission option.")
		quit(1)
		return

	var artifact_result: Dictionary = run_manager.call("_resolve_artifact_option", "use_artifact:handwritten_authority_cards:0", prepared_artifact_event)
	if not artifact_result.get("lines", []) is Array or artifact_result.get("lines", []).is_empty():
		push_error("Artifact alternate option did not resolve into result lines.")
		quit(1)
		return

	var debrief_packet: Dictionary = run_manager.call("_build_special_encounter", "cooldown_offering_floor")
	var debrief_buttons: Array = debrief_packet.get("buttons", [])
	if not _has_action_prefix(debrief_buttons, "debrief_choice:cooldown_offering_floor:"):
		push_error("Debrief choices were not converted into actionable buttons.")
		quit(1)
		return

	var first_debrief_action := _first_action_with_prefix(debrief_buttons, "debrief_choice:cooldown_offering_floor:")
	var debrief_result: Dictionary = run_manager.call("_resolve_debrief_choice", first_debrief_action, debrief_packet.get("event_data", {}))
	var debrief_lines: Array = debrief_result.get("lines", [])
	if debrief_lines.is_empty() or not str(debrief_lines[0]).begins_with("Debrief decision filed:"):
		push_error("Debrief choice did not resolve into a follow-up screen.")
		quit(1)
		return

	print("ARTIFACT_INVENTORY_SMOKE_OK")
	quit(0)


func _find_room_event(run_manager: Node, event_id: String) -> Dictionary:
	for room_id in run_manager.room_events_by_room.keys():
		var room_events: Array = run_manager.room_events_by_room.get(room_id, [])
		for event_variant in room_events:
			if event_variant is Dictionary and str(event_variant.get("id", "")) == event_id:
				return event_variant
	return {}


func _has_action_prefix(buttons: Array, prefix: String) -> bool:
	return _first_action_with_prefix(buttons, prefix) != ""


func _first_action_with_prefix(buttons: Array, prefix: String) -> String:
	for button_variant in buttons:
		if not button_variant is Dictionary:
			continue
		var action := str(button_variant.get("action", ""))
		if action.begins_with(prefix):
			return action
	return ""
