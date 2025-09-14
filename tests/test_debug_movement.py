#!/usr/bin/env python3
"""
Test with debug output to see exactly what the LLM is choosing.
"""

from zelda_game_llm_integration import create_llm_shopkeeper
import pygame

pygame.init()

def test_debug_movement():
    """Test movement with full debug output"""
    
    print("🔍 Debug Movement Test")
    print("=" * 50)
    
    npc = create_llm_shopkeeper(400, 250)
    
    # Test different player phrases that should trigger different movement types
    test_phrases = [
        ("step aside", "Should trigger move_short (0.5 tiles)"),
        ("move east", "Should trigger move_dir (1.0 tiles)"),
        ("walk away", "Should trigger move_long (3.0 tiles)"),
        ("go north", "Should trigger move_dir (1.0 tiles)"),
        ("scoot over", "Should trigger move_short (0.5 tiles)"),
    ]
    
    for phrase, expected in test_phrases:
        print(f"\n{'='*60}")
        print(f"🎭 Testing phrase: '{phrase}'")
        print(f"Expected: {expected}")
        print(f"{'='*60}")
        
        # Reset NPC state
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
        
        # Simulate game state
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
        
        print(f"Starting position: ({npc.rect.x}, {npc.rect.y})")
        
        # Make initial decision
        try:
            result = npc.llm_controller.npc_decision_tick(engine_state)
            print(f"Initial decision result: {result}")
            print(f"Position after initial decision: ({npc.rect.x}, {npc.rect.y})")
            
            if npc.llm_controller.active_movement:
                print(f"Active movement: {npc.llm_controller.active_movement}")
                print(f"Steps remaining: {npc.llm_controller.movement_steps_remaining}")
                
                # Let a few autonomous steps happen
                for i in range(3):
                    engine_state["current_time"] += 250
                    engine_state["player_spoke"] = False
                    player.speech_text = None
                    
                    if npc.llm_controller.should_make_decision(engine_state["current_time"], False):
                        result = npc.llm_controller.npc_decision_tick(engine_state)
                        print(f"Auto step {i+1}: {result}, pos: ({npc.rect.x}, {npc.rect.y})")
                        if not npc.llm_controller.active_movement:
                            break
                    else:
                        break
                
                total_movement = npc.rect.x - 400
                print(f"Total movement: {total_movement} pixels")
                
                if abs(total_movement - 16) <= 4:
                    print("✅ Looks like move_short (16px)")
                elif abs(total_movement - 32) <= 4:
                    print("✅ Looks like move_dir (32px)")
                elif abs(total_movement - 96) <= 8:
                    print("✅ Looks like move_long (96px)")
                else:
                    print(f"❓ Unexpected movement distance: {total_movement}px")
            else:
                print("❌ No active movement started")
                
        except Exception as e:
            print(f"❌ Error during test: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*60}")
    print("🎯 Debug Analysis Complete")
    print("Look at the debug output above to see:")
    print("1. What the LLM's raw response was")
    print("2. Which action type it chose")
    print("3. Which execution method was called")
    print("4. What distance calculation was made")
    print("5. Whether the movement matches expectations")


if __name__ == "__main__":
    test_debug_movement()