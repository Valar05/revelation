extends SceneTree

const WorldScene := preload("res://world.tscn")


func _init() -> void:
	var world := WorldScene.instantiate()
	root.add_child(world)
	for index in range(12):
		await process_frame

	var dashboard := world.get_node_or_null("ShipDashboard")
	var backdrop := world.get_node_or_null("ShipDashboard/FullscreenBackdrop")
	var console := world.get_node_or_null("ShipDashboard/Console")
	var console_content := world.get_node_or_null("ShipDashboard/Console/ConsoleContent")
	var command_input := world.get_node_or_null("ShipDashboard/CommandInput")
	var room_sprite := world.get_node_or_null("RoomSprite")
	var player_avatar := world.get_node_or_null("PlayerAvatar")

	if dashboard == null or console == null or command_input == null:
		push_error("Text-only UI nodes are missing.")
		quit(1)
		return

	var dashboard_sprite := dashboard as Sprite2D
	if dashboard_sprite == null or dashboard_sprite.texture == null:
		push_error("Dashboard sprite background is missing.")
		quit(1)
		return

	if backdrop != null and backdrop.visible:
		push_error("TextureRect backdrop should not replace the dashboard sprite background.")
		quit(1)
		return

	if float(dashboard_sprite.self_modulate.a) < 0.99:
		push_error("Dashboard sprite should be visible as the background.")
		quit(1)
		return

	var texture_size := dashboard_sprite.texture.get_size()
	if texture_size.x < 800.0 or texture_size.y < 1800.0:
		push_error("Dashboard did not load the Nightmare Voyage portrait texture: %s." % str(texture_size))
		quit(1)
		return
	var sprite_width := texture_size.x * absf(dashboard_sprite.scale.x)
	var sprite_height := texture_size.y * absf(dashboard_sprite.scale.y)
	var sprite_left := dashboard_sprite.global_position.x - sprite_width * 0.5
	var sprite_top := dashboard_sprite.global_position.y - sprite_height * 0.5
	var sprite_right := dashboard_sprite.global_position.x + sprite_width * 0.5
	var sprite_bottom := dashboard_sprite.global_position.y + sprite_height * 0.5
	if sprite_left > 1.0 or sprite_top > 1.0 or sprite_right < 1079.0 or sprite_bottom < 1919.0:
		push_error("Dashboard sprite does not cover the viewport: left %.1f top %.1f right %.1f bottom %.1f." % [sprite_left, sprite_top, sprite_right, sprite_bottom])
		quit(1)
		return

	if sprite_top > 4.0 or sprite_bottom < 1916.0:
		push_error("Portrait dashboard sprite does not cover the viewport vertically: top %.1f bottom %.1f." % [sprite_top, sprite_bottom])
		quit(1)
		return
	if dashboard_sprite.global_position.y > 1300.0 and dashboard_sprite.scale.y < 2.0:
		push_error("Dashboard transform still matches the old bottom-half animation: position %s scale %s." % [str(dashboard_sprite.global_position), str(dashboard_sprite.scale)])
		quit(1)
		return

	if room_sprite != null and room_sprite.visible:
		push_error("Room sprite should be hidden for text-only presentation.")
		quit(1)
		return
	if player_avatar != null and player_avatar.visible:
		push_error("Player avatar sprite should be hidden for text-only presentation.")
		quit(1)
		return

	var console_rect: Rect2 = console.get_global_rect()
	var console_width := console_rect.size.x
	var console_height := console_rect.size.y
	if console_width < 800.0 or console_height < 1200.0:
		push_error("Console does not cover enough of the viewport: %.1fx%.1f." % [console_width, console_height])
		quit(1)
		return
	if console_rect.position.y > 130.0 or console_rect.end.y < 1400.0:
		push_error("Console should fill the paper terminal area: %s." % str(console_rect))
		quit(1)
		return

	var input_rect: Rect2 = command_input.get_global_rect()
	var input_height := input_rect.size.y
	if input_height < 70.0:
		push_error("Command input is too small for the text-only layout.")
		quit(1)
		return

	var first_label: Label = null
	var first_button: Button = null
	if console_content != null:
		for child in console_content.get_children():
			if first_label == null and child is Label:
				first_label = child
			if child is Button:
				first_button = child
				break

	if first_label == null or not first_label.has_theme_font_override("font"):
		push_error("Narration label is missing the Nightmare Voyage font override.")
		quit(1)
		return

	if first_button == null:
		push_error("No command button was rendered.")
		quit(1)
		return

	if not first_button.has_theme_font_override("font") or not command_input.has_theme_font_override("font"):
		push_error("Command controls are missing the Nightmare Voyage font override.")
		quit(1)
		return

	var normal_style := first_button.get_theme_stylebox("normal") as StyleBoxFlat
	if normal_style == null:
		push_error("Command button is missing its normal stylebox.")
		quit(1)
		return

	if normal_style.bg_color.v > 0.35:
		push_error("Command button normal style should read as dark ink on paper: %s." % normal_style.bg_color)
		quit(1)
		return

	var long_line := "Ross is in the surface van with the evidence bag on the seat beside him. He has not put it in the transfer case yet. The seal is intact. He is reading the log timestamps again."
	var long_button := "Wait for command confirmation before moving the evidence bag into the transfer case"
	dashboard.call("show_console", [long_line], [{"label": long_button, "action": "wait"}], "layout_smoke")
	for index in range(4):
		await process_frame

	var wrapped_label: Label = null
	var wrapped_button: Button = null
	for child in console_content.get_children():
		if wrapped_label == null and child is Label:
			wrapped_label = child
		if wrapped_button == null and child is Button:
			wrapped_button = child

	if wrapped_label == null or wrapped_label.text.ends_with("...") or wrapped_label.text_overrun_behavior != TextServer.OVERRUN_NO_TRIMMING:
		push_error("Narration label should preserve full wrapped text without ellipsis.")
		quit(1)
		return
	if wrapped_button == null or wrapped_button.text != long_button:
		push_error("Command button should preserve its full label.")
		quit(1)
		return
	if wrapped_button.text_overrun_behavior != TextServer.OVERRUN_NO_TRIMMING or wrapped_button.autowrap_mode == TextServer.AUTOWRAP_OFF:
		push_error("Command button should wrap instead of trimming.")
		quit(1)
		return
	if wrapped_button.custom_minimum_size.y <= 96.0:
		push_error("Long command button did not grow vertically for wrapped text.")
		quit(1)
		return

	print("TEXT_ONLY_UI_SMOKE_OK")
	quit(0)
