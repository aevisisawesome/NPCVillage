#!/usr/bin/env python3
"""
Test that the LLM correctly chooses between move and move_to actions.
"""

from zelda_game_llm_integration import create_llm_shopkeeper
from npc.llm_client import LLMClient
from npc.observation import build_observation
import pygame
import json

pygame.init()

def test_move_vs_move_to():
    """Test that LLM chooses the correct action type"""
    
    print("🎯 Move vs Move_To Action Selection Test")
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
    
    # Test phrases that should use "move" action
    test_cases = [
        ("navigate to player position", "move", "Should use move with direction"),
        ("come closer to me", "move", "Should use move with direction"),
        ("move toward the player", "move", "Should use move with direction"),
        ("go to the player", "move", "Should use move with direction"),
        ("move east", "move", "Clear directional command"),
        ("step aside", "move", "Simple movement request"),
        ("go to position 10,5", "move_to", "Exact coordinates - should use move_to"),
        ("move to coordinates 15,20", "move_to", "Explicit coordinates"),
    ]
    
    correct_actions = 0
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
                correct_actions += 1
                
                # Additional validation
                if actual_action == "move":
                    if 'direction' in args and 'distance' in args:
                        print(f"   ✅ Move args valid: {args['direction']} direction, {args['distance']} tiles")
                    else:
                        print(f"   ❌ Move args invalid: missing direction or distance")
                elif actual_action == "move_to":
                    if 'x' in args and 'y' in args:
                        print(f"   ✅ Move_to args valid: ({args['x']}, {args['y']})")
                    else:
                        print(f"   ❌ Move_to args invalid: missing x or y")
            else:
                print(f"❌ WRONG: Expected {expected_action}, got {actual_action}")
                
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON: {e}")
    
    print(f"\n{'='*60}")
    print(f"📊 RESULTS: {correct_actions}/{total_tests} correct action selections")
    print(f"Success rate: {correct_actions/total_tests*100:.1f}%")
    
    if correct_actions >= total_tests * 0.8:
        print("\n✅ SUCCESS: Action selection working well!")
    else:
        print("\n⚠️  NEEDS IMPROVEMENT: Update LM Studio with new system prompt")
        print("\nMake sure to:")
        print("1. Copy updated lm_studio_system_prompt_new.txt to LM Studio")
        print("2. Restart LM Studio completely")
        print("3. Clear conversation history")


if __name__ == "__main__":
    test_move_vs_move_to()