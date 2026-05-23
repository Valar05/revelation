extends Node

signal pulse(current_bpm: float)

const MIN_BPM := 0.1

@export_range(1.0, 300.0, 0.1) var bpm: float = 20.0

var _elapsed := 0.0


func _ready() -> void:
	add_to_group("heart_manager")


func _process(delta: float) -> void:
	_elapsed += delta

	var interval := get_pulse_interval()
	while _elapsed >= interval:
		_elapsed -= interval
		pulse.emit(bpm)


func get_pulse_interval() -> float:
	return 60.0 / max(bpm, MIN_BPM)


func trigger_pulse() -> void:
	_elapsed = 0.0
	pulse.emit(bpm)