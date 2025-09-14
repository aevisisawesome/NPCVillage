#!/usr/bin/env python3
"""
Debug script to see exactly what format the LLM is returning.
"""

from zelda_game_llm_integration import create_llm_shopkeeper
from npc.llm_client import LLMClient
from npc.observation import build_observation
import pygame
import json

pygame.init()

def test_llm_format_debug():
    """Test what format the LLM is actually returning"""
    
    print("🔍 LLM Format Debug Test")
    print("=" * 60)
    
    # Test with direct LLM client
    client = LLMClient()
    
    if not client.test_connection():
        print("❌ LLM server not available")
        return
    
    print("✅ LLM server connected")
    
    # Create a simple observation
    npc = create_llm_shopkeeper(400, 250)
    
    class MockPlayer:
        def __init__(self, speech):
            self.rect = pygame.Rect(450, 250, 28, 28)
            self.speech_text = speech
    
    # Test with very simple, clear phrases
    test_phrases = [
        "step aside",
        "move east", 
        "walk away",
        "move a bit",
        "go far"
    ]
    
    for phrase in test_phrases:
        print(f"\n{'='*60}")
        print(f"🎭 Testing phrase: '{phrase}'")
        print(f"{'='*60}")
        
        player = MockPlayer(phrase)
        
        # Build observation
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
        
        print(f"📤 Sending observation to LLM:")
        print(f"Player said: '{observation['player']['last_said']}'")
        
        # Get LLM response
        response, error = client.decide(observation)
        
        if error:
            print(f"❌ LLM Error: {error}")
            continue
        
        print(f"\n📥 Raw LLM Response:")
        print(f"{response}")
        
        # Try to parse as JSON to see structure
        try:
            parsed = json.loads(response)
            print(f"\n📋 Parsed JSON Structure:")
            print(f"Action: {parsed.get('action', 'MISSING')}")
            print(f"Args: {parsed.get('args', 'MISSING')}")
            
            # Check if it's the new format
            if parsed.get('action') == 'move':
                args = parsed.get('args', {})
                if 'direction' in args and 'distance' in args:
                    print(f"✅ NEW FORMAT DETECTED!")
                    print(f"   Direction: {args['direction']}")
                    print(f"   Distance: {args['distance']} tiles")
                else:
                    print(f"❌ OLD FORMAT: Missing direction or distance")
            elif parsed.get('action') in ['move_dir', 'move_short', 'move_long']:
                print(f"❌ OLD FORMAT: Using {parsed.get('action')}")
            else:
                print(f"ℹ️  Other action: {parsed.get('action')}")
                
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON: {e}")
            print("Raw response might contain extra text")
    
    print(f"\n{'='*60}")
    print("🎯 TROUBLESHOOTING GUIDE:")
    print("\nIf you see OLD FORMAT responses:")
    print("1. ✅ Restart LM Studio completely")
    print("2. ✅ Reload the model after updating prompts")
    print("3. ✅ Clear any conversation history")
    print("4. ✅ Verify the system prompt was saved")
    print("5. ✅ Check that JSON schema is active")
    
    print("\nExpected NEW FORMAT:")
    print('✅ {"action":"move","args":{"direction":"E","distance":0.5}}')
    print('✅ {"action":"move","args":{"direction":"N","distance":1.0}}')
    print('✅ {"action":"move","args":{"direction":"W","distance":3.0}}')
    
    print("\nOLD FORMAT (should NOT see):")
    print('❌ {"action":"move_dir","args":{"direction":"E"}}')
    print('❌ {"action":"move_short","args":{"direction":"E"}}')
    print('❌ {"action":"move_long","args":{"direction":"E"}}')


def test_system_prompt_check():
    """Show what the system prompt should contain"""
    
    print(f"\n📝 System Prompt Verification")
    print("-" * 40)
    
    print("Your LM Studio system prompt should contain:")
    print("\n1. ✅ Movement distance system explanation:")
    print("   - 0.5 tiles = Short distance")
    print("   - 1.0 tiles = Medium distance")
    print("   - 3.0 tiles = Long distance")
    
    print("\n2. ✅ New action format:")
    print('   - move: {"action":"move","args":{"direction":"N|E|S|W","distance":0.5-5.0}}')
    
    print("\n3. ✅ Examples with distances:")
    print('   - "step aside" → {"action":"move","args":{"direction":"E","distance":0.5}}')
    print('   - "move east" → {"action":"move","args":{"direction":"E","distance":1.0}}')
    print('   - "walk away" → {"action":"move","args":{"direction":"W","distance":3.0}}')
    
    print("\n4. ✅ JSON Schema should include:")
    print('   - "action": {"enum": ["say", "move", "move_to", "interact", "transfer_item"]}')
    print('   - "distance": {"type": "number", "minimum": 0.1, "maximum": 5.0}')


if __name__ == "__main__":
    test_system_prompt_check()
    test_llm_format_debug()