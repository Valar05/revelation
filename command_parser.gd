extends RefCounted

const NUMBER_WORDS := {
	"1": 0,
	"one": 0,
	"won": 0,
	"2": 1,
	"two": 1,
	"too": 1,
	"to": 1,
	"tu": 1,
	"3": 2,
	"three": 2,
	"tree": 2,
	"free": 2,
	"4": 3,
	"four": 3,
	"for": 3,
	"fore": 3,
	"5": 4,
	"five": 4,
	"6": 5,
	"six": 5,
	"sex": 5,
	"7": 6,
	"seven": 6,
	"8": 7,
	"eight": 7,
	"ate": 7,
	"9": 8,
	"nine": 8
}

const GLOBAL_ALIASES := {
	"repeat": "repeat",
	"again": "repeat",
	"say again": "repeat",
	"read again": "repeat",
	"replay": "repeat",
	"repeat choices": "repeat_choices",
	"choices": "repeat_choices",
	"options": "repeat_choices",
	"read choices": "repeat_choices",
	"what are my choices": "repeat_choices",
	"status": "status",
	"stats": "status",
	"state": "status",
	"health": "status",
	"report": "status",
	"inventory": "inventory",
	"items": "inventory",
	"gear": "inventory",
	"symbiotes": "inventory",
	"mutations": "inventory",
	"help": "help",
	"commands": "help",
	"command": "help",
	"confirm": "confirm",
	"confirm action": "confirm",
	"confirm that action": "confirm",
	"yes": "confirm",
	"okay": "confirm",
	"ok": "confirm",
	"next": "proceed",
	"pause": "pause",
	"stop": "pause",
	"cancel": "cancel",
	"back": "cancel",
	"continue": "continue_audio",
	"resume": "continue_audio",
	"slower": "slower",
	"slow down": "slower",
	"speed down": "slower",
	"faster": "faster",
	"speed up": "faster"
}

const CONFIRMATION_THRESHOLD := 0.8
const DIRECT_MATCH_THRESHOLD := 0.92

const ACTION_ALIASES := {
	"combat": ["fight", "attack", "kill", "strike", "cut down", "engage"],
	"proceed": ["move", "go", "continue", "proceed", "advance", "walk", "leave"],
	"retreat": ["retreat", "withdraw", "back away", "fall back", "leave"],
	"browse_wares": ["approach", "scale", "scales", "merchant", "trade", "exchange"],
	"leave_merchant": ["withdraw", "leave merchant", "refuse merchant", "walk away"],
	"leave_symbiote": ["leave symbiote", "leave them", "no bond", "ignore symbiote"],
	"take_symbiote": ["bond", "take symbiote", "claim symbiote", "choose symbiote"],
	"activate_symbiote": ["activate", "use symbiote", "wake symbiote"],
	"drink_pool": ["drink", "drink pool"],
	"study_pool": ["study", "sample", "inspect"],
	"buy_mutation": ["buy", "purchase", "mutation", "take mutation"]
}

const TERM_REPLACEMENTS := {
	"b9nd": "bond",
	"b0nd": "bond",
	"activatr": "activate",
	"activare": "activate",
	"actuvate": "activate",
	"symbiot": "symbiote",
	"symbiotee": "symbiote",
	"symbiotes": "symbiote",
	"pheremones": "pheromones",
	"pherem9nes": "pheromones",
	"pharamones": "pheromones",
	"fair moans": "pheromones",
	"fairmones": "pheromones",
	"impermeabpe": "impermeable",
	"impermiable": "impermeable",
	"impenetrible": "impermeable",
	"impenetrable": "impermeable",
	"impermeble": "impermeable",
	"barrior": "barrier",
	"miyosis": "mitosis",
	"mitosys": "mitosis",
	"mighty osis": "mitosis",
	"blood hunntet": "blood hunter",
	"blood hunter": "blood hunter",
	"heaoth": "health",
	"biomads": "biomass",
	"biomas": "biomass"
}


