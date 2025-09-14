#!/usr/bin/env python3
"""
Test observation with a realistic game scenario to see if updates work properly.
"""

from zelda_game_llm_integration import create_llm_shopkeeper
from npc.observation import build_observation
import pygame
import json
import time

pygame.init()

def test_realistic_observation():
    """Test observation with realistic game scenario"""
    
    print("🎮 Realistic Game Scenario Test")
    print("=" * 60)
    
    npc = create_llm_shopkeeper(400, 250)
    
    class MockPlayer:
        def __init__(self, x, y, speech=""):
            self.rect = pygame.Rect(x, y, 28, 28)
            self.speech_text = speech
    
    # Create a realistic game world
    walls = [
        # Room boundaries
        pygame.Rect(0, 0, 800, 32),      # Top wall
        pygame.Rect(0, 0, 32, 600),      # Left wall
        pygame.Rect(768, 0, 32, 600),    # Right wall
        pygame.Rect(0, 568, 800, 32),    # Bottom wall
        
        # Interior walls
        pygame.Rect(320, 160, 32, 32),   # Wall near NPC
        pygame.Rect(352, 160, 32, 32),   # Wall near NPC
        pygame.Rect(480, 200, 32, 32),   # Wall near player area
    ]
    
    entities = [
        {"id": "door_shop_entrance", "kind": "door", "x": 384, "y": 160},
        {"id": "chest_treasure", "kind": "chest", "x": 320, "y": 200},
        {"id": "table_shop", "kind": "furniture", "x": 416, "y": 240},
    ]
    
    # Simulate a conversation sequence
    conversation_sequence = [
        (450, 250, "hello", "Player greets NPC"),
        (450, 250, "what do you sell?", "Player asks about inventory"),
        (430, 250, "step aside please", "Player asks NPC to move"),
        (410, 250, "move east", "Player gives movement command"),
        (390, 250, "", "Player stops talking"),
    ]
    
    for i, (px, py, speech, description) in enumerate(conversation_sequence):
        print(f"\n{'='*50}")
        print(f"STEP {i+1}: {description}")
        print(f"{'='*50}")
        
        player = MockPlayer(px, py, speech)
        
        engine_state = {
            "npc": npc,
            "player": player,
            "walls": walls,
            "entities": entities,
            "tick": 100 + i * 10,
            "last_result": "ok" if i > 0 else None,
            "goals": ["respond to player", "sell items"],
            "cooldowns": {"move": 0, "interact": 0}
        }
        
        observation = build_observation(engine_state)
        
        print(f"Player position: {observation['player']['pos']}")
        print(f"Player speech: '{observation['player']['last_said']}'")
        print(f"NPC position: {observation['npc']['pos']}")
        print(f"Tick: {observation['tick']}")
        print(f"Last result: {observation['last_result']}")
        
        print("\nASCII Map:")
        for row_idx, row in enumerate(observation['ascii_map']):
            print(f"  {row_idx:2d}: {row}")
        
        print(f"\nVisible entities ({len(observation['visible_entities'])}):")
        for entity in observation['visible_entities']:
            print(f"  - {entity['kind']} '{entity['id']}' at {entity['pos']}")
        
        # Simulate time passing
        time.sleep(0.5)
    
    print(f"\n🎯 VERIFICATION:")
    print("✅ ASCII map should show different P positions as player moves")
    print("✅ Player speech should change with each step")
    print("✅ Walls (#) and doors (D) should be visible")
    print("✅ Entities should be detected when in the 11x11 grid")
    print("✅ Tick counter should increment")
    print("✅ Last result should update")
    
    # Test edge case: Player speech clearing
    print(f"\n📍 EDGE CASE: Player speech clearing")
    
    player_silent = MockPlayer(450, 250, "")  # Empty speech
    engine_state["player"] = player_silent
    observation = build_observation(engine_state)
    
    print(f"Empty speech -> last_said: '{observation['player']['last_said']}'")
    
    player_none_speech = MockPlayer(450, 250)  # No speech_text attribute
    if hasattr(player_none_speech, 'speech_text'):
        delattr(player_none_speech, 'speech_text')
    
    engine_state["player"] = player_none_speech
    observation = build_observation(engine_state)
    
    print(f"No speech_text attribute -> last_said: '{observation['player']['last_said']}'")


if __name__ == "__main__":
    test_realistic_observation()