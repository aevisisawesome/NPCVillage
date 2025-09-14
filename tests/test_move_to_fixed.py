#!/usr/bin/env python3
"""
Test the fixed move_to action.
"""

from zelda_game_llm_integration import create_llm_shopkeeper
from npc.actions import parse_action
import pygame
import time

pygame.init()

def test_move_to_fixed():
    """Test that move_to now works with autonomous movement"""
    
    print("🎯 Fixed Move_To Test")
    print("=" * 60)
    
    npc = create_llm_shopkeeper(400, 250)
    
    print(f"NPC starting position: ({npc.rect.x}, {npc.rect.y})")
    print(f"NPC center: ({npc.rect.centerx}, {npc.rect.centery})")
    
    # Test move_to action
    target_tile_x, target_tile_y = 5, 5
    target_world_x = target_tile_x * 32
    target_world_y = target_tile_y * 32
    
    print(f"Target: tile ({target_tile_x}, {target_tile_y}) = world ({target_world_x}, {target_world_y})")
    
    # Parse the action
    json_input = f'{{"action":"move_to","args":{{"x":{target_tile_x},"y":{target_tile_y}}}}}'
    action, error = parse_action(json_input)
    
    if error:
        print(f"❌ Parse error: {error}")
        return
    
    print(f"✅ Action parsed: move_to to ({action.args.x}, {action.args.y})")
    
    # Mock engine state
    engine_state = {
        "npc": npc,
        "walls": [],
        "entities": [],
        "characters": [npc],
        "current_time": 1000
    }
    
    # Execute the action
    print(f"\n🚀 Executing move_to action...")
    result = npc.llm_controller.execute_action(action, engine_state)
    print(f"Initial result: {result}")
    
    if result == "ok":
        print(f"✅ Move_to started successfully")
        print(f"Active movement: {npc.llm_controller.active_movement}")
        print(f"Movement target: {npc.llm_controller.movement_target}")
        print(f"Steps remaining: {npc.llm_controller.movement_steps_remaining}")
        
        # Simulate autonomous movement continuation
        print(f"\n🔄 Simulating autonomous movement...")
        step_count = 0
        max_steps = 50  # Safety limit
        
        while (npc.llm_controller.active_movement == "move_to" and 
               npc.llm_controller.movement_steps_remaining > 0 and 
               step_count < max_steps):
            
            step_count += 1
            engine_state["current_time"] += 200  # Simulate time passing
            
            # Check if should continue movement
            if npc.llm_controller.should_make_decision(engine_state["current_time"]):
                result = npc.llm_controller.npc_decision_tick(engine_state)
                print(f"Step {step_count}: {result} - Position: ({npc.rect.x}, {npc.rect.y})")
                
                if result != "ok":
                    break
            
            # Small delay to see movement
            time.sleep(0.1)
        
        print(f"\n📊 Final Results:")
        print(f"Final position: ({npc.rect.x}, {npc.rect.y})")
        print(f"Final center: ({npc.rect.centerx}, {npc.rect.centery})")
        print(f"Target was: ({target_world_x}, {target_world_y})")
        
        # Calculate final distance
        import math
        dx = target_world_x - npc.rect.centerx
        dy = target_world_y - npc.rect.centery
        final_distance = math.sqrt(dx*dx + dy*dy)
        print(f"Final distance to target: {final_distance:.1f} pixels")
        
        if final_distance < 20:
            print("✅ SUCCESS: NPC reached the target!")
        else:
            print("⚠️  PARTIAL: NPC moved toward target but didn't reach it")
        
        print(f"Total steps taken: {step_count}")
        print(f"Active movement: {npc.llm_controller.active_movement}")
        
    else:
        print(f"❌ Move_to failed: {result}")


if __name__ == "__main__":
    test_move_to_fixed()