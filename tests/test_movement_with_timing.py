#!/usr/bin/env python3
"""
Test NPC movement with proper timing simulation to match game conditions.
"""

from zelda_game_llm_integration import create_llm_shopkeeper
import time

def test_movement_with_game_timing():
    """Test movement with realistic game timing"""
    
    print("⏰ Testing Movement with Game Timing")
    print("-" * 50)
    
    npc = create_llm_shopkeeper(400, 250)
    
    # Mock player that asks NPC to move
    class MockPlayer:
        def __init__(self):
            import pygame
            self.rect = pygame.Rect(450, 250, 28, 28)  # Use real pygame.Rect
            self.speech_text = "move east"
    
    player = MockPlayer()
    
    print(f"Starting position: ({npc.rect.x}, {npc.rect.y})")
    print(f"NPC speed: {npc.speed} pixels per move")
    
    # Simulate multiple game ticks with proper timing
    base_time = 1000
    
    for i in range(5):
        current_time = base_time + (i * 5000)  # 5 seconds between each decision
        
        print(f"\n--- Decision {i+1} at time {current_time}ms ---")
        print(f"Position before: ({npc.rect.x}, {npc.rect.y})")
        print(f"Move cooldown: {npc.llm_controller.cooldowns['move']}ms")
        
        # Simulate game state
        engine_state = {
            "npc": npc,
            "player": player,
            "walls": [],  # No walls for this test
            "entities": [],
            "characters": [npc, player],
            "current_time": current_time,
            "player_spoke": True,  # Player asked NPC to move
            "tick": i * 100
        }
        
        # Let NPC make a decision
        result = npc.llm_controller.npc_decision_tick(engine_state)
        
        print(f"Position after: ({npc.rect.x}, {npc.rect.y})")
        print(f"Decision result: {result}")
        
        if result == "ok":
            print("✅ NPC made a successful decision")
        elif result is None:
            print("⏸️  NPC chose not to make a decision")
        else:
            print(f"⚠️  NPC decision: {result}")
    
    total_movement = ((npc.rect.x - 400)**2 + (npc.rect.y - 250)**2)**0.5
    print(f"\n📊 Summary:")
    print(f"Total distance moved: {total_movement:.1f} pixels")
    print(f"Final position: ({npc.rect.x}, {npc.rect.y})")
    
    if total_movement > 0:
        print("✅ NPC is capable of movement!")
    else:
        print("❌ NPC didn't move at all")
    
    # Test what happens when we ask for specific movement
    print(f"\n🎯 Testing Direct Movement Commands")
    
    # Reset cooldown
    npc.llm_controller.cooldowns["move"] = 0
    
    from npc.actions import Action, MoveDirArgs
    
    directions = ["E", "S", "W", "N"]
    for direction in directions:
        print(f"\nTesting {direction} movement:")
        print(f"  Before: ({npc.rect.x}, {npc.rect.y})")
        
        action = Action(action="move_dir", args=MoveDirArgs(direction=direction))
        result = npc.llm_controller._execute_move_dir(action.args, {
            "walls": [],
            "characters": [npc]
        })
        
        print(f"  After:  ({npc.rect.x}, {npc.rect.y})")
        print(f"  Result: {result}")
        
        # Wait for cooldown to expire
        time.sleep(0.6)  # 600ms > 500ms cooldown
        npc.llm_controller.cooldowns["move"] = 0  # Reset for testing


if __name__ == "__main__":
    test_movement_with_game_timing()