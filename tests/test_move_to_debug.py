#!/usr/bin/env python3
"""
Debug the move_to action to see what's happening.
"""

from zelda_game_llm_integration import create_llm_shopkeeper
import pygame

pygame.init()

def test_move_to_debug():
    """Debug move_to action"""
    
    print("🔍 Move_To Debug Test")
    print("=" * 60)
    
    npc = create_llm_shopkeeper(400, 250)
    
    print(f"NPC starting position: ({npc.rect.x}, {npc.rect.y})")
    print(f"NPC center: ({npc.rect.centerx}, {npc.rect.centery})")
    
    # Test what coordinates (1,1) should be
    target_tile_x, target_tile_y = 1, 1
    target_world_x = target_tile_x * 32
    target_world_y = target_tile_y * 32
    
    print(f"Target tile: ({target_tile_x}, {target_tile_y})")
    print(f"Target world coordinates: ({target_world_x}, {target_world_y})")
    
    # Calculate distance
    import math
    dx = target_world_x - npc.rect.centerx
    dy = target_world_y - npc.rect.centery
    distance = math.sqrt(dx*dx + dy*dy)
    
    print(f"Distance to target: {distance:.1f} pixels")
    print(f"Direction: dx={dx}, dy={dy}")
    
    # Test single step movement
    if distance > 0:
        move_dx = (dx / distance) * npc.speed
        move_dy = (dy / distance) * npc.speed
        print(f"Single step movement: dx={move_dx:.1f}, dy={move_dy:.1f}")
        
        # How many steps would it take?
        steps_needed = distance / npc.speed
        print(f"Steps needed to reach target: {steps_needed:.1f}")
    
    print(f"\n🎯 PROBLEM ANALYSIS:")
    print("1. move_to only moves ONE step toward target")
    print("2. It doesn't continue moving like the 'move' action does")
    print("3. For long distances, it would need many calls to reach target")
    
    print(f"\n✅ SOLUTION:")
    print("1. Make move_to set up autonomous movement like 'move' action")
    print("2. Continue moving until target is reached")
    print("3. Or recommend using 'move' action instead for most cases")


if __name__ == "__main__":
    test_move_to_debug()