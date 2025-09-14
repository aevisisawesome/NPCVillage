#!/usr/bin/env python3
"""
Test the distance calculation system directly.
"""

from zelda_game_llm_integration import create_llm_shopkeeper
from npc.actions import parse_action
import pygame

pygame.init()

def test_distance_calculation():
    """Test that distance calculations work correctly"""
    
    print("🎯 Distance Calculation Test")
    print("=" * 60)
    
    npc = create_llm_shopkeeper(400, 250)
    
    # Test different distances
    test_cases = [
        (0.5, 16, "Short distance"),
        (1.0, 32, "Medium distance"), 
        (1.5, 48, "1.5 tiles"),
        (2.0, 64, "Long distance"),
        (3.0, 96, "Very long distance"),
        (4.0, 128, "Maximum practical distance"),
    ]
    
    for distance_tiles, expected_pixels, description in test_cases:
        print(f"\n🧪 Testing {distance_tiles} tiles ({description})")
        
        # Create mock action
        json_input = f'{{"action":"move","args":{{"direction":"E","distance":{distance_tiles}}}}}'
        action, error = parse_action(json_input)
        
        if error:
            print(f"❌ Parse error: {error}")
            continue
            
        print(f"✅ Action parsed: direction={action.args.direction}, distance={action.args.distance}")
        
        # Calculate expected steps
        expected_steps = int(distance_tiles * 32 / npc.speed)  # 32 pixels per tile, 4 pixels per step
        
        print(f"Expected: {expected_pixels} pixels = {expected_steps} steps")
        
        # Reset NPC
        npc.rect.x = 400
        npc.rect.y = 250
        npc.llm_controller.active_movement = None
        npc.llm_controller.movement_steps_remaining = 0
        
        # Mock engine state
        engine_state = {
            "npc": npc,
            "walls": [],
            "entities": [],
            "current_time": 1000
        }
        
        # Execute the action
        result = npc.llm_controller._execute_move_dir(action.args, engine_state, distance_tiles=action.args.distance)
        
        if result == "ok":
            actual_steps = npc.llm_controller.movement_steps_remaining + 1  # +1 for initial step
            actual_pixels = actual_steps * npc.speed
            actual_tiles = actual_pixels / 32.0
            
            print(f"Actual: {actual_pixels} pixels = {actual_steps} steps = {actual_tiles:.1f} tiles")
            
            if abs(actual_tiles - distance_tiles) <= 0.1:
                print("✅ CORRECT: Distance calculation matches!")
            else:
                print(f"❌ WRONG: Expected {distance_tiles} tiles, got {actual_tiles} tiles")
        else:
            print(f"❌ Execution failed: {result}")
    
    print(f"\n{'='*60}")
    print("🎯 SUMMARY:")
    print("The distance calculation system converts:")
    print("- LLM distance (tiles) → Movement steps → Pixel movement")
    print("- Formula: steps = (distance_tiles * 32) / npc.speed")
    print(f"- With npc.speed = {npc.speed}, each step = {npc.speed} pixels")
    print("- Each tile = 32 pixels")


def test_action_validation():
    """Test that action validation works correctly"""
    
    print(f"\n🔍 Action Validation Test")
    print("-" * 40)
    
    test_cases = [
        ('{"action":"move","args":{"direction":"E","distance":0.5}}', True, "Valid short move"),
        ('{"action":"move","args":{"direction":"N","distance":1.0}}', True, "Valid medium move"),
        ('{"action":"move","args":{"direction":"W","distance":3.0}}', True, "Valid long move"),
        ('{"action":"move","args":{"direction":"S","distance":5.0}}', True, "Valid max distance"),
        ('{"action":"move","args":{"direction":"E","distance":0.05}}', False, "Distance too small"),
        ('{"action":"move","args":{"direction":"E","distance":10.0}}', False, "Distance too large"),
        ('{"action":"move","args":{"direction":"X","distance":1.0}}', False, "Invalid direction"),
        ('{"action":"move","args":{"direction":"E"}}', False, "Missing distance"),
        ('{"action":"move","args":{"distance":1.0}}', False, "Missing direction"),
    ]
    
    for json_input, should_succeed, description in test_cases:
        action, error = parse_action(json_input)
        success = action is not None
        
        status = "✅" if success == should_succeed else "❌"
        print(f"{status} {description}")
        print(f"    Input: {json_input}")
        
        if error and not should_succeed:
            print(f"    Expected error: {error}")
        elif success and should_succeed:
            print(f"    Parsed: direction={action.args.direction}, distance={action.args.distance}")
        print()


if __name__ == "__main__":
    test_action_validation()
    test_distance_calculation()