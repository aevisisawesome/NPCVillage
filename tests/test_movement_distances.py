#!/usr/bin/env python3
"""
Test the new movement distance system with different action types.
"""

from zelda_game_llm_integration import create_llm_shopkeeper
from npc.actions import Action, MoveDirArgs, MoveShortArgs, MoveLongArgs
import pygame

pygame.init()

def test_movement_distances():
    """Test all three movement distance types"""
    
    print("📏 Testing Movement Distance System")
    print("=" * 50)
    
    npc = create_llm_shopkeeper(400, 250)
    
    # Test data for different movement types
    movement_tests = [
        ("move_short", MoveShortArgs(direction="E"), 0.5, "Short movement (step aside)"),
        ("move_dir", MoveDirArgs(direction="E"), 1.0, "Medium movement (standard)"),
        ("move_long", MoveLongArgs(direction="E"), 3.0, "Long movement (walk away)")
    ]
    
    engine_state = {
        "walls": [],
        "characters": [npc]
    }
    
    for action_type, args_obj, expected_tiles, description in movement_tests:
        print(f"\n--- Testing {action_type} ({description}) ---")
        
        # Reset NPC position and state
        npc.rect.x = 400
        npc.rect.y = 250
        npc.llm_controller.active_movement = None
        npc.llm_controller.movement_steps_remaining = 0
        npc.llm_controller.cooldowns["move"] = 0  # Reset cooldown
        npc.llm_controller.last_decision_time = 0  # Reset timing
        
        start_x = npc.rect.x
        print(f"Starting position: ({start_x}, {npc.rect.y})")
        print(f"Expected distance: {expected_tiles} tiles ({expected_tiles * 32:.0f} pixels)")
        
        # Create and execute action
        action = Action(action=action_type, args=args_obj)
        result = npc.llm_controller.execute_action(action, engine_state)
        
        print(f"Initial result: {result}")
        print(f"Position after initial step: ({npc.rect.x}, {npc.rect.y})")
        print(f"Active movement: {npc.llm_controller.active_movement}")
        print(f"Steps remaining: {npc.llm_controller.movement_steps_remaining}")
        
        # Continue autonomous movement
        step = 1
        current_time = 1000
        while npc.llm_controller.active_movement and step < 30:  # Safety limit
            current_time += 250  # Advance time
            
            # Check if should make decision
            should_decide = npc.llm_controller.should_make_decision(current_time, False)
            print(f"  Step {step}: should_decide={should_decide}, remaining={npc.llm_controller.movement_steps_remaining}")
            
            if should_decide:
                # Simulate engine state for autonomous movement
                engine_state_copy = engine_state.copy()
                engine_state_copy["current_time"] = current_time
                engine_state_copy["player_spoke"] = False
                
                result = npc.llm_controller.npc_decision_tick(engine_state_copy)
                print(f"    Result: {result}, pos: ({npc.rect.x}, {npc.rect.y})")
                
                if result and result.startswith("blocked"):
                    break
                step += 1
            else:
                break
        
        final_x = npc.rect.x
        actual_distance = final_x - start_x
        actual_tiles = actual_distance / 32.0
        
        print(f"Final position: ({final_x}, {npc.rect.y})")
        print(f"Actual distance: {actual_distance} pixels ({actual_tiles:.1f} tiles)")
        
        # Check if distance matches expectation
        expected_pixels = expected_tiles * 32
        tolerance = 8  # Allow some tolerance
        
        if abs(actual_distance - expected_pixels) <= tolerance:
            print(f"✅ SUCCESS: Distance matches expectation!")
        else:
            print(f"❌ MISMATCH: Expected {expected_pixels:.0f}px, got {actual_distance}px")
        
        print("-" * 30)
    
    print(f"\n🎯 Usage Examples:")
    print(f"Player: 'step aside' → NPC uses move_short (16 pixels)")
    print(f"Player: 'move east' → NPC uses move_dir (32 pixels)")  
    print(f"Player: 'walk away' → NPC uses move_long (96 pixels)")
    
    print(f"\n📋 JSON Examples:")
    print(f'Short:  {{"action":"move_short","args":{{"direction":"E"}}}}')
    print(f'Medium: {{"action":"move_dir","args":{{"direction":"E"}}}}')
    print(f'Long:   {{"action":"move_long","args":{{"direction":"E"}}}}')


def test_action_parsing():
    """Test that the new actions parse correctly"""
    
    print(f"\n🔍 Testing Action Parsing")
    print("-" * 30)
    
    from npc.actions import parse_action
    
    test_cases = [
        ('{"action":"move_short","args":{"direction":"N"}}', "move_short"),
        ('{"action":"move_dir","args":{"direction":"E"}}', "move_dir"),
        ('{"action":"move_long","args":{"direction":"S"}}', "move_long"),
    ]
    
    for json_input, expected_action in test_cases:
        action, error = parse_action(json_input)
        
        if error:
            print(f"❌ Parse error for {expected_action}: {error}")
        elif action.action == expected_action:
            print(f"✅ {expected_action} parsed correctly")
        else:
            print(f"❌ Expected {expected_action}, got {action.action}")


if __name__ == "__main__":
    test_movement_distances()
    test_action_parsing()