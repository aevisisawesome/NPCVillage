#!/usr/bin/env python3
"""
Test script to verify NPC only speaks when spoken to.
"""

from zelda_game_llm_integration import create_llm_shopkeeper
import time


def test_npc_speech_behavior():
    """Test that NPC only speaks when player speaks first"""
    
    print("🧪 Testing NPC Speech Behavior")
    print("-" * 40)
    
    # Create NPC
    npc = create_llm_shopkeeper(400, 250)
    
    # Mock player
    class MockPlayer:
        def __init__(self):
            self.rect = type('Rect', (), {'centerx': 450, 'centery': 250})()
            self.speech_text = None  # No speech initially
    
    player = MockPlayer()
    
    # Test 1: NPC should not speak when player hasn't spoken
    print("Test 1: Player silent, NPC should not make decisions")
    
    engine_state = {
        "npc": npc,
        "player": player,
        "walls": [],
        "entities": [],
        "characters": [npc, player],
        "current_time": 1000,
        "player_spoke": False,  # Player hasn't spoken
        "tick": 100
    }
    
    result = npc.llm_controller.npc_decision_tick(engine_state)
    
    if result is None:
        print("✅ NPC correctly stayed silent when player hasn't spoken")
    else:
        print(f"❌ NPC made unexpected decision: {result}")
    
    # Test 2: NPC should respond when player speaks
    print("\nTest 2: Player speaks, NPC should respond")
    
    player.speech_text = "Hello there!"
    engine_state["player_spoke"] = True
    engine_state["current_time"] = 2000
    
    result = npc.llm_controller.npc_decision_tick(engine_state)
    
    if result is not None:
        print(f"✅ NPC responded when player spoke: {result}")
    else:
        print("❌ NPC failed to respond when player spoke")
    
    # Test 3: Test idle behavior toggle
    print("\nTest 3: Testing idle behavior toggle")
    
    print("Enabling idle behavior...")
    npc.llm_controller.enable_idle_behavior(True, 0.5)
    
    # Reset state
    player.speech_text = None
    engine_state["player_spoke"] = False
    engine_state["current_time"] = 10000  # Much later time
    
    # This should now potentially make a decision (though timing dependent)
    result = npc.llm_controller.npc_decision_tick(engine_state)
    
    print(f"With idle behavior enabled: {result if result else 'No decision (timing dependent)'}")
    
    # Disable idle behavior
    print("Disabling idle behavior...")
    npc.llm_controller.enable_idle_behavior(False)
    
    engine_state["current_time"] = 20000
    result = npc.llm_controller.npc_decision_tick(engine_state)
    
    if result is None:
        print("✅ NPC correctly silent after disabling idle behavior")
    else:
        print(f"❌ NPC still making decisions: {result}")
    
    print("\n" + "=" * 40)
    print("Behavior test complete!")
    print("The NPC should now only speak when spoken to.")
    print("Use the 'T' key in the game to toggle idle behavior for testing.")


if __name__ == "__main__":
    test_npc_speech_behavior()