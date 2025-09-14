#!/usr/bin/env python3
"""
Test that the LLM correctly responds to greetings vs movement requests.
"""

from zelda_game_llm_integration import create_llm_shopkeeper
from npc.llm_client import LLMClient
from npc.observation import build_observation
import pygame
import json

pygame.init()

def test_greeting_vs_movement():
    """Test that LLM responds appropriately to different types of input"""
    
    print("🎯 Greeting vs Movement Response Test")
    print("=" * 60)
    
    # Test with direct LLM client
    client = LLMClient()
    
    if not client.test_connection():
        print("❌ LLM server not available - start LM Studio first")
        return
    
    print("✅ LLM server connected")
    
    # Create a simple observation
    npc = create_llm_shopkeeper(400, 250)
    
    class MockPlayer:
        def __init__(self, speech):
            self.rect = pygame.Rect(450, 250, 28, 28)
            self.speech_text = speech
    
    # Test cases: input -> expected action type
    test_cases = [
        # Greetings should use "say"
        ("hello", "say", "Simple greeting"),
        ("hi there", "say", "Casual greeting"),
        ("greetings", "say", "Formal greeting"),
        ("good day", "say", "Polite greeting"),
        
        # Questions should use "say"
        ("what do you sell?", "say", "Inventory question"),
        ("do you have weapons?", "say", "Stock inquiry"),
        ("how much for a sword?", "say", "Price question"),
        
        # Movement requests should use "move"
        ("step aside", "move", "Polite movement request"),
        ("move east", "move", "Directional command"),
        ("could you move please?", "move", "Polite movement request"),
        ("get out of the way", "move", "Urgent movement request"),
        ("navigate to player position", "move", "Movement toward player"),
    ]
    
    correct_responses = 0
    total_tests = len(test_cases)
    
    for phrase, expected_action, reasoning in test_cases:
        print(f"\n{'='*60}")
        print(f"🧪 Testing: '{phrase}'")
        print(f"Expected action: {expected_action}")
        print(f"Reasoning: {reasoning}")
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
        
        # Get LLM response
        response, error = client.decide(observation)
        
        if error:
            print(f"❌ LLM Error: {error}")
            continue
        
        print(f"📥 Raw LLM Response: {response}")
        
        # Parse and check action type
        try:
            parsed = json.loads(response)
            actual_action = parsed.get('action')
            args = parsed.get('args', {})
            
            print(f"📋 Parsed Action: {actual_action}")
            print(f"📋 Args: {args}")
            
            if actual_action == expected_action:
                print("✅ CORRECT: Action type matches expectation!")
                correct_responses += 1
                
                # Show what the NPC would do
                if actual_action == "say":
                    print(f"   🗣️  NPC would say: '{args.get('text', 'N/A')}'")
                elif actual_action == "move":
                    direction = args.get('direction', 'N/A')
                    distance = args.get('distance', 'N/A')
                    print(f"   🚶 NPC would move: {direction} direction, {distance} tiles")
            else:
                print(f"❌ WRONG: Expected {expected_action}, got {actual_action}")
                if actual_action == "move" and expected_action == "say":
                    print("   🚨 NPC is moving when it should be talking!")
                elif actual_action == "say" and expected_action == "move":
                    print("   🚨 NPC is talking when it should be moving!")
                
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON: {e}")
    
    print(f"\n{'='*60}")
    print(f"📊 RESULTS: {correct_responses}/{total_tests} correct responses")
    print(f"Success rate: {correct_responses/total_tests*100:.1f}%")
    
    if correct_responses >= total_tests * 0.8:
        print("\n✅ SUCCESS: Response selection working well!")
    else:
        print("\n⚠️  NEEDS IMPROVEMENT: Update LM Studio with corrected system prompt")
        print("\nThe issue was:")
        print("- LLM responding to 'hello' with movement instead of speech")
        print("- Updated prompt clarifies when to use 'say' vs 'move'")
        print("- Copy updated lm_studio_system_prompt_new.txt to LM Studio")


if __name__ == "__main__":
    test_greeting_vs_movement()