#!/usr/bin/env python3
"""
Test with very explicit phrases that should clearly trigger different movement types.
"""

from zelda_game_llm_integration import create_llm_shopkeeper
import pygame

pygame.init()

def test_explicit_movement():
    """Test with very explicit phrases"""
    
    print("🎯 Explicit Movement Test")
    print("=" * 60)
    
    npc = create_llm_shopkeeper(400, 250)
    
    # Very explicit test phrases
    test_cases = [
        # These should DEFINITELY trigger move_short
        ("Could you step aside please?", "move_short", "Very polite, small request"),
        ("Move a bit to the left", "move_short", "Explicitly asks for 'a bit'"),
        ("Scoot over", "move_short", "Casual small movement"),
        
        # These should trigger move_dir  
        ("Move east", "move_dir", "Standard directional command"),
        ("Go north", "move_dir", "Basic movement request"),
        
        # These should DEFINITELY trigger move_long
        ("Walk away from me", "move_long", "Explicitly asks to walk away"),
        ("Move far back", "move_long", "Explicitly asks for 'far'"),
        ("Get out of the way!", "move_long", "Urgent, dramatic request"),
    ]
    
    correct_predictions = 0
    total_tests = len(test_cases)
    
    for phrase, expected_action, reasoning in test_cases:
        print(f"\n{'='*60}")
        print(f"🧪 Testing: '{phrase}'")
        print(f"Expected: {expected_action}")
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
            
            # The debug output will show us what the LLM actually chose
            # We can parse it from the debug messages, but let's also check the result
            
            if result == "ok":
                print("✅ LLM made a decision")
                # Check if it was the right type based on movement setup
                if npc.llm_controller.active_movement:
                    steps = npc.llm_controller.movement_steps_remaining + 1  # +1 for initial step
                    
                    if expected_action == "move_short" and steps == 4:  # 0.5 tiles = 4 steps
                        print("✅ CORRECT: LLM chose move_short")
                        correct_predictions += 1
                    elif expected_action == "move_dir" and steps == 8:  # 1.0 tiles = 8 steps  
                        print("✅ CORRECT: LLM chose move_dir")
                        correct_predictions += 1
                    elif expected_action == "move_long" and steps == 24:  # 3.0 tiles = 24 steps
                        print("✅ CORRECT: LLM chose move_long")
                        correct_predictions += 1
                    else:
                        print(f"❌ WRONG: Expected {expected_action}, got {steps} steps")
                        if steps == 4:
                            print("   LLM chose move_short instead")
                        elif steps == 8:
                            print("   LLM chose move_dir instead")
                        elif steps == 24:
                            print("   LLM chose move_long instead")
                        else:
                            print(f"   Unknown movement type ({steps} steps)")
                else:
                    print("❌ No movement started")
            else:
                print(f"❌ Decision failed: {result}")
                
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print(f"\n{'='*60}")
    print(f"📊 RESULTS: {correct_predictions}/{total_tests} correct predictions")
    print(f"Success rate: {correct_predictions/total_tests*100:.1f}%")
    
    if correct_predictions == 0:
        print("\n🚨 PROBLEM: LLM is not using the new action types at all!")
        print("Possible issues:")
        print("1. LM Studio system prompt not updated correctly")
        print("2. JSON schema not configured properly")
        print("3. Model needs to be restarted/reloaded")
        print("4. Model doesn't support the new action types")
    elif correct_predictions < total_tests // 2:
        print("\n⚠️  PARTIAL: LLM sometimes uses new actions but not consistently")
        print("Try adjusting the system prompt to be even more explicit")
    else:
        print("\n✅ SUCCESS: LLM is using contextual movement correctly!")


if __name__ == "__main__":
    test_explicit_movement()