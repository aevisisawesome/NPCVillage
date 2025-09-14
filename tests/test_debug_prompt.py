#!/usr/bin/env python3
"""
Test to capture the exact prompt being sent to the LLM.
"""

from zelda_game_llm_integration import create_llm_shopkeeper
import pygame

pygame.init()

def test_debug_prompt():
    """Test to see the exact prompt sent to LLM"""
    
    print("🔍 Debug Prompt Test")
    print("=" * 60)
    
    npc = create_llm_shopkeeper(400, 250)
    
    # Mock player saying "hello"
    class MockPlayer:
        def __init__(self, speech):
            self.rect = pygame.Rect(450, 250, 28, 28)
            self.speech_text = speech
    
    player = MockPlayer("hi")
    
    engine_state = {
        "npc": npc,
        "player": player,
        "walls": [],
        "entities": [],
        "characters": [npc, player],
        "current_time": 1000,
        "player_spoke": True,
        "tick": 100
    }
    
    print("Testing with player saying: 'hello'")
    print("This should trigger debug output showing the exact prompt...")
    print()
    
    try:
        result = npc.llm_controller.npc_decision_tick(engine_state)
        print(f"\nResult: {result}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_debug_prompt()