func parse_command(raw_input: String, buttons: Array, context: Dictionary = {}) -> Dictionary:
	var normalized := normalize_command(raw_input)
	if normalized == "":
		return _unknown()

	var choice_index := _parse_choice_index(normalized)
	if choice_index >= 0:
		if choice_index < buttons.size():
			return _action_result(buttons[choice_index], 1.0, "number")
		return {
			"type": "unknown",
			"prompt": "That choice number is not available."
		}

	if GLOBAL_ALIASES.has(normalized):
		return {
			"type": "global",
			"command": str(GLOBAL_ALIASES[normalized]),
			"confidence": 1.0
		}

	var contextual_match := _resolve_contextual_shortcut(normalized, buttons, context)
	if not contextual_match.is_empty():
		return contextual_match

	var candidates := _build_candidates(buttons)
	var matches := _score_candidates(normalized, candidates)
	if matches.is_empty():
		return _unknown()

	var best: Dictionary = matches[0]
	var best_score := float(best.get("score", 0.0))
	if best_score < CONFIRMATION_THRESHOLD:
		return _unknown()

	if matches.size() > 1:
		var second: Dictionary = matches[1]
		var second_score := float(second.get("score", 0.0))
		if second_score >= 0.62 and best_score - second_score < 0.16:
			return {
				"type": "ambiguous",
				"prompt": _build_ambiguity_prompt(best, second),
				"matches": [best, second]
			}

	var result := _action_result(best.get("button", {}), best_score, str(best.get("source", "fuzzy")))
	if best_score < DIRECT_MATCH_THRESHOLD:
		result["needs_confirmation"] = true
		result["prompt"] = _build_confirmation_prompt(best)
	return result


func normalize_command(raw_input: String) -> String:
	var normalized := raw_input.strip_edges().to_lower()
	normalized = normalized.replace("0", "o")
	normalized = normalized.replace("3", "e")
	normalized = normalized.replace("4", "a")
	normalized = normalized.replace("5", "s")
	normalized = normalized.replace("6", "g")
	normalized = normalized.replace("8", "b")
	normalized = normalized.replace("9", "o")
	var punctuation := [".", ",", "!", "?", ":", ";", "\"", "'", "(", ")", "[", "]", "{", "}", "/", "\\", "-", "_"]
	for mark in punctuation:
		normalized = normalized.replace(mark, " ")
	normalized = " ".join(normalized.split(" ", false))
	for bad in TERM_REPLACEMENTS.keys():
		normalized = normalized.replace(str(bad), str(TERM_REPLACEMENTS[bad]))
	return " ".join(normalized.split(" ", false))


func _parse_choice_index(normalized: String) -> int:
	if NUMBER_WORDS.has(normalized):
		return int(NUMBER_WORDS[normalized])

	var tokens := normalized.split(" ", false)
	if tokens.size() == 2 and tokens[0] in ["choice", "option", "number"]:
		var second := str(tokens[1])
		if NUMBER_WORDS.has(second):
			return int(NUMBER_WORDS[second])
	if tokens.size() == 3 and tokens[0] == "choose":
		var third := str(tokens[2])
		if NUMBER_WORDS.has(third):
			return int(NUMBER_WORDS[third])
	return -1


func _build_confirmation_prompt(match: Dictionary) -> String:
	var button: Dictionary = match.get("button", {})
	var label := str(button.get("label", "that action")).strip_edges().trim_suffix(".")
	if label == "":
		label = "that action"
	return "I think you meant %s. Say confirm or cancel." % label


func _build_candidates(buttons: Array) -> Array[Dictionary]:
	var candidates: Array[Dictionary] = []
	for index in range(buttons.size()):
		var button = buttons[index]
		if not button is Dictionary:
			continue
		var button_data: Dictionary = button
		var label := str(button_data.get("label", ""))
		_add_candidate(candidates, label, button_data, index, "label")
		var action := str(button_data.get("action", ""))
		for alias in _aliases_for_action(action):
			_add_candidate(candidates, str(alias), button_data, index, "action")
		var voice_aliases = button_data.get("voice_aliases", [])
		if voice_aliases is Array:
			for alias in voice_aliases:
				_add_candidate(candidates, str(alias), button_data, index, "voice_alias")
		_add_label_token_candidates(candidates, label, button_data, index)
	return candidates


func _add_candidate(candidates: Array[Dictionary], phrase: String, button: Dictionary, index: int, source: String) -> void:
	var normalized := normalize_command(phrase)
	if normalized == "":
		return
	candidates.append({
		"phrase": normalized,
		"button": button,
		"index": index,
		"source": source
	})


func _add_label_token_candidates(candidates: Array[Dictionary], label: String, button: Dictionary, index: int) -> void:
	var normalized := normalize_command(label)
	var stop_words := {"the": true, "a": true, "an": true, "it": true, "them": true, "with": true, "to": true, "and": true}
	for token in normalized.split(" ", false):
		var text := str(token)
		if text.length() < 4 or stop_words.has(text):
			continue
		_add_candidate(candidates, text, button, index, "label_token")


