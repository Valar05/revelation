class_name CombatSystem
extends RefCounted


static func simulate_combat(player_stats: Dictionary, enemy_stats: Dictionary, rng: RandomNumberGenerator) -> Dictionary:
	var player := _normalize_stats(player_stats)
	var enemy := _normalize_stats(enemy_stats)
	var player_starting_health: int = player.health
	var player_starting_shield: int = player.shield
	var enemy_starting_health: int = enemy.health
	var enemy_starting_shield: int = enemy.shield
	var combat_log: Array[String] = []
	var turns: int = 0
	var player_gauge := 0.0
	var enemy_gauge := 0.0
	var turn_gauge := 100.0
	var max_turns := 500

	var ambush_triggered: bool = rng.randf() < float(player.ambush_chance)
	if ambush_triggered:
		var ambush_result := _apply_attack(player, enemy)
		combat_log.append("Ambush strike for %d total damage." % ambush_result.total_damage)

	while player.health > 0 and enemy.health > 0 and turns < max_turns:
		var player_speed: float = max(float(player.speed), 0.01)
		var enemy_speed: float = max(float(enemy.speed), 0.01)
		var player_time: float = (turn_gauge - player_gauge) / player_speed
		var enemy_time: float = (turn_gauge - enemy_gauge) / enemy_speed
		var elapsed: float = min(player_time, enemy_time)
		player_gauge += player_speed * elapsed
		enemy_gauge += enemy_speed * elapsed

		var player_ready: bool = player_gauge >= turn_gauge or is_equal_approx(player_gauge, turn_gauge)
		var enemy_ready: bool = enemy_gauge >= turn_gauge or is_equal_approx(enemy_gauge, turn_gauge)
		var player_acts: bool = player_ready and (not enemy_ready or player_speed >= enemy_speed)
		if player_acts:
			player_gauge -= turn_gauge
			turns += 1
			var player_turn := _apply_attack(player, enemy)
			combat_log.append("Turn %d: player hits for %d total damage." % [turns, player_turn.total_damage])
		else:
			enemy_gauge -= turn_gauge
			turns += 1
			var enemy_turn := _apply_attack(enemy, player)
			combat_log.append("Turn %d: enemy hits for %d total damage." % [turns, enemy_turn.total_damage])
			if enemy_turn.total_damage > 0 and int(player.contact_damage) > 0:
				var contact_result := _apply_attack({"damage": player.contact_damage}, enemy)
				combat_log.append("Contact damage returns %d total damage." % contact_result.total_damage)

	return {
		"ambush_triggered": ambush_triggered,
		"initiative_winner": "atb",
		"player_won": player.health > 0 and enemy.health <= 0,
		"enemy_won": enemy.health > 0 and player.health <= 0,
		"rounds": turns,
		"turns": turns,
		"player_damage_taken": player_starting_health - player.health,
		"player_shield_lost": player_starting_shield - player.shield,
		"player_remaining_health": player.health,
		"player_remaining_shield": player.shield,
		"enemy_damage_taken": enemy_starting_health - enemy.health,
		"enemy_remaining_health": enemy.health,
		"enemy_remaining_shield": enemy.shield,
		"enemy_shield_lost": enemy_starting_shield - enemy.shield,
		"combat_log": combat_log
	}


static func _normalize_stats(stats: Dictionary) -> Dictionary:
	return {
		"damage": int(stats.get("damage", 1)),
		"armor": int(stats.get("armor", 0)),
		"shield": int(stats.get("shield", 0)),
		"health": int(stats.get("health", 1)),
		"ambush_chance": clamp(float(stats.get("ambush_chance", 0.0)), 0.0, 1.0),
		"initiative": clamp(float(stats.get("initiative", 0.5)), 0.0, 1.0),
		"speed": max(float(stats.get("speed", 1.0)), 0.01),
		"contact_damage": int(stats.get("contact_damage", 0))
	}


static func _roll_initiative(player: Dictionary, enemy: Dictionary, rng: RandomNumberGenerator) -> String:
	var player_score: float = rng.randf() + float(player.initiative)
	var enemy_score: float = rng.randf() + float(enemy.initiative)
	if is_equal_approx(player_score, enemy_score):
		return "player" if rng.randf() < 0.5 else "enemy"
	return "player" if player_score > enemy_score else "enemy"


static func _apply_attack(attacker: Dictionary, defender: Dictionary) -> Dictionary:
	var mitigated_damage: int = max(int(attacker.damage) - int(defender.armor), 0)
	var shield_damage: int = min(int(defender.shield), mitigated_damage)
	defender.shield -= shield_damage
	var health_damage: int = max(mitigated_damage - shield_damage, 0)
	defender.health = max(defender.health - health_damage, 0)
	return {
		"total_damage": shield_damage + health_damage,
		"health_damage": health_damage,
		"shield_damage": shield_damage
	}
