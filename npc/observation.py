"""
Observation builder for LLM-driven NPCs.
Creates compact world observations with local tile grids and entity information.
"""

import math
from typing import Dict, List, Tuple, Any, Optional


def world_to_tile(world_x: int, world_y: int, tile_size: int = 32) -> Tuple[int, int]:
    """Convert world coordinates to tile coordinates"""
    return world_x // tile_size, world_y // tile_size


def tile_to_world(tile_x: int, tile_y: int, tile_size: int = 32) -> Tuple[int, int]:
    """Convert tile coordinates to world coordinates"""
    return tile_x * tile_size, tile_y * tile_size


def build_observation(engine_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a compact observation for the NPC's LLM decision-making.
    
    Args:
        engine_state: Dictionary containing:
            - npc: NPC object with pos, hp, state info
            - player: Player object with pos, last_said
            - walls: List of wall rectangles
            - entities: List of interactive entities
            - tick: Current game tick
            - last_result: Result of last action
            - goals: List of current goals
            - cooldowns: Dict of action cooldowns
    
    Returns:
        Observation dictionary matching the specified format
    """
    try:
        npc = engine_state["npc"]
        player = engine_state["player"]
        walls = engine_state.get("walls", [])
        entities = engine_state.get("entities", [])
        tick = engine_state.get("tick", 0)
        last_result = engine_state.get("last_result")
        goals = engine_state.get("goals", ["greet player"])
        cooldowns = engine_state.get("cooldowns", {"move": 0, "interact": 0})
    except Exception as e:
        print(f"DEBUG: Error accessing engine_state: {e}")
        raise
    
    # Get NPC position in tile coordinates
    try:
        npc_tile_x, npc_tile_y = world_to_tile(npc.rect.centerx, npc.rect.centery)
        player_tile_x, player_tile_y = world_to_tile(player.rect.centerx, player.rect.centery)
    except Exception as e:
        print(f"DEBUG: Error getting tile coordinates: {e}")
        print(f"DEBUG: NPC rect: {npc.rect}")
        print(f"DEBUG: Player rect: {player.rect}")
        raise
    
    # Build 11x11 local tile grid centered on NPC
    grid_size = 11
    half_size = grid_size // 2
    
    # Calculate the top-left corner of the observation window
    origin_tile_x = npc_tile_x - half_size
    origin_tile_y = npc_tile_y - half_size
    origin_world_x, origin_world_y = tile_to_world(origin_tile_x, origin_tile_y)
    
    # Build the tile grid
    grid = []
    ascii_grid = []
    
    for row in range(grid_size):
        grid_row = ""
        ascii_row = ""
        
        for col in range(grid_size):
            tile_x = origin_tile_x + col
            tile_y = origin_tile_y + row
            world_x, world_y = tile_to_world(tile_x, tile_y)
            
            # Check what's at this tile
            tile_char = '.'  # Default: floor
            ascii_char = '.'
            
            # Check for walls
            tile_rect = {"x": world_x, "y": world_y, "width": 32, "height": 32}
            for wall in walls:
                if rectangles_overlap(tile_rect, wall):
                    tile_char = '#'
                    ascii_char = '#'
                    break
            
            # Check for doors (entities with "door" in their ID)
            for entity in entities:
                entity_tile_x, entity_tile_y = world_to_tile(entity.get("x", 0), entity.get("y", 0))
                if entity_tile_x == tile_x and entity_tile_y == tile_y:
                    if "door" in entity.get("id", "").lower():
                        tile_char = 'D'
                        ascii_char = 'D'
                        break
            
            # Add player and NPC to ASCII view only (not in the grid legend)
            if tile_x == player_tile_x and tile_y == player_tile_y:
                ascii_char = 'P'
            elif tile_x == npc_tile_x and tile_y == npc_tile_y:
                ascii_char = 'N'
            
            grid_row += tile_char
            ascii_row += ascii_char
        
        grid.append(grid_row)
        ascii_grid.append(ascii_row)
    
    # Find visible entities within the observation window
    visible_entities = []
    
    # Add player as a visible entity
    visible_entities.append({
        "id": "player",
        "kind": "player", 
        "pos": [player_tile_x, player_tile_y]
    })
    
    # Add other entities
    for entity in entities:
        entity_x = entity.get("x", 0)
        entity_y = entity.get("y", 0)
        entity_tile_x, entity_tile_y = world_to_tile(entity_x, entity_y)
        
        # Check if entity is within the observation window
        if (origin_tile_x <= entity_tile_x < origin_tile_x + grid_size and
            origin_tile_y <= entity_tile_y < origin_tile_y + grid_size):
            
            visible_entities.append({
                "id": entity.get("id", "unknown"),
                "kind": entity.get("kind", "unknown"),
                "pos": [entity_tile_x, entity_tile_y]
            })
    
    # Determine NPC state
    npc_state = "Idle"
    if hasattr(npc, 'current_action'):
        if npc.current_action == "patrol":
            npc_state = "Patrol"
        elif npc.is_moving:
            npc_state = "Approach"
        elif npc.speech_text:
            npc_state = "Talk"
    
    # Get player's last said message
    player_last_said = None
    if hasattr(player, 'speech_text') and player.speech_text:
        player_last_said = player.speech_text
    
    # Get NPC inventory for shopkeeper context
    npc_inventory = []
    if hasattr(npc, 'get_inventory_list'):
        npc_inventory = npc.get_inventory_list()
    
    # Build the observation
    observation = {
        "npc": {
            "pos": [npc_tile_x, npc_tile_y],
            "hp": getattr(npc, 'current_health', 100),
            "state": npc_state,
            "inventory": npc_inventory
        },
        "player": {
            "pos": [player_tile_x, player_tile_y],
            "last_said": player_last_said
        },
        "local_tiles": {
            "origin": [origin_tile_x, origin_tile_y],
            "grid": ascii_grid  # Use ASCII grid with N/P markers for better spatial understanding
        },
        "visible_entities": visible_entities,
        "goals": goals,
        "cooldowns": cooldowns,
        "last_result": last_result,
        "tick": tick
    }
    
    # *** DEBUG: Log the observation details ***
    print("=" * 60)
    print("DEBUG: OBSERVATION BUILT:")
    print(f"NPC position: tile ({npc_tile_x}, {npc_tile_y}) = world ({npc.rect.centerx}, {npc.rect.centery})")
    print(f"Player position: tile ({player_tile_x}, {player_tile_y}) = world ({player.rect.centerx}, {player.rect.centery})")
    print(f"Player last said: '{player_last_said}'")
    print(f"Grid origin: tile ({origin_tile_x}, {origin_tile_y}) = world ({origin_world_x}, {origin_world_y})")
    print(f"Visible entities: {len(visible_entities)}")
    print("ASCII Map:")
    for i, row in enumerate(ascii_grid):
        print(f"  {i:2d}: {row}")
    print("Grid (without characters):")
    for i, row in enumerate(grid):
        print(f"  {i:2d}: {row}")
    print("=" * 60)
    
    return observation


def rectangles_overlap(rect1: Dict[str, int], rect2) -> bool:
    """Check if two rectangles overlap"""
    # Handle pygame.Rect objects
    if hasattr(rect2, 'x'):
        r2_x, r2_y, r2_w, r2_h = rect2.x, rect2.y, rect2.width, rect2.height
    else:
        r2_x, r2_y, r2_w, r2_h = rect2["x"], rect2["y"], rect2["width"], rect2["height"]
    
    r1_x, r1_y, r1_w, r1_h = rect1["x"], rect1["y"], rect1["width"], rect1["height"]
    
    return not (r1_x + r1_w <= r2_x or r2_x + r2_w <= r1_x or 
                r1_y + r1_h <= r2_y or r2_y + r2_h <= r1_y)


def format_observation_for_llm(observation: Dict[str, Any]) -> str:
    """
    Format observation as a clean string for LLM consumption.
    """
    import json
    
    # Format the observation as JSON
    json_str = json.dumps(observation, indent=2)
    
    result = f"OBSERVATION:\n{json_str}"
    
    # Add explanation of grid symbols
    result += f"\n\nGRID LEGEND: N=NPC, P=Player, #=wall, .=floor, D=door"
    
    return result


# Test function
def test_observation_builder():
    """Test the observation builder with sample data"""
    
    # Mock objects for testing
    class MockRect:
        def __init__(self, x, y, width=32, height=32):
            self.x = x
            self.y = y
            self.width = width
            self.height = height
            self.centerx = x + width // 2
            self.centery = y + height // 2
    
    class MockCharacter:
        def __init__(self, x, y):
            self.rect = MockRect(x, y)
            self.current_health = 100
            self.is_moving = False
            self.speech_text = ""
            self.current_action = "idle"
    
    # Create test scenario
    npc = MockCharacter(320, 160)  # Tile (10, 5)
    player = MockCharacter(416, 160)  # Tile (13, 5)
    player.speech_text = "hello"
    
    walls = [
        MockRect(0, 0, 800, 32),      # Top boundary
        MockRect(0, 0, 32, 600),      # Left boundary
        MockRect(768, 0, 32, 600),    # Right boundary
        MockRect(0, 568, 800, 32),    # Bottom boundary
        MockRect(384, 64, 32, 32),    # A wall tile at (12, 2)
    ]
    
    entities = [
        {"id": "door_12_2", "kind": "door", "x": 384, "y": 64}
    ]
    
    engine_state = {
        "npc": npc,
        "player": player,
        "walls": walls,
        "entities": entities,
        "tick": 12345,
        "last_result": None,
        "goals": ["greet player"],
        "cooldowns": {"move": 0, "interact": 0}
    }
    
    # Build observation
    obs = build_observation(engine_state)
    
    # Print formatted observation
    print("=== TEST OBSERVATION ===")
    print(format_observation_for_llm(obs))
    print("\n=== RAW OBSERVATION ===")
    import json
    print(json.dumps(obs, indent=2))


if __name__ == "__main__":
    test_observation_builder()