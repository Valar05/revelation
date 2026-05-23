# Revelation Credit-Streamlined Generation

## Rule

Use paid model calls for compact creative blueprints, not final Godot patch assembly.

The stack should minimize context bloat and maximize useful writing instruction:

- send selected corpus fragments, not the whole corpus;
- send concise project rules, not every design document;
- require a deployable blueprint shape;
- compile deterministic boilerplate locally;
- validate locally before any critique pass;
- avoid paid critique for obviously invalid output.

## Default Flow

1. Select 3-6 corpus fragments.
2. Run a dry budget check with `tools/revelation_blueprint_agent.py --dry-run`.
3. Generate one blueprint with Claude Sonnet only if the input budget is acceptable.
4. Validate the blueprint locally.
5. Compile the blueprint to a scenario patch locally.
6. Run project validation and the Revelation auditor.

## Guardrails

The blueprint agent has a hard input budget. If it trips, shrink the corpus packet or prompt.

The model is responsible for:

- modern incident logic;
- root sin or moral failure;
- religious structural specificity;
- procedural plausibility;
- character-owned plans;
- readable prose;
- resolution and cooldown interlude intent.

The compiler is responsible for:

- patch shape;
- room/event placement;
- deck pool entries;
- repeated corpus anchors;
- final JSON formatting.

## Credit Discipline

Do not send the full room database, full event database, or full corpus to the model for room drafting.

Do not ask the model to critique a room that failed basic schema validation. Fix the schema contract, compiler, or prompt first.

Do not generate multiple variants until one variant can pass the blueprint validator and compiler path.
