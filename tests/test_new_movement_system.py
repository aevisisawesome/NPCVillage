#!/usr/bin/env python3
"""
Test the new movement system where LLM chooses distance directly.
"""

from zelda_game_llm_integration import create_llm_shopkeeper
from npc.actions import parse_action
import pygame

pygame.init()

def test_new_movement_system():
    """Test the new movement system with LLM-chosen distances"""
    
    print("🎯 New Movement System Test")
    print("=" * 60)
    
    npc = create_llm_shopkeeper(400, 250)
    
    # Test different phrases that should trigger different distances
    test_cases = [
        ("Could you step aside please?", 0.5, "Polite small request"),
        ("Move a bit to the left", 0.5, "Explicitly asks for 'a bit'"),
        ("Scoot over", 0.5, "Casual small movement"),
        ("Move east", 1.0, "Standard directional command"),
        ("Go north", 1.0, "Basic movement request"),
        ("Walk away from me", 3.0, "Explicitly asks to walk away"),
        ("Move far back", 3.0, "Explicitly asks for 'far'"),
        ("Get out of the way!", 3.0, "Urgent, dramatic request"),
    ]
    
    correct_predictions = 0
    total_tests = len(test_cases)
    
    for phrase, expected_distance, reasoning in test_cases:
        print(f"\n{'='*60}")
        print(f"🧪 Testing: '{phrase}'")
        print(f"Expected distance: {expected_distance} tiles")
        print(f"Reasoning: {reasoning}")
        print(f"{'='*60}")
        
        # Reset NPC
        npc.rect.x = 400
        npc.rect.y = 250
        npc.llm_controller.active_movement = None
        npc.llm_controller.movement_steps_remaining = 0
        npc.llm_controller.cooldowns["move"] = 0
        npc.llm_controller.last_decision_time = 0
        
        # Mock player
        class MockPlayer:
            def __init__(self, speech):
                self.rect = pygame.Rect(450, 250, 28, 28)
                self.speech_text = speech
        
        player = MockPlayer(phrase)
        
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
        
        try:
            result = npc.llm_controller.npc_decision_tick(engine_state)
            
            if result == "ok":
                print("✅ LLM made a decision")
                
                # Check the distance by looking at movement steps
                if npc.llm_controller.active_movement:
                    steps = npc.llm_controller.movement_steps_remaining + 1  # +1 for initial step
                    actual_distance = (steps * npc.speed) / 32.0  # Convert to tiles
                    
                    print(f"Actual distance: {actual_distance} tiles ({steps} steps)")
                    
                    # Check if distance matches expectation (with tolerance)
                    if abs(actual_distance - expected_distance) <= 0.1:
                        print("✅ CORRECT: Distance matches expectation!")
                        correct_predictions += 1
                    else:
                        print(f"❌ WRONG: Expected {expected_distance} tiles, got {actual_distance} tiles")
                else:
                    print("❌ No movement started")
            else:
                print(f"❌ Decision failed: {result}")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*60}")
    print(f"📊 RESULTS: {correct_predictions}/{total_tests} correct predictions")
    print(f"Success rate: {correct_predictions/total_tests*100:.1f}%")
    
    if correct_predictions >= total_tests * 0.75:
        print("\n✅ SUCCESS: New movement system working well!")
    elif correct_predictions >= total_tests * 0.5:
        print("\n⚠️  PARTIAL: System working but needs refinement")
    else:
        print("\n❌ NEEDS WORK: System not working as expected")
    
    print(f"\n🎯 Next Steps:")
    print("1. Copy lm_studio_system_prompt_new.txt to LM Studio system prompt")
    print("2. Update JSON schema in LM Studio")
    print("3. Test with real LLM")


def test_action_parsing():
    """Test that the new action format parses correctly"""
    
    print(f"\n🔍 Testing New Action Parsing")
    print("-" * 40)
    
    test_cases = [
        ('{"action":"move","args":{"direction":"E","distance":0.5}}', True),
        ('{"action":"move","args":{"direction":"N","distance":1.0}}', True),
        ('{"action":"move","args":{"direction":"W","distance":3.0}}', True),
        ('{"action":"move","args":{"direction":"S","distance":2.5}}', True),
        ('{"action":"move","args":{"direction":"E"}}', False),  # Missing distance
        ('{"action":"move","args":{"distance":1.0}}', False),  # Missing direction
        ('{"action":"move","args":{"direction":"E","distance":10.0}}', False),  # Distance too high
    ]
    
    for json_input, should_succeed in test_cases:
        action, error = parse_action(json_input)
        success = action is not None
        
        status = "✅" if success == should_succeed else "❌"
        print(f"{status} {json_input}")
        
        if error and not should_succeed:
            print(f"    Expected error: {error}")
        elif success and should_succeed:
            print(f"    Parsed: action={action.action}, direction={action.args.direction}, distance={action.args.distance}")


if __name__ == "__main__":
    test_action_parsing()
    test_new_movement_system()