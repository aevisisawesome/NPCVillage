#!/usr/bin/env python3
"""
Test that NPC movement is now more visible with increased speed.
"""

from zelda_game_llm_integration import create_llm_shopkeeper
from npc.actions import Action, MoveDirArgs
import pygame

pygame.init()

def test_visible_movement():
    """Test that movement is now more visible"""
    
    print("👀 Testing Movement Visibility")
    print("-" * 40)
    
    npc = create_llm_shopkeeper(400, 250)
    
    print(f"NPC speed: {npc.speed} pixels per move")
    print(f"Starting position: ({npc.rect.x}, {npc.rect.y})")
    
    # Test multiple moves in the same direction
    engine_state = {
        "walls": [],  # No walls for this test
        "characters": [npc]
    }
    
    directions = ["E", "E", "E", "S", "S", "W", "W", "N", "N"]
    
    for i, direction in enumerate(directions, 1):
        print(f"\nMove {i}: Going {direction}")
        print(f"  Before: ({npc.rect.x}, {npc.rect.y})")
        
        # Execute movement through controller
        action = Action(action="move_dir", args=MoveDirArgs(direction=direction))
        result = npc.llm_controller._execute_move_dir(action.args, engine_state)
        
        print(f"  After:  ({npc.rect.x}, {npc.rect.y})")
        print(f"  Result: {result}")
        
        if result == "ok":
            print(f"  ✅ Movement successful")
        else:
            print(f"  ❌ Movement failed: {result}")
    
    print(f"\nFinal position: ({npc.rect.x}, {npc.rect.y})")
    print(f"Total displacement from start: ({npc.rect.x - 400}, {npc.rect.y - 250})")
    
    # Calculate expected vs actual movement
    expected_moves = {"E": 3, "S": 2, "W": 2, "N": 2}
    expected_x = 400 + (expected_moves["E"] - expected_moves["W"]) * npc.speed
    expected_y = 250 + (expected_moves["S"] - expected_moves["N"]) * npc.speed
    
    print(f"Expected final position: ({expected_x}, {expected_y})")
    
    if npc.rect.x == expected_x and npc.rect.y == expected_y:
        print("✅ Movement calculations are correct!")
    else:
        print("❌ Movement calculations don't match expected values")
    
    print(f"\n📏 Movement Analysis:")
    print(f"  Speed: {npc.speed} pixels per move")
    print(f"  Tile size: 32 pixels")
    print(f"  Moves per tile: {32 / npc.speed:.1f}")
    print(f"  This means {npc.speed / 32 * 100:.1f}% of a tile per move")


if __name__ == "__main__":
    test_visible_movement()