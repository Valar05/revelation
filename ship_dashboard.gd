extends Sprite2D

signal console_option_selected(action_id: String, room_id: String)
signal console_command_submitted(command_text: String, room_id: String)

const DEFAULT_OPTION_LABEL := "Proceed."
const DEFAULT_OPTION_ACTION := "proceed"
const PORTRAIT_DASHBOARD_PATH := "res://NightmareVoyage-dashboard-portrait.png"
const CONSOLE_FONT_PATH := "res://SpecialElite-Regular.ttf"
const CONSOLE_TEXT_COLOR := Color(0.12, 0.09, 0.055, 1.0)
const CONSOLE_BUTTON_TEXT_COLOR := Color(0.88, 0.78, 0.58, 1.0)
const CONSOLE_BUTTON_COLOR := Color(0.16, 0.11, 0.07, 0.92)
const CONSOLE_BUTTON_BORDER_COLOR := Color(0.54, 0.38, 0.18, 0.95)
const COMMAND_INPUT_TEXT_COLOR := Color(0.90, 0.81, 0.62, 1.0)
const COMMAND_INPUT_COLOR := Color(0.10, 0.07, 0.045, 0.90)
const TERMINAL_MARGIN_X := 124.0
const TERMINAL_MARGIN_TOP := 108.0
const TERMINAL_MARGIN_BOTTOM := 300.0
const COMMAND_GAP := 24.0
const FULLSCREEN_INPUT_HEIGHT := 96.0
const BODY_FONT_SIZE := 36
const HEADING_FONT_SIZE := 42
const BUTTON_FONT_SIZE := 32
const INPUT_FONT_SIZE := 32
const BUTTON_MIN_HEIGHT := 96
const BUTTON_TEXT_MARGIN_X := 44.0
const BUTTON_TEXT_MARGIN_Y := 32.0

@onready var console_scroll: ScrollContainer = $Console
@onready var console_content: VBoxContainer = $Console/ConsoleContent

var _current_room_id := ""
var _command_input: LineEdit
var _command_submission_in_progress := false
var _last_command_input_text := ""
var _fullscreen_size := Vector2(1080, 1920)
var _background_scale := Vector2.ONE
var _console_font: Font


func _ready() -> void:
	_load_portrait_dashboard_texture()
	_load_console_font()
	var animation_player := get_node_or_null("AnimationPlayer") as AnimationPlayer
	if animation_player != null:
		animation_player.stop()
		animation_player.process_mode = Node.PROCESS_MODE_DISABLED
	set_process(true)
	console_scroll.focus_mode = Control.FOCUS_NONE
	_ensure_command_input()
	set_fullscreen_console_layout(_fullscreen_size)
	clear_console()


func _load_portrait_dashboard_texture() -> void:
	var image_path := ProjectSettings.globalize_path(PORTRAIT_DASHBOARD_PATH)
	if not FileAccess.file_exists(image_path):
		push_warning("Portrait dashboard texture not found: %s." % image_path)
		return
	var image := Image.load_from_file(image_path)
	if image == null or image.is_empty():
		push_warning("Portrait dashboard texture could not be loaded: %s." % image_path)
		return
	texture = ImageTexture.create_from_image(image)


func _load_console_font() -> void:
	if not FileAccess.file_exists(CONSOLE_FONT_PATH):
		push_warning("Console font not found: %s." % CONSOLE_FONT_PATH)
		return
	var font_file := FontFile.new()
	var load_error := font_file.load_dynamic_font(CONSOLE_FONT_PATH)
	if load_error != OK:
		push_warning("Console font could not be loaded: %s. Error: %s" % [CONSOLE_FONT_PATH, load_error])
		return
	_console_font = font_file


func _process(_delta: float) -> void:
	if _command_input != null and _command_input.visible and not _command_input.has_focus():
		_command_input.grab_focus()


func set_room_data(room_data: Dictionary) -> void:
	_current_room_id = str(room_data.get("id", ""))
	var lines: Array[String] = []
	var ui_text_variant = room_data.get("ui_text", {})
	if ui_text_variant is Dictionary:
		var ui_text: Dictionary = ui_text_variant
		var speaker := str(ui_text.get("speaker", ""))
		var line_1 := str(ui_text.get("line_1", ""))
		var line_2 := str(ui_text.get("line_2", ""))

		if line_1 != "":
			lines.append(line_1)
		if line_2 != "":
			lines.append(line_2)

	show_console(lines, _get_room_options(room_data), _current_room_id)


func set_fullscreen_console_layout(viewport_size: Vector2) -> void:
	if viewport_size.x <= 0.0 or viewport_size.y <= 0.0:
		return

	_fullscreen_size = viewport_size
	centered = true
	modulate = Color.WHITE
	self_modulate = Color.WHITE

	_background_scale = _calculate_background_cover_scale(viewport_size)
	scale = _background_scale
	position = viewport_size * 0.5

	var content_left := TERMINAL_MARGIN_X
	var content_top := TERMINAL_MARGIN_TOP
	var content_right := viewport_size.x - TERMINAL_MARGIN_X
	var content_bottom := viewport_size.y - TERMINAL_MARGIN_BOTTOM
	var control_width: float = max(content_right - content_left, 0.0)
	var input_top := content_bottom - FULLSCREEN_INPUT_HEIGHT
	var console_bottom := input_top - COMMAND_GAP
	var console_height: float = max(console_bottom - content_top, 0.0)

	_disable_legacy_fullscreen_backdrop()

	_place_control_in_viewport(console_scroll, Rect2(content_left, content_top, control_width, console_height))
	console_scroll.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	console_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	console_content.custom_minimum_size = Vector2(control_width, 0.0)
	console_content.add_theme_constant_override("separation", 24)

	_ensure_command_input()
	if _command_input != null:
		_place_control_in_viewport(_command_input, Rect2(content_left, input_top, control_width, FULLSCREEN_INPUT_HEIGHT))
		_command_input.custom_minimum_size = Vector2(0, FULLSCREEN_INPUT_HEIGHT)


func _calculate_background_cover_scale(viewport_size: Vector2) -> Vector2:
	if texture == null:
		return Vector2.ONE
	var texture_size := texture.get_size()
	if texture_size.x <= 0.0 or texture_size.y <= 0.0:
		return Vector2.ONE
	var cover_scale: float = max(viewport_size.x / texture_size.x, viewport_size.y / texture_size.y)
	return Vector2(cover_scale, cover_scale)


func _place_control_in_viewport(control: Control, viewport_rect: Rect2) -> void:
	if control == null:
		return
	var local_position := _viewport_point_to_local(viewport_rect.position)
	control.scale = Vector2(1.0 / max(_background_scale.x, 0.001), 1.0 / max(_background_scale.y, 0.001))
	control.offset_left = local_position.x
	control.offset_top = local_position.y
	control.offset_right = local_position.x + viewport_rect.size.x
	control.offset_bottom = local_position.y + viewport_rect.size.y


func _viewport_point_to_local(viewport_point: Vector2) -> Vector2:
	return Vector2(
		(viewport_point.x - position.x) / max(_background_scale.x, 0.001),
		(viewport_point.y - position.y) / max(_background_scale.y, 0.001)
	)


func _disable_legacy_fullscreen_backdrop() -> void:
	var old_backdrop := get_node_or_null("FullscreenBackdrop") as CanvasItem
	if old_backdrop != null:
		old_backdrop.hide()


func clear_console() -> void:
	for child in console_content.get_children():
		child.queue_free()


func append_console_entry(text: String) -> void:
	_append_label(text)
	call_deferred("_scroll_console_to_bottom")


func show_console(lines: Array, options: Array, room_id: String = "") -> void:
	if room_id != "":
		_current_room_id = room_id

	clear_console()
	var narrative_lines := _sanitize_narration_lines(lines)
	for index in narrative_lines.size():
		var line_text := str(narrative_lines[index])
		_append_label(line_text, index == 0 and line_text.ends_with(":"))

	for option in options:
		_append_button(option)

	call_deferred("_scroll_console_to_bottom")
	call_deferred("focus_command_input")


func focus_command_input() -> void:
	_ensure_command_input()
	if _command_input != null:
		call_deferred("_restore_command_focus")


func _sanitize_narration_lines(lines: Array) -> Array[String]:
	var clean_lines: Array[String] = []
	for line in lines:
		var text := str(line).strip_edges()
		if text == "" or text == "Her:":
			continue
		clean_lines.append(text)
	return clean_lines


func _get_room_options(room_data: Dictionary) -> Array:
	var event_data_variant = room_data.get("event_data", {})
	if event_data_variant is Dictionary:
		var event_data: Dictionary = event_data_variant
		var buttons_variant = event_data.get("buttons", event_data.get("options", []))
		if buttons_variant is Array and not buttons_variant.is_empty():
			return buttons_variant

	var top_level_buttons = room_data.get("buttons", [])
	if top_level_buttons is Array and not top_level_buttons.is_empty():
		return top_level_buttons

	return [{"label": DEFAULT_OPTION_LABEL, "action": DEFAULT_OPTION_ACTION}]


func _append_label(text: String, is_heading: bool = false) -> void:
	var label := Label.new()
	label.text = text
	label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	label.clip_text = false
	label.text_overrun_behavior = TextServer.OVERRUN_NO_TRIMMING
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_LEFT
	label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	label.size_flags_vertical = Control.SIZE_SHRINK_BEGIN
	label.custom_minimum_size = Vector2(_console_content_width(), 0.0)
	if _console_font != null:
		label.add_theme_font_override("font", _console_font)
	label.add_theme_color_override("font_color", CONSOLE_TEXT_COLOR)
	label.add_theme_font_size_override("font_size", HEADING_FONT_SIZE if is_heading else BODY_FONT_SIZE)
	console_content.add_child(label)


func _append_button(option_data: Variant) -> void:
	if not option_data is Dictionary:
		return

	var option: Dictionary = option_data
	var button := Button.new()
	button.text = str(option.get("label", DEFAULT_OPTION_LABEL))
	button.custom_minimum_size = Vector2(0, _button_min_height_for_text(button.text))
	button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	button.size_flags_vertical = Control.SIZE_SHRINK_BEGIN
	button.flat = false
	button.focus_mode = Control.FOCUS_ALL
	button.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	button.clip_text = false
	button.text_overrun_behavior = TextServer.OVERRUN_NO_TRIMMING
	if _console_font != null:
		button.add_theme_font_override("font", _console_font)
	button.add_theme_font_size_override("font_size", BUTTON_FONT_SIZE)
	button.add_theme_color_override("font_color", CONSOLE_BUTTON_TEXT_COLOR)
	button.add_theme_color_override("font_hover_color", CONSOLE_BUTTON_TEXT_COLOR)
	button.add_theme_color_override("font_pressed_color", CONSOLE_BUTTON_TEXT_COLOR)
	button.add_theme_color_override("font_focus_color", CONSOLE_BUTTON_TEXT_COLOR)
	button.add_theme_color_override("font_disabled_color", CONSOLE_BUTTON_TEXT_COLOR.darkened(0.35))
	button.add_theme_stylebox_override("normal", _build_button_style(CONSOLE_BUTTON_COLOR))
	button.add_theme_stylebox_override("hover", _build_button_style(CONSOLE_BUTTON_COLOR.lightened(0.08)))
	button.add_theme_stylebox_override("pressed", _build_button_style(CONSOLE_BUTTON_COLOR.darkened(0.12)))
	button.add_theme_stylebox_override("disabled", _build_button_style(CONSOLE_BUTTON_COLOR.darkened(0.35)))
	button.add_theme_stylebox_override("focus", _build_button_style(CONSOLE_BUTTON_COLOR.lightened(0.14)))
	button.focus_mode = Control.FOCUS_NONE
	button.pressed.connect(_on_console_button_pressed.bind(str(option.get("action", DEFAULT_OPTION_ACTION))))
	console_content.add_child(button)


func _console_content_width() -> float:
	if console_content != null and console_content.custom_minimum_size.x > 0.0:
		return console_content.custom_minimum_size.x
	return max(_fullscreen_size.x - TERMINAL_MARGIN_X * 2.0, 0.0)


func _button_min_height_for_text(text: String) -> float:
	var width: float = max(_console_content_width() - BUTTON_TEXT_MARGIN_X, 1.0)
	var font_size: int = BUTTON_FONT_SIZE
	var line_count: int = 1
	if _console_font != null:
		var line := TextLine.new()
		line.add_string(text, _console_font, font_size)
		line_count = int(ceil(max(line.get_line_width(), width) / width))
	else:
		var approximate_chars_per_line: int = max(int(width / max(float(font_size) * 0.58, 1.0)), 1)
		line_count = int(ceil(float(text.length()) / float(approximate_chars_per_line)))
	return max(float(BUTTON_MIN_HEIGHT), float(line_count) * float(font_size) * 1.25 + BUTTON_TEXT_MARGIN_Y)


func _build_button_style(color: Color) -> StyleBoxFlat:
	var style := StyleBoxFlat.new()
	style.bg_color = color
	style.corner_radius_top_left = 10
	style.corner_radius_top_right = 10
	style.corner_radius_bottom_right = 10
	style.corner_radius_bottom_left = 10
	style.border_width_left = 2
	style.border_width_top = 2
	style.border_width_right = 2
	style.border_width_bottom = 2
	style.border_color = CONSOLE_BUTTON_BORDER_COLOR
	style.content_margin_left = 22
	style.content_margin_right = 22
	style.content_margin_top = 16
	style.content_margin_bottom = 16
	return style


func _on_console_button_pressed(action_id: String) -> void:
	console_option_selected.emit(action_id, _current_room_id)


func _ensure_command_input() -> void:
	if _command_input != null:
		return

	_command_input = get_node_or_null("CommandInput") as LineEdit
	if _command_input == null:
		_command_input = LineEdit.new()
		_command_input.name = "CommandInput"
		add_child(_command_input)

	_command_input.custom_minimum_size = Vector2(0, FULLSCREEN_INPUT_HEIGHT)
	_command_input.layout_mode = 2
	_command_input.size_flags_horizontal = Control.SIZE_EXPAND_FILL

	_command_input.placeholder_text = "Command, next, choice #, status, inventory."
	_command_input.clear_button_enabled = true
	_command_input.focus_mode = Control.FOCUS_ALL
	if _console_font != null:
		_command_input.add_theme_font_override("font", _console_font)
	_command_input.add_theme_font_size_override("font_size", INPUT_FONT_SIZE)
	_command_input.add_theme_color_override("font_color", COMMAND_INPUT_TEXT_COLOR)
	_command_input.add_theme_color_override("font_placeholder_color", COMMAND_INPUT_TEXT_COLOR.darkened(0.45))
	_command_input.add_theme_color_override("caret_color", COMMAND_INPUT_TEXT_COLOR)
	_command_input.add_theme_stylebox_override("normal", _build_input_style(COMMAND_INPUT_COLOR))
	_command_input.add_theme_stylebox_override("focus", _build_input_style(COMMAND_INPUT_COLOR.lightened(0.08)))
	if not _command_input.text_submitted.is_connected(_on_command_input_submitted):
		_command_input.text_submitted.connect(_on_command_input_submitted)
	if not _command_input.text_changed.is_connected(_on_command_input_changed):
		_command_input.text_changed.connect(_on_command_input_changed)
	if not _command_input.focus_exited.is_connected(_on_command_input_focus_exited):
		_command_input.focus_exited.connect(_on_command_input_focus_exited)


func _build_input_style(color: Color) -> StyleBoxFlat:
	var style := StyleBoxFlat.new()
	style.bg_color = color
	style.corner_radius_top_left = 6
	style.corner_radius_top_right = 6
	style.corner_radius_bottom_right = 6
	style.corner_radius_bottom_left = 6
	style.border_width_left = 1
	style.border_width_top = 1
	style.border_width_right = 1
	style.border_width_bottom = 1
	style.border_color = CONSOLE_TEXT_COLOR.darkened(0.25)
	style.content_margin_left = 12
	style.content_margin_right = 12
	style.content_margin_top = 8
	style.content_margin_bottom = 8
	return style


func _on_command_input_submitted(text: String) -> void:
	_submit_command_text(text)


func _on_command_input_changed(text: String) -> void:
	var trimmed := text.strip_edges()
	if trimmed != "":
		_last_command_input_text = trimmed
	else:
		_last_command_input_text = ""


func _on_command_input_focus_exited() -> void:
	call_deferred("_submit_pending_command_text")


func _submit_pending_command_text() -> void:
	if _command_input == null or _command_submission_in_progress:
		return
	if not _command_input.visible:
		return
	var pending_text := _command_input.text.strip_edges()
	if pending_text == "":
		pending_text = _last_command_input_text.strip_edges()
	if pending_text == "":
		return
	if _command_input.has_focus():
		return
	_submit_command_text(pending_text)


func _submit_command_text(text: String) -> void:
	if _command_submission_in_progress:
		return
	var command_text := text.strip_edges()
	if command_text == "":
		return
	_command_submission_in_progress = true
	_last_command_input_text = ""
	if _command_input != null:
		_command_input.clear()
	console_command_submitted.emit(command_text, _current_room_id)
	call_deferred("_clear_command_submission_guard")


func _clear_command_submission_guard() -> void:
	_command_submission_in_progress = false


func _restore_command_focus() -> void:
	await get_tree().process_frame
	await get_tree().process_frame
	if not is_inside_tree() or _command_input == null:
		return
	_command_input.grab_focus()
	_command_input.caret_column = _command_input.text.length()


func _scroll_console_to_bottom() -> void:
	console_scroll.scroll_vertical = int(console_scroll.get_v_scroll_bar().max_value)