func _aliases_for_action(action: String) -> Array[String]:
	var base_action := action
	if action.find(":") != -1:
		base_action = action.substr(0, action.find(":"))
	var aliases: Array[String] = []
	if ACTION_ALIASES.has(base_action):
		for alias in ACTION_ALIASES[base_action]:
			aliases.append(str(alias))
	if action.begins_with("take_symbiote:"):
		aliases.append(action.substr("take_symbiote:".length()).replace("_", " "))
	if action.begins_with("activate_symbiote:"):
		aliases.append(action.substr("activate_symbiote:".length()).replace("_", " "))
	if action.begins_with("buy_mutation:"):
		aliases.append(action.substr("buy_mutation:".length()).replace("_", " "))
	return aliases


func _resolve_contextual_shortcut(normalized: String, buttons: Array, context: Dictionary) -> Dictionary:
	var input_tokens := _meaningful_tokens(normalized)
	if input_tokens.is_empty():
		return {}

	var context_tokens := _context_tokens(context)
	var scored_buttons: Array[Dictionary] = []
	for index in range(buttons.size()):
		var button = buttons[index]
		if not button is Dictionary:
			continue
		var button_data: Dictionary = button
		var phrase_tokens := _button_tokens(button_data)
		if phrase_tokens.is_empty():
			continue

		var token_hits := 0
		for token in input_tokens:
			if phrase_tokens.has(token):
				token_hits += 1
		if token_hits == 0:
			continue

		var label := normalize_command(str(button_data.get("label", "")))
		var action := str(button_data.get("action", ""))
		var exact_phrase_bonus := 0.0
		if normalized == label:
			exact_phrase_bonus += 0.15
		if normalized == action:
			exact_phrase_bonus += 0.10

		var overlap_ratio := float(token_hits) / float(max(input_tokens.size(), 1))
		var context_hits := 0
		for token in phrase_tokens.keys():
			if context_tokens.has(token):
				context_hits += 1

		var specificity_bonus := 1.0 / float(max(phrase_tokens.size(), 1))
		var score = (overlap_ratio * 0.65) + min(0.20, float(context_hits) * 0.04) + min(0.10, specificity_bonus * 0.10) + exact_phrase_bonus
		var scored := button_data.duplicate(true)
		scored["score"] = score
		scored["token_hits"] = token_hits
		scored["index"] = index
		scored_buttons.append(scored)

	if scored_buttons.is_empty():
		return {}

	scored_buttons.sort_custom(func(a: Dictionary, b: Dictionary) -> bool:
		var left_score := float(a.get("score", 0.0))
		var right_score := float(b.get("score", 0.0))
		if left_score == right_score:
			var left_hits := int(a.get("token_hits", 0))
			var right_hits := int(b.get("token_hits", 0))
			if left_hits == right_hits:
				return int(a.get("index", 0)) < int(b.get("index", 0))
			return left_hits > right_hits
		return left_score > right_score
	)

	var best: Dictionary = scored_buttons[0]
	var best_score := float(best.get("score", 0.0))
	var best_hits := int(best.get("token_hits", 0))
	if scored_buttons.size() > 1:
		var second: Dictionary = scored_buttons[1]
		var second_score := float(second.get("score", 0.0))
		if abs(best_score - second_score) < 0.06 and int(second.get("token_hits", 0)) == best_hits:
			return {
				"type": "ambiguous",
				"prompt": _build_ambiguity_prompt(best, second),
				"matches": [best, second]
			}

	if best_score >= 0.58 or input_tokens.size() <= 2:
		return _action_result(best.get("button", {}), 1.0, "contextual_shortcut")
	return {}


func _button_tokens(button: Dictionary) -> Dictionary:
	var tokens := {}
	_add_tokens_from_phrase(tokens, str(button.get("label", "")))
	var action := str(button.get("action", ""))
	_add_tokens_from_phrase(tokens, action.replace("_", " "))
	if action.find(":") != -1:
		_add_tokens_from_phrase(tokens, action.substr(0, action.find(":")).replace("_", " "))
		_add_tokens_from_phrase(tokens, action.substr(action.find(":") + 1).replace("_", " "))
	for alias in _aliases_for_action(action):
		_add_tokens_from_phrase(tokens, alias)
	var voice_aliases = button.get("voice_aliases", [])
	if voice_aliases is Array:
		for alias in voice_aliases:
			_add_tokens_from_phrase(tokens, str(alias))
	return tokens


func _context_tokens(context: Dictionary) -> Dictionary:
	var tokens := {}
	var lines = context.get("lines", [])
	if lines is Array:
		for line in lines:
			_add_tokens_from_phrase(tokens, str(line))
	var room_id := str(context.get("room_id", ""))
	_add_tokens_from_phrase(tokens, room_id.replace("_", " "))
	return tokens


func _add_tokens_from_phrase(tokens: Dictionary, phrase: String) -> void:
	var normalized := normalize_command(phrase)
	if normalized == "":
		return
	for token in normalized.split(" ", false):
		var text := str(token).strip_edges()
		if text == "":
			continue
		tokens[text] = true


func _meaningful_tokens(text: String) -> Array[String]:
	var result: Array[String] = []
	var stop_words := {"the": true, "a": true, "an": true, "to": true, "and": true, "of": true, "in": true, "on": true, "at": true, "for": true, "my": true, "me": true}
	for token in text.split(" ", false):
		var word := str(token).strip_edges()
		if word == "" or stop_words.has(word):
			continue
		result.append(word)
	return result


func _score_candidates(normalized: String, candidates: Array[Dictionary]) -> Array[Dictionary]:
	var best_by_action: Dictionary = {}
	for candidate in candidates:
		var phrase := str(candidate.get("phrase", ""))
		var score := _score_phrase(normalized, phrase)
		if score <= 0.0:
			continue
		var button: Dictionary = candidate.get("button", {})
		var action := str(button.get("action", ""))
		var existing: Dictionary = best_by_action.get(action, {})
		if existing.is_empty() or score > float(existing.get("score", 0.0)):
			var scored := candidate.duplicate(true)
			scored["score"] = score
			best_by_action[action] = scored

	var matches: Array[Dictionary] = []
	for action in best_by_action.keys():
		matches.append(best_by_action[action])
	matches.sort_custom(func(a: Dictionary, b: Dictionary) -> bool:
		return float(a.get("score", 0.0)) > float(b.get("score", 0.0))
	)
	return matches


func _score_phrase(input_text: String, phrase: String) -> float:
	if input_text == phrase:
		return 1.0
	if input_text.begins_with(phrase) or phrase.begins_with(input_text):
		var shorter = min(input_text.length(), phrase.length())
		var longer = max(input_text.length(), phrase.length())
		return 0.78 + 0.16 * (float(shorter) / float(max(longer, 1)))
	if input_text.find(phrase) != -1 or phrase.find(input_text) != -1:
		var shorter_contains = min(input_text.length(), phrase.length())
		var longer_contains = max(input_text.length(), phrase.length())
		return 0.68 + 0.16 * (float(shorter_contains) / float(max(longer_contains, 1)))

	var token_score := _token_overlap_score(input_text, phrase)
	var distance_score := _edit_similarity(input_text, phrase)
	return max(token_score, distance_score)


func _token_overlap_score(a: String, b: String) -> float:
	var a_tokens := _token_set(a)
	var b_tokens := _token_set(b)
	if a_tokens.is_empty() or b_tokens.is_empty():
		return 0.0
	var overlap := 0
	for token in a_tokens.keys():
		if b_tokens.has(token):
			overlap += 1
	var larger = max(a_tokens.size(), b_tokens.size())
	return float(overlap) / float(max(larger, 1))


func _token_set(text: String) -> Dictionary:
	var tokens := {}
	for token in text.split(" ", false):
		var item := str(token)
		if item != "":
			tokens[item] = true
	return tokens


func _edit_similarity(a: String, b: String) -> float:
	var max_len = max(a.length(), b.length())
	if max_len == 0:
		return 1.0
	var distance := _levenshtein_distance(a, b)
	return 1.0 - (float(distance) / float(max_len))


func _levenshtein_distance(a: String, b: String) -> int:
	var previous: Array[int] = []
	for j in range(b.length() + 1):
		previous.append(j)
	for i in range(1, a.length() + 1):
		var current: Array[int] = [i]
		for j in range(1, b.length() + 1):
			var cost := 0 if a[i - 1] == b[j - 1] else 1
			current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + cost))
		previous = current
	return previous[b.length()]


func _action_result(button_data: Variant, confidence: float, source: String) -> Dictionary:
	if not button_data is Dictionary:
		return _unknown()
	var button: Dictionary = button_data
	return {
		"type": "action",
		"action": str(button.get("action", "")),
		"label": str(button.get("label", "")),
		"confidence": confidence,
		"source": source
	}


func _unknown() -> Dictionary:
	return {
		"type": "unknown",
		"prompt": "I did not match that."
	}


func _build_ambiguity_prompt(first: Dictionary, second: Dictionary) -> String:
	var first_label := str(first.get("button", {}).get("label", "first choice"))
	var second_label := str(second.get("button", {}).get("label", "second choice"))
	return "I matched two commands: %s, or %s. Say a choice number." % [first_label, second_label]
