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

	var pressure_before: Dictionary = run_manager.revelation_pressure.duplicate(true)
	var event_data := {
		"id": "pressure_smoke",
		"type": "resolution",
		"action_results": {
			"report": {
				"lines": ["Report filed."],
				"environment_state_changes": ["pressure_smoke.report.success"],
				"pressure_changes": {
					"institute_scrutiny": 3,
					"doctrine_fracture": 1
				}
			}
		}
	}
	var result: Dictionary = run_manager.call("_apply_event_action_result", "report", event_data, {})
	if not result.get("lines", []).has("Report filed."):
		push_error("Pressure smoke action result did not resolve its visible line.")
		quit(1)
		return

	var scrutiny_delta := int(run_manager.revelation_pressure.get("institute_scrutiny", 0)) - int(pressure_before.get("institute_scrutiny", 0))
	var fracture_delta := int(run_manager.revelation_pressure.get("doctrine_fracture", 0)) - int(pressure_before.get("doctrine_fracture", 0))
	if scrutiny_delta < 2 or fracture_delta < 1:
		push_error("Explicit Revelation pressure changes were not applied.")
		quit(1)
		return
	var pending_after_review: Array = run_manager.call("_pending_story_event_ids")
	if not pending_after_review.has("pressure_command_review"):
		push_error("Institute scrutiny pressure did not queue a command review interlude.")
		quit(1)
		return

	var artifact_event := {
		"id": "pressure_artifact_smoke",
		"type": "resolution",
		"action_results": {
			"secure": {
				"lines": ["Artifact secured."],
				"environment_state_changes": ["pressure_artifact_smoke.secure.success"],
				"pressure_changes": {
					"artifact_burden": 3
				},
				"artifact_rewards": ["covenant_lock_remnant"]
			}
		}
	}
	var artifact_burden_before := int(run_manager.revelation_pressure.get("artifact_burden", 0))
	run_manager.call("_apply_event_action_result", "secure", artifact_event, {})
	if int(run_manager.revelation_pressure.get("artifact_burden", 0)) <= artifact_burden_before:
		push_error("Artifact reward did not apply inferred artifact burden.")
		quit(1)
		return
	var pending_after_artifact: Array = run_manager.call("_pending_story_event_ids")
	if not pending_after_artifact.has("pressure_artifact_custody"):
		push_error("Artifact burden did not queue an evidence custody interlude.")
		quit(1)
		return

	var review_packet: Dictionary = run_manager.call("_build_special_encounter", "pressure_command_review")
	var review_buttons: Array = review_packet.get("buttons", [])
	if not _has_action_prefix(review_buttons, "debrief_choice:pressure_command_review:"):
		push_error("Pressure command review did not expose player-facing choices.")
		quit(1)
		return

	print("REVELATION_PRESSURE_SMOKE_OK")
	quit(0)


func _has_action_prefix(buttons: Array, prefix: String) -> bool:
	for button_variant in buttons:
		if not button_variant is Dictionary:
			continue
		if str(button_variant.get("action", "")).begins_with(prefix):
			return true
	return false
