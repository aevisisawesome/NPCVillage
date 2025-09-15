"""
Test movement continuation to ensure NPCs don't get stuck
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from npc.controller import NPCController
from npc.actions import MoveToArgs


def test_movement_continuation():
    """Test that movement continues properly without getting stuck"""
    print("🔄 TESTING MOVEMENT CONTINUATION")
    print("=" * 50)
    
    # Mock NPC
    class MockNPC:
        def __init__(self):
            self.rect = type('Rect', (), {'x': 410, 'y': 260, 'centerx': 426, 'centery': 276})()
            self.speed = 4
            self.name = "TestNPC"
            self.current_health = 100
            self.is_moving = False
            self.speech_text = ""
            self.current_action = "idle"
        
        def move(self, dx, dy, walls, characters):
            # Simulate movement
            old_x, old_y = self.rect.x, self.rect.y
            self.rect.x += dx
            self.rect.y += dy
            self.rect.centerx = self.rect.x + 16
            self.rect.centery = self.rect.y + 16
            self.is_moving = True
            distance_moved = ((self.rect.x - old_x)**2 + (self.rect.y - old_y)**2)**0.5
            print(f"DEBUG: {self.name} moved {distance_moved:.1f} pixels to ({self.rect.x:.1f}, {self.rect.y:.1f})")
        
        def say(self, text):
            self.speech_text = text
    
    # Create controller and initialize navigation
    npc = MockNPC()
    controller = NPCController(npc)
    
    # Initialize navigation
    walls = []
    controller.initialize_navigation(25, 18, walls)
    
    print(f"✅ Navigation initialized")
    
    # Set up a move_to command
    args = MoveToArgs(x=12, y=14)  # Target tile
    engine_state = {
        "npc": npc,
        "walls": walls,
        "characters": [npc],
        "current_time": 1000,
        "player_spoke": True,
        "tick": 100
    }
    
    print("\n1. INITIAL MOVE_TO COMMAND")
    print("-" * 30)
    
    # Execute initial move_to
    result = controller._execute_move_to(args, engine_state)
    print(f"Initial result: {result}")
    print(f"Active movement: {controller.active_movement}")
    print(f"Steps remaining: {controller.movement_steps_remaining}")
    print(f"Waypoints: {len(controller.current_waypoints) if controller.current_waypoints else 0}")
    
    if controller.current_waypoints:
        print(f"Target waypoint: {controller.current_waypoints[0] if controller.current_waypoints else 'None'}")
    
    print("\n2. MOVEMENT CONTINUATION SIMULATION")
    print("-" * 40)
    
    # Simulate game ticks with proper timing
    for step in range(20):  # Test up to 20 steps
        print(f"\nStep {step + 1}:")
        
        # Update time (simulate 100ms per tick)
        engine_state["current_time"] += 100
        engine_state["player_spoke"] = False  # Only first tick has player speech
        
        # Check if should make decision
        should_decide = controller.should_make_decision(
            engine_state["current_time"], 
            engine_state.get("player_spoke", False), 
            False
        )
        
        print(f"  Should make decision: {should_decide}")
        print(f"  Active movement: {controller.active_movement}")
        print(f"  Steps remaining: {controller.movement_steps_remaining}")
        
        if should_decide:
            try:
                result = controller.npc_decision_tick(engine_state)
                print(f"  Decision result: {result}")
                
                if controller.current_waypoints:
                    print(f"  Waypoints remaining: {len(controller.current_waypoints)}")
                    print(f"  Next waypoint: {controller.current_waypoints[0] if controller.current_waypoints else 'None'}")
                else:
                    print("  No waypoints remaining")
                
                # Check if movement is complete
                if not controller.active_movement or controller.movement_steps_remaining <= 0:
                    print("  ✅ Movement completed!")
                    break
                    
            except Exception as e:
                print(f"  ❌ ERROR: {e}")
                return False
        else:
            print("  No decision needed")
            
            # If we're not making decisions but should be moving, something is wrong
            if controller.active_movement and controller.movement_steps_remaining > 0:
                print("  ⚠️ WARNING: Should be moving but not making decisions!")
                
                # Check timing
                time_since_last = engine_state["current_time"] - controller.last_decision_time
                print(f"  Time since last decision: {time_since_last}ms")
    
    print("\n3. FINAL STATE CHECK")
    print("-" * 25)
    
    final_x, final_y = npc.rect.centerx, npc.rect.centery
    target_x, target_y = 12 * 32 + 16, 14 * 32 + 16  # Target position
    final_distance = ((final_x - target_x)**2 + (final_y - target_y)**2)**0.5
    
    print(f"Final position: ({final_x:.1f}, {final_y:.1f})")
    print(f"Target position: ({target_x}, {target_y})")
    print(f"Distance to target: {final_distance:.1f} pixels")
    
    if final_distance < 32:  # Within one tile
        print("✅ NPC reached target successfully!")
        return True
    else:
        print("❌ NPC did not reach target")
        return False


if __name__ == "__main__":
    success = test_movement_continuation()
    
    if success:
        print("\n🎉 Movement continuation test passed!")
        print("   The NPC should now move smoothly to targets.")
    else:
        print("\n❌ Movement continuation test failed!")
        print("   There may still be issues with movement.")
    
    exit(0 if success else 1)