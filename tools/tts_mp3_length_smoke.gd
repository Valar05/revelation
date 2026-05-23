extends SceneTree

const CHECK_IDS := [
	"room_borrowed_separation_detection_narration_1_part_1",
	"room_borrowed_separation_current_narration_1_part_1",
	"root_borrowed_separation_proposal_1_part_1",
	"root_borrowed_separation_proposal_2_part_1",
	"root_borrowed_separation_choice_1",
]


func _init() -> void:
	var manifest_file := FileAccess.open("res://audio/tts_manifest.json", FileAccess.READ)
	if manifest_file == null:
		push_error("TTS manifest could not be opened.")
		quit(1)
		return
	var parsed = JSON.parse_string(manifest_file.get_as_text())
	if not parsed is Dictionary:
		push_error("TTS manifest was not valid JSON.")
		quit(1)
		return
	var by_id := {}
	for clip in parsed.get("clips", []):
		if clip is Dictionary:
			by_id[str(clip.get("id", ""))] = clip

	for clip_id in CHECK_IDS:
		var clip: Dictionary = by_id.get(clip_id, {})
		if clip.is_empty():
			push_error("Missing clip id: %s" % clip_id)
			quit(1)
			return
		var clip_file := str(clip.get("file", ""))
		var stream: AudioStream
		match clip_file.get_extension().to_lower():
			"wav":
				stream = AudioStreamWAV.load_from_file(clip_file)
			"mp3":
				stream = AudioStreamMP3.load_from_file(clip_file)
			_:
				stream = load(clip_file) as AudioStream
		if stream == null:
			push_error("Could not load MP3: %s" % clip_file)
			quit(1)
			return
		var length := stream.get_length()
		print("TTS_LENGTH id=%s seconds=%.3f text=%s" % [clip_id, length, str(clip.get("text", ""))])
		if length < 0.55:
			push_error("Clip is too short according to Godot: %s %.3fs" % [clip_id, length])
			quit(1)
			return

	print("TTS_MP3_LENGTH_SMOKE_OK")
	quit(0)
