#!/usr/bin/env python3
"""
Test that the system works with only LM Studio system prompt (no hardcoded prompt).
"""

from zelda_game_llm_integration import create_llm_shopkeeper
import pygame

pygame.init()

def test_single_system_prompt():
    """Test with only LM Studio system prompt"""
    
    print("🎯 Single System Prompt Test")
    print("=" * 60)
    print("This test verifies that the system works with:")
    print("✅ LM Studio system prompt (configured in LM Studio)")
    print("❌ No hardcoded prompt in llm_client.py")
    print()
    
    npc = create_llm_shopkeeper(400, 250)
    
    # Mock player saying "hello"
    class MockPlayer:
        def __init__(self, speech):
            self.rect = pygame.Rect(450, 250, 28, 28)
            self.speech_text = speech
    
    player = MockPlayer("hello")
    
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
    print("Expected: LLM should respond with 'say' action")
    print()
    
    try:
        result = npc.llm_controller.npc_decision_tick(engine_state)
        print(f"Result: {result}")
        
        if result == "ok":
            print("✅ SUCCESS: System working with LM Studio prompt only!")
        else:
            print(f"⚠️  Issue: {result}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nThis might mean:")
        print("1. LM Studio is not running")
        print("2. LM Studio system prompt is not configured")
        print("3. LM Studio system prompt needs to be updated")
    
    print(f"\n📋 SETUP INSTRUCTIONS:")
    print("1. Open LM Studio")
    print("2. Go to system prompt field")
    print("3. Copy content from 'lm_studio_system_prompt_new.txt'")
    print("4. Paste into LM Studio system prompt")
    print("5. Make sure JSON schema is also configured")
    print("6. Restart LM Studio if needed")


if __name__ == "__main__":
    test_single_system_prompt()