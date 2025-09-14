# LLM-Driven NPC System

This system implements reliable LLM-driven NPC behavior using strict tool-use patterns. The NPC's LLM selects ONE action per turn from a defined toolset, with the game engine maintaining authority over physics and pathfinding.

## Architecture Overview

The system consists of four main modules:

1. **Observation Builder** (`npc/observation.py`) - Creates compact world observations
2. **Action Schema** (`npc/actions.py`) - Defines and validates LLM actions  
3. **LLM Client** (`npc/llm_client.py`) - Communicates with local LLM endpoint
4. **NPC Controller** (`npc/controller.py`) - Orchestrates the decision loop

## Decision Loop

```
1. Build Observation → 2. Call LLM → 3. Parse/Validate → 4. Execute Action → 5. Store Result
     ↑                                                                            ↓
     ←←←←←←←←←←←←←←←←←←←← Feed back result for next turn ←←←←←←←←←←←←←←←←←←←←←←←←
```

## Observation Format

The LLM receives a JSON observation with local, relevant information:

```json
{
  "npc": {"pos": [10, 5], "hp": 100, "state": "Idle"},
  "player": {"pos": [13, 5], "last_said": "hello"},
  "local_tiles": {
    "origin": [5, 0],
    "grid": [
      "###########",
      "#.........#", 
      "#...D.....#",
      "#....#....#",
      "#....#....#",
      "#..N.P....#",
      "#.........#",
      "#.........#", 
      "#.........#",
      "#.........#",
      "###########"
    ]
  },
  "visible_entities": [{"id": "door_12_2", "kind": "door", "pos": [12, 2]}],
  "goals": ["greet player"],
  "cooldowns": {"move": 0, "interact": 0},
  "last_result": null,
  "tick": 12345
}
```

### Tile Legend
- `#` = wall
- `.` = floor  
- `D` = closed door
- `N` = NPC (ASCII view only)
- `P` = Player (ASCII view only)

## Action API

The LLM must output exactly ONE JSON action per turn:

### Available Actions

**say(text)**
```json
{"action": "say", "args": {"text": "Welcome, traveler!"}}
```

**move_dir(direction)**
```json
{"action": "move_dir", "args": {"direction": "N"}}
```
Valid directions: `"N"`, `"E"`, `"S"`, `"W"`

**move_to(x, y)**
```json
{"action": "move_to", "args": {"x": 15, "y": 8}}
```
Target coordinates in tile space. Engine runs pathfinding and moves ≤1 step per tick.

**interact(entity_id)**
```json
{"action": "interact", "args": {"entity_id": "door_12_2"}}
```

**transfer_item(entity_id, item_id)**
```json
{"action": "transfer_item", "args": {"entity_id": "player", "item_id": "health_potion"}}
```

## Result Feedback

The engine returns standardized result strings:

- `"ok"` - Action succeeded
- `"blocked:wall"` - Movement blocked by wall
- `"blocked:too_far"` - Target out of range
- `"no_path"` - No valid path to target
- `"cooldown"` - Action on cooldown
- `"invalid:reason"` - Invalid action/parameters
- `"parse_error"` - Failed to parse LLM output

## Configuration

Set these environment variables:

```bash
LOCAL_LLM_MODEL=Qwen3-4B-2507
LLM_TEMP=0.25
LLM_ENDPOINT=http://127.0.0.1:1234/v1/chat/completions
```

## Usage

### Basic Integration

```python
from npc.controller import NPCController
from zelda_game_llm_integration import create_llm_shopkeeper

# Create LLM-driven NPC
shopkeeper = create_llm_shopkeeper(400, 250)

# Configure behavior - by default, only responds when spoken to
shopkeeper.llm_controller.enable_idle_behavior(False)

# In your game loop
def update_game(dt):
    # Update NPC with LLM decisions
    shopkeeper.update(dt, walls, characters, player)
```

### Idle Behavior Control

```python
# Enable idle behavior (thinking out loud, random movement)
shopkeeper.llm_controller.enable_idle_behavior(True, speech_chance=0.1)

# Disable idle behavior (only respond when spoken to)
shopkeeper.llm_controller.enable_idle_behavior(False)

# Check current state
if shopkeeper.llm_controller.idle_behavior_enabled:
    print("NPC will occasionally act on its own")
```

### Custom NPC

```python
from npc.controller import NPCController

class MyNPC:
    def __init__(self, x, y):
        # ... initialize NPC properties ...
        self.llm_controller = NPCController(self)
        self.llm_controller.set_goals(["patrol area", "help players"])
    
    def update(self, dt, walls, characters, player):
        engine_state = {
            "npc": self,
            "player": player,
            "walls": walls,
            "entities": [],
            "characters": characters,
            "current_time": time.time() * 1000,
            "player_spoke": player_just_spoke,
            "tick": current_tick
        }
        
        result = self.llm_controller.npc_decision_tick(engine_state)
        if result:
            print(f"NPC action result: {result}")
```

## Testing

Run the test suite:

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test categories
python -m pytest tests/test_actions.py -v          # Schema validation
python -m pytest tests/test_blocked_move.py -v     # Movement collision
python -m pytest tests/test_move_to_step.py -v     # Pathfinding
python -m pytest tests/test_parse_error.py -v      # Error handling

# Run LLM integration tests (requires running LLM server)
python -m pytest tests/test_golden_llm.py -v

# Skip LLM tests
SKIP_LLM_TESTS=true python -m pytest tests/ -v
```

## Error Handling

The system includes robust error handling:

- **Parse Errors**: Invalid JSON → `"parse_error"` → retry with backoff
- **Schema Validation**: Invalid actions → `"invalid:reason"` → adapt behavior  
- **Execution Errors**: Blocked actions → `"blocked:reason"` → try alternatives
- **Rate Limiting**: Max 2 retries per decision, cooldowns prevent thrashing
- **Backoff**: After 3 consecutive errors, pause decisions briefly

## Performance Guidelines

- **Observation Size**: Keep ≤4KB (11x11 tile window)
- **Decision Frequency**: Every 4-10 game ticks (not every frame)
- **LLM Timeout**: 10 seconds with 2 retries
- **Temperature**: 0.2-0.5 for stable behavior
- **Token Limit**: ~150 tokens per response

## Character Prompt

The system includes a pre-configured shopkeeper character (Garruk Ironhand) with this personality:

> Grizzled, war-scarred shopkeeper on Faerun's Sword Coast. Gravelly voice, blunt manner, impatient. Uses medieval-fantasy diction with short, rough sentences. Discusses inventory, haggling, and local rumors. Keeps dialogue under 10 words when speaking aloud.

## Behavior Control

**Default Behavior:** NPCs only respond when spoken to by the player.

**Idle Behavior:** Can be enabled for occasional autonomous actions:
```python
# Enable thinking out loud and random movement
npc.llm_controller.enable_idle_behavior(True, speech_chance=0.2)

# Disable for response-only behavior  
npc.llm_controller.enable_idle_behavior(False)
```

**Settings:**
- `idle_behavior_enabled`: Whether NPC acts autonomously (default: False)
- `idle_speech_chance`: Probability of speaking during idle decisions (0.0-1.0)
- `decision_interval`: Base time between decisions (4000ms default)
- Idle decisions occur much less frequently (8x interval) when enabled

## Local LLM Setup

1. Install a local LLM server (e.g., LM Studio, Ollama, or text-generation-webui)
2. Start server on `http://127.0.0.1:1234`
3. Load a capable model (4B+ parameters recommended)
4. Ensure OpenAI-compatible API endpoint at `/v1/chat/completions`

## Troubleshooting

**LLM not responding:**
- Check server is running on correct port
- Verify endpoint URL in environment variables
- Test connection with `python -c "from npc.llm_client import LLMClient; print(LLMClient().test_connection())"`

**Parse errors:**
- Check LLM temperature (too high = inconsistent output)
- Verify model supports instruction following
- Review system prompt for clarity

**Movement issues:**
- Check collision detection in `move()` method
- Verify wall rectangles are properly defined
- Test pathfinding with simple scenarios

**Performance issues:**
- Reduce decision frequency (increase `decision_interval`)
- Optimize observation size (smaller tile window)
- Use faster local model

## Extension Points

The system is designed for easy extension:

- **New Actions**: Add to `actions.py` schema and `controller.py` execution
- **Enhanced Pathfinding**: Implement A* in `move_to` execution
- **Memory System**: Extend controller with persistent memory
- **Multi-NPC**: Create multiple controllers with different personalities
- **Dynamic Goals**: Update NPC goals based on game events

## Files Overview

```
npc/
├── __init__.py           # Module initialization
├── actions.py            # Action schema and validation
├── observation.py        # World observation builder  
├── llm_client.py         # LLM communication
└── controller.py         # Main decision loop

tests/
├── test_actions.py       # Schema validation tests
├── test_blocked_move.py  # Movement collision tests
├── test_move_to_step.py  # Pathfinding tests
├── test_parse_error.py   # Error handling tests
└── test_golden_llm.py    # LLM integration tests

zelda_game_llm_integration.py  # Integration example
README_LLM_NPC.md             # This documentation
```

This system provides a robust foundation for LLM-driven NPCs that can navigate, communicate, and interact reliably within your game world while maintaining strict boundaries between AI decision-making and engine authority.