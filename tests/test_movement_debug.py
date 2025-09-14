#!/usr/bin/env python3
"""
Debug NPC movement issues - test if movement is working correctly.
"""

from zelda_game_llm_integration import create_llm_shopkeeper
import pygame

# Initialize pygame for rect operations
pygame.init()

def test_npc_movement():
    """Test NPC movement mechanics"""
    
    print("🚶 Testing NPC Movement")
    print("-" * 40)
    
    # Create shopkeeper
    npc = create_llm_shopkeeper(400, 250)
    
    print(f"Initial position: ({npc.rect.x}, {npc.rect.y})")
    print(f"Initial center: ({npc.rect.centerx}, {npc.rect.centery})")
    print(f"NPC speed: {npc.speed}")
    
    # Test movement in each direction
    directions = [
        ("North", 0, -npc.speed),
        ("East", npc.speed, 0), 
        ("South", 0, npc.speed),
        ("West", -npc.speed, 0)
    ]
    
    # Simple walls (shop boundaries from the game)
    walls = [
        pygame.Rect(300, 200, 200, 10),  # Top wall
        pygame.Rect(300, 390, 80, 10),   # Bottom left
        pygame.Rect(420, 390, 80, 10),   # Bottom right
        pygame.Rect(300, 200, 10, 190),  # Left wall
        pygame.Rect(490, 200, 10, 190),  # Right wall
    ]
    
    print(f"\nWalls present: {len(walls)} walls")
    for i, wall in enumerate(walls):
        print(f"  Wall {i+1}: ({wall.x}, {wall.y}) {wall.width}x{wall.height}")
    
    for direction_name, dx, dy in directions:
        print(f"\n--- Testing {direction_name} movement (dx={dx}, dy={dy}) ---")
        
        # Store original position
        orig_x, orig_y = npc.rect.x, npc.rect.y
        orig_center_x, orig_center_y = npc.rect.centerx, npc.rect.centery
        
        print(f"Before: pos=({orig_x}, {orig_y}), center=({orig_center_x}, {orig_center_y})")
        
        # Test movement
        npc.move(dx, dy, walls, [])
        
        new_x, new_y = npc.rect.x, npc.rect.y
        new_center_x, new_center_y = npc.rect.centerx, npc.rect.centery
        
        print(f"After:  pos=({new_x}, {new_y}), center=({new_center_x}, {new_center_y})")
        
        # Check if movement occurred
        moved = (new_x != orig_x) or (new_y != orig_y)
        distance_moved = ((new_x - orig_x)**2 + (new_y - orig_y)**2)**0.5
        
        if moved:
            print(f"✅ Moved {distance_moved:.1f} pixels")
            print(f"   is_moving flag: {npc.is_moving}")
        else:
            print(f"❌ No movement occurred")
            print(f"   is_moving flag: {npc.is_moving}")
            
            # Check why movement failed
            test_rect = npc.rect.copy()
            test_rect.x += dx
            test_rect.y += dy
            
            # Check boundaries
            if test_rect.left < 0 or test_rect.right > 800 or test_rect.top < 0 or test_rect.bottom > 600:
                print(f"   Reason: Would go out of bounds")
                print(f"   Test rect: ({test_rect.x}, {test_rect.y}) {test_rect.width}x{test_rect.height}")
                print(f"   Bounds check: left={test_rect.left}, right={test_rect.right}, top={test_rect.top}, bottom={test_rect.bottom}")
            
            # Check wall collisions
            for i, wall in enumerate(walls):
                if test_rect.colliderect(wall):
                    print(f"   Reason: Would collide with wall {i+1}")
                    print(f"   Wall: ({wall.x}, {wall.y}) {wall.width}x{wall.height}")
                    break
    
    print(f"\n" + "=" * 40)
    print("🔍 MOVEMENT ANALYSIS:")
    print(f"NPC rect size: {npc.rect.width}x{npc.rect.height}")
    print(f"NPC speed: {npc.speed} pixels per move")
    print(f"Current position: ({npc.rect.x}, {npc.rect.y})")
    
    # Check if NPC is trapped
    can_move_any_direction = False
    for direction_name, dx, dy in directions:
        test_rect = npc.rect.copy()
        test_rect.x += dx
        test_rect.y += dy
        
        # Check if this direction is valid
        bounds_ok = (test_rect.left >= 0 and test_rect.right <= 800 and 
                    test_rect.top >= 0 and test_rect.bottom <= 600)
        
        wall_collision = False
        if bounds_ok:
            for wall in walls:
                if test_rect.colliderect(wall):
                    wall_collision = True
                    break
        
        if bounds_ok and not wall_collision:
            can_move_any_direction = True
            print(f"✅ Can move {direction_name}")
        else:
            reason = "out of bounds" if not bounds_ok else "wall collision"
            print(f"❌ Cannot move {direction_name} ({reason})")
    
    if not can_move_any_direction:
        print("⚠️  NPC appears to be trapped!")
    else:
        print("✅ NPC has valid movement options")


def test_controller_movement():
    """Test movement through the controller"""
    print(f"\n🎮 Testing Controller Movement")
    print("-" * 40)
    
    npc = create_llm_shopkeeper(400, 250)
    
    # Test controller movement
    from npc.actions import Action, MoveDirArgs
    
    engine_state = {
        "walls": [pygame.Rect(300, 200, 200, 10)],  # Just one wall for testing
        "characters": [npc]
    }
    
    # Test east movement
    action = Action(action="move_dir", args=MoveDirArgs(direction="E"))
    
    print(f"Before controller move: ({npc.rect.x}, {npc.rect.y})")
    result = npc.llm_controller._execute_move_dir(action.args, engine_state)
    print(f"After controller move: ({npc.rect.x}, {npc.rect.y})")
    print(f"Controller result: {result}")


if __name__ == "__main__":
    test_npc_movement()
    test_controller_movement()