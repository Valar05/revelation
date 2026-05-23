extends SceneTree

const WorldScene := preload("res://world.tscn")


func _init() -> void:
	var world := WorldScene.instantiate()
	root.add_child(world)
	for index in range(12):
		await process_frame

	var run_manager = world.call("_get_run_manager")
	if run_manager == null:
		push_error("RunManager was not available.")
		quit(1)
		return

	var room_id := "room_borrowed_separation"
	var room_events: Array = run_manager.room_events_by_room.get(room_id, [])
	if room_events.is_empty():
		push_error("%s has no room events." % room_id)
		quit(1)
		return

	var encounter: Dictionary = run_manager.call("_build_room_encounter", room_id, room_events[0])
	var lines: Array = encounter.get("lines", [])
	if lines.size() < 6:
		push_error("Borrowed separation encounter did not include room and event lines.")
		quit(1)
		return

	var direct_count := 0
	var event_line_count := 0
	var proposal_count := 0
	var selected_files: Array[String] = []
	for line_index in range(lines.size()):
		var files: Array = world.call("_tts_direct_clip_files_for_console_line", encounter, str(lines[line_index]), line_index)
		for file in files:
			selected_files.append(str(file))
		direct_count += files.size()
		if str(lines[line_index]) == str(room_events[0].get("line_1", "")) or str(lines[line_index]) == str(room_events[0].get("line_2", "")):
			event_line_count += files.size()
		if str(lines[line_index]).begins_with("Proposals") or str(lines[line_index]).contains(" Risk: "):
			proposal_count += files.size()

	if direct_count < 15:
		push_error("Borrowed separation queued too few direct TTS clips: %d." % direct_count)
		quit(1)
		return
	if event_line_count < 2:
		push_error("Borrowed separation did not queue direct event-line TTS clips.")
		quit(1)
		return
	var detection_file := str(world._tts_clip_files.get("room_borrowed_separation_detection_narration_1_part_1", ""))
	var current_file := str(world._tts_clip_files.get("room_borrowed_separation_current_narration_1_part_1", ""))
	var brooks_file := str(world._tts_clip_files.get("root_borrowed_separation_proposal_1_part_1", ""))
	var park_file := str(world._tts_clip_files.get("root_borrowed_separation_proposal_2_part_1", ""))
	var old_header_file := str(world._tts_clip_files.get("root_borrowed_separation_proposals_header", ""))
	if not selected_files.has(detection_file):
		push_error("Borrowed separation did not select the detection intro clip.")
		quit(1)
		return
	if not selected_files.has(current_file):
		push_error("Borrowed separation did not select the current intro clip.")
		quit(1)
		return
	if brooks_file != "" and selected_files.has(brooks_file):
		var brooks_text := str(world._tts_file_texts.get(brooks_file, ""))
		if brooks_text.find("he and Owen") != -1:
			push_error("Borrowed separation selected stale Brooks proposal audio with old pronouns.")
			quit(1)
			return
	if park_file != "" and selected_files.has(park_file):
		var park_text := str(world._tts_file_texts.get(park_file, ""))
		if park_text == "":
			push_error("Borrowed separation selected a Park proposal clip without manifest text.")
			quit(1)
			return
	if old_header_file != "" and selected_files.has(old_header_file):
		push_error("Borrowed separation still selected the standalone Proposals header clip.")
		quit(1)
		return
	for selected_file in selected_files:
		var selected_text := str(world._tts_file_texts.get(selected_file, ""))
		if ["Brooks.", "Specialist Mina Park.", "Risk.", "takes.", "Proposals."].has(selected_text):
			push_error("Borrowed separation selected standalone fragment: %s" % selected_text)
			quit(1)
			return

	var choice_one_file := str(world._tts_clip_files.get("root_borrowed_separation_choice_1", ""))
	var choice_two_file := str(world._tts_clip_files.get("root_borrowed_separation_choice_2", ""))
	if choice_one_file == "" or not world.call("_tts_clip_available", choice_one_file):
		push_error("Borrowed separation choice one TTS file was not available.")
		quit(1)
		return
	if choice_two_file == "" or not world.call("_tts_clip_available", choice_two_file):
		push_error("Borrowed separation choice two TTS file was not available.")
		quit(1)
		return

	var cooldown: Dictionary = run_manager.call("_build_special_encounter", "cooldown_borrowed_separation")
	var cooldown_buttons: Array = cooldown.get("buttons", [])
	if cooldown_buttons.size() < 3:
		push_error("Borrowed separation cooldown did not expose all debrief choice buttons.")
		quit(1)
		return
	if str(cooldown_buttons[0].get("label", "")).contains("Concede") or str(cooldown_buttons[1].get("label", "")).contains("Hold Line"):
		push_error("Borrowed separation cooldown still exposed generic Concede/Hold Line choices.")
		quit(1)
		return
	var cooldown_choice_file := str(world._tts_clip_files.get("cooldown_borrowed_separation_choice_1", ""))
	if cooldown_choice_file != "":
		var expected_cooldown_choice := "Choice one. %s." % str(cooldown_buttons[0].get("label", "")).trim_suffix(".")
		var cooldown_choice_text := str(world._tts_file_texts.get(cooldown_choice_file, ""))
		if cooldown_choice_text.contains("Concede") or cooldown_choice_text.contains("Hold Line"):
			push_error("Borrowed separation cooldown still maps to stale generic choice audio.")
			quit(1)
			return
		var cooldown_choice_files: Array[String] = [cooldown_choice_file]
		if not world.call("_tts_clip_files_match_line", cooldown_choice_files, expected_cooldown_choice):
			push_error("Borrowed separation cooldown choice audio did not match the visible choice.")
			quit(1)
			return

	var action_context := {
		"event_id": "root_borrowed_separation",
		"room_id": room_id,
		"tts_context": "action_result",
		"tts_action_id": "destroy"
	}
	var action_files: Array = world.call(
		"_tts_direct_clip_files_for_console_line",
		action_context,
		str(room_events[0].get("action_results", {}).get("destroy", {}).get("lines", [""])[0]),
		0
	)
	if action_files.size() < 10:
		push_error("Borrowed separation action result queued too few direct TTS clips: %d." % action_files.size())
		quit(1)
		return

	var operation_plans: Array = room_events[0].get("operation_plans", [])
	var destroy_plan: Dictionary = operation_plans[1] if operation_plans.size() > 1 and operation_plans[1] is Dictionary else {}
	var destroy_outcomes: Dictionary = destroy_plan.get("outcomes", {})
	var destroy_partial: Dictionary = destroy_outcomes.get("partial", {})
	var destroy_partial_lines: Array = destroy_partial.get("lines", [])
	var operation_line := str(destroy_partial_lines[0] if not destroy_partial_lines.is_empty() else "")
	var mismatched_operation_files: Array = world.call(
		"_tts_direct_clip_files_for_console_line",
		action_context,
		operation_line,
		0
	)
	if not mismatched_operation_files.is_empty():
		push_error("Borrowed separation selected canned action-result TTS for a randomized operation outcome.")
		quit(1)
		return

	var operation_context := action_context.duplicate(true)
	operation_context["tts_operation_band"] = "partial"
	var operation_files: Array = world.call(
		"_tts_direct_clip_files_for_console_line",
		operation_context,
		operation_line,
		0
	)
	if not operation_files.is_empty():
		var operation_texts: Array[String] = []
		for operation_file in operation_files:
			operation_texts.append(str(world._tts_file_texts.get(str(operation_file), "")))
		if world.call("_tts_equivalence_key", " ".join(operation_texts)) != world.call("_tts_equivalence_key", operation_line):
			push_error("Borrowed separation operation TTS did not match the displayed operation result.")
			quit(1)
			return

	print("TTS_BORROWED_AUDIO_SMOKE_OK direct=%d event=%d proposal=%d action=%d operation=%d choices=2 no_standalone_fragments" % [direct_count, event_line_count, proposal_count, action_files.size(), operation_files.size()])
	quit(0)
