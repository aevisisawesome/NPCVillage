#!/usr/bin/env python3
"""
Debug the observation building to see why ASCII map and entities aren't updating.
"""

from zelda_game_llm_integration import create_llm_shopkeeper
from npc.observation import build_observation
import pygame
import json

pygame.init()

def test_observation_debug():
    """Test observation building with different scenarios"""
    
    print("🔍 Observation Debug Test")
    print("=" * 60)
    
    npc = create_llm_shopkeeper(400, 250)
    
    # Test 1: Basic observation with player movement
    print("\n📍 TEST 1: Player at different positions")
    
    positions = [
        (450, 250, "Player to the right"),
        (350, 250, "Player to the left"), 
        (400, 200, "Player above"),
        (400, 300, "Player below"),
    ]
    
    for px, py, description in positions:
        print(f"\n{description}:")
        
        class MockPlayer:
            def __init__(self, x, y, speech=""):
                self.rect = pygame.Rect(x, y, 28, 28)
                self.speech_text = speech
        
        player = MockPlayer(px, py, "hello")
        
        engine_state = {
            "npc": npc,
            "player": player,
            "walls": [],
            "entities": [],
            "tick": 100,
            "last_result": None,
            "goals": ["respond to player"],
            "cooldowns": {"move": 0, "interact": 0}
        }
        
        observation = build_observation(engine_state)
        
        print(f"NPC pos: {observation['npc']['pos']}")
        print(f"Player pos: {observation['player']['pos']}")
        print(f"Player last_said: {observation['player']['last_said']}")
        print("ASCII Map:")
        for row in observation['ascii_map']:
            print(f"  {row}")
    
    # Test 2: With walls
    print(f"\n📍 TEST 2: With walls")
    
    class MockPlayer:
        def __init__(self, x, y, speech=""):
            self.rect = pygame.Rect(x, y, 28, 28)
            self.speech_text = speech
    
    player = MockPlayer(450, 250, "move east")
    
    # Add some walls
    walls = [
        pygame.Rect(320, 200, 32, 32),  # Wall at tile (10, 6)
        pygame.Rect(352, 200, 32, 32),  # Wall at tile (11, 6)
        pygame.Rect(384, 200, 32, 32),  # Wall at tile (12, 6)
    ]
    
    engine_state = {
        "npc": npc,
        "player": player,
        "walls": walls,
        "entities": [],
        "tick": 100,
        "last_result": None,
        "goals": ["respond to player"],
        "cooldowns": {"move": 0, "interact": 0}
    }
    
    observation = build_observation(engine_state)
    
    print("ASCII Map with walls:")
    for row in observation['ascii_map']:
        print(f"  {row}")
    
    # Test 3: With entities
    print(f"\n📍 TEST 3: With entities")
    
    # Add some entities
    entities = [
        {"id": "door_11_7", "kind": "door", "x": 352, "y": 224},
        {"id": "chest_13_7", "kind": "chest", "x": 416, "y": 224},
    ]
    
    engine_state["entities"] = entities
    
    observation = build_observation(engine_state)
    
    print("ASCII Map with entities:")
    for row in observation['ascii_map']:
        print(f"  {row}")
    
    print("Visible entities:")
    for entity in observation['visible_entities']:
        print(f"  {entity}")
    
    # Test 4: Player speech changes
    print(f"\n📍 TEST 4: Player speech changes")
    
    speeches = ["hello", "move east", "step aside", ""]
    
    for speech in speeches:
        player.speech_text = speech
        observation = build_observation(engine_state)
        print(f"Speech: '{speech}' -> last_said: '{observation['player']['last_said']}'")
    
    print(f"\n🎯 ANALYSIS:")
    print("1. ASCII map should show N (NPC) and P (Player) positions")
    print("2. Walls should show as # characters")
    print("3. Doors should show as D characters")
    print("4. Player speech should update in observation")
    print("5. Visible entities should list entities in the 11x11 grid")


if __name__ == "__main__":
    test_observation_debug()