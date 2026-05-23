extends Node2D

const DISSOLVE_PARAMETER := "dissolve_progress"

@export var damage := 8
@export var armor := 2
@export var shield := 6
@export var health := 30
@export_range(0.0, 1.0, 0.01) var ambush_chance := 0.15
@export_range(0.0, 1.0, 0.01) var initiative := 0.6
@export_range(0.01, 5.0, 0.01) var speed := 1.0

@onready var sprite: Sprite2D = $Sprite
@onready var combat_sprite: Sprite2D = $CombatSprite
@onready var attack_sprite: Sprite2D = $AttackSprite
@onready var animation_player: AnimationPlayer = $AnimationPlayer

var _base_scale := Vector2.ONE


# Called when the node enters the scene tree for the first time.
func _ready() -> void:
	_base_scale = scale
	reset_visuals()
	animation_player.play("idle")


func get_combat_stats(overrides: Dictionary = {}) -> Dictionary:
	var stats := {
		"damage": damage,
		"armor": armor,
		"shield": shield,
		"health": health,
		"ambush_chance": ambush_chance,
		"initiative": initiative,
		"speed": speed
	}
	for key in overrides.keys():
		stats[key] = overrides[key]
	return stats


func reset_visuals() -> void:
	visible = true
	sprite.visible = true
	combat_sprite.visible = false
	attack_sprite.visible = false
	scale = Vector2(absf(_base_scale.x), absf(_base_scale.y))
	_reset_dissolve()


func show_combat_pose(face_left: bool) -> void:
	visible = true
	sprite.visible = false
	combat_sprite.visible = true
	attack_sprite.visible = false
	set_facing(face_left)
	_reset_dissolve()
	if animation_player.has_animation("combat_idle"):
		animation_player.play("combat_idle")


func show_attack_pose(face_left: bool) -> void:
	visible = true
	sprite.visible = false
	combat_sprite.visible = false
	attack_sprite.visible = true
	set_facing(face_left)
	_reset_dissolve()


func show_world_pose(face_left: bool = false) -> void:
	visible = true
	sprite.visible = true
	combat_sprite.visible = false
	attack_sprite.visible = false
	set_facing(face_left)
	_reset_dissolve()
	if animation_player.has_animation("idle"):
		animation_player.play("idle")


func set_facing(face_left: bool) -> void:
	var horizontal_sign := -1.0 if face_left else 1.0
	scale = Vector2(absf(_base_scale.x) * horizontal_sign, absf(_base_scale.y))


func set_dissolve_progress(value: float) -> void:
	for target_sprite in [sprite, combat_sprite, attack_sprite]:
		var shader_material := target_sprite.material as ShaderMaterial
		if shader_material != null:
			shader_material.set_shader_parameter(DISSOLVE_PARAMETER, clamp(value, 0.0, 1.0))


func hide_actor() -> void:
	visible = false


func _reset_dissolve() -> void:
	set_dissolve_progress(0.0)
