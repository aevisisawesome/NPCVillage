#!/usr/bin/env python3
"""
Test autonomous movement completion - NPC should continue moving without waiting for player input.
"""

from zelda_game_llm_integration import create_llm_shopkeeper
import pygame
import time

pygame.init()

def test_autonomous_movement():
    """Test that NPC continues moving autonomously after initial command"""
    
    print("🤖 Testing Autonomous Movement Completion")
    print("-" * 50)
    
    npc = create_llm_shopkeeper(400, 250)
    
    # Mock player
    class MockPlayer:
        def __init__(self):
            self.rect = pygame.Rect(450, 250, 28, 28)
            self.speech_text = "move east"
    
    player = MockPlayer()
    
    print(f"Starting position: ({npc.rect.x}, {npc.rect.y})")
    print(f"NPC speed: {npc.speed} pixels per move")
    
    # Simulate the initial player command
    print(f"\n--- Player says 'move east' ---")
    
    engine_state = {
        "npc": npc,
        "player": player,
        "walls": [],
        "entities": [],
        "characters": [npc, player],
        "current_time": 1000,
        "player_spoke": True,  # Initial command
        "tick": 100
    }
    
    # First decision (triggered by player speech)
    result1 = npc.llm_controller.npc_decision_tick(engine_state)
    print(f"Initial decision result: {result1}")
    print(f"Position after initial decision: ({npc.rect.x}, {npc.rect.y})")
    print(f"Active movement: {npc.llm_controller.active_movement}")
    print(f"Steps remaining: {npc.llm_controller.movement_steps_remaining}")
    
    # Now simulate autonomous continuation (no player speech)
    print(f"\n--- Autonomous movement continuation (no player input) ---")
    
    for i in range(10):  # Try up to 10 autonomous steps
        # Advance time
        engine_state["current_time"] += 250  # 250ms intervals
        engine_state["player_spoke"] = False  # No new player input
        player.speech_text = None  # Clear player speech
        
        print(f"\nStep {i+1} at time {engine_state['current_time']}ms:")
        print(f"  Before: ({npc.rect.x}, {npc.rect.y})")
        print(f"  Active movement: {npc.llm_controller.active_movement}")
        print(f"  Steps remaining: {npc.llm_controller.movement_steps_remaining}")
        
        # Check if NPC should make a decision
        should_decide = npc.llm_controller.should_make_decision(
            engine_state["current_time"], 
            engine_state["player_spoke"]
        )
        
        print(f"  Should make decision: {should_decide}")
        
        if should_decide:
            result = npc.llm_controller.npc_decision_tick(engine_state)
            print(f"  Decision result: {result}")
            print(f"  After: ({npc.rect.x}, {npc.rect.y})")
            
            if result is None or result.startswith("blocked") or not npc.llm_controller.active_movement:
                print(f"  Movement sequence ended")
                break
        else:
            print(f"  No decision made")
            break
    
    total_movement = npc.rect.x - 400
    print(f"\n📊 Results:")
    print(f"Total eastward movement: {total_movement} pixels")
    print(f"Final position: ({npc.rect.x}, {npc.rect.y})")
    print(f"Expected movement: ~32 pixels (1 tile)")
    
    if total_movement >= 24:  # At least 3/4 of a tile
        print("✅ Autonomous movement working! NPC moved significantly without player input.")
    elif total_movement >= 8:  # At least 2 steps
        print("⚠️  Partial autonomous movement - some steps completed.")
    else:
        print("❌ Autonomous movement failed - NPC only moved on initial command.")
    
    # Test that movement stops when sequence completes
    print(f"\n--- Testing movement sequence completion ---")
    
    # Wait for any remaining movement to complete
    for i in range(5):
        engine_state["current_time"] += 250
        engine_state["player_spoke"] = False
        
        if npc.llm_controller.should_make_decision(engine_state["current_time"], False):
            result = npc.llm_controller.npc_decision_tick(engine_state)
            print(f"Completion step {i+1}: {result}")
            if not npc.llm_controller.active_movement:
                print("✅ Movement sequence properly completed")
                break
        else:
            print("✅ Movement sequence completed - no more autonomous decisions")
            break


if __name__ == "__main__":
    test_autonomous_movement()