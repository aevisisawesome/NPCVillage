"""
Test the navigation fix for the NoneType error
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from npc.controller import NPCController
from npc.actions import MoveToArgs


def test_navigation_fix():
    """Test that the navigation fix prevents the NoneType error"""
    print("🔧 TESTING NAVIGATION FIX")
    print("=" * 40)
    
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
            self.rect.x += dx
            self.rect.y += dy
            self.rect.centerx = self.rect.x + 16
            self.rect.centery = self.rect.y + 16
            self.is_moving = True
            print(f"DEBUG: {self.name} moved to ({self.rect.x}, {self.rect.y})")
        
        def say(self, text):
            self.speech_text = text
    
    # Create controller
    npc = MockNPC()
    controller = NPCController(npc)
    
    # Initialize navigation (this creates the navigator)
    walls = []
    controller.initialize_navigation(25, 18, walls)
    
    print(f"✅ Navigation initialized: {controller.navigator is not None}")
    
    # Test move_to action
    args = MoveToArgs(x=12, y=14)
    engine_state = {
        "npc": npc,
        "walls": walls,
        "characters": [npc],
        "current_time": 1000
    }
    
    print("\n1. TESTING INITIAL MOVE_TO")
    print("-" * 30)
    
    result = controller._execute_move_to(args, engine_state)
    print(f"Move_to result: {result}")
    
    if controller.current_waypoints:
        print(f"Waypoints generated: {len(controller.current_waypoints)}")
        print(f"Active movement: {controller.active_movement}")
        print(f"Steps remaining: {controller.movement_steps_remaining}")
    
    print("\n2. TESTING CONTINUED MOVEMENT")
    print("-" * 30)
    
    # Simulate several movement continuation steps
    for step in range(5):
        print(f"\nStep {step + 1}:")
        
        # This should not cause a NoneType error anymore
        try:
            result = controller._continue_move_to(args, engine_state)
            print(f"  Continue result: {result}")
            
            if controller.current_waypoints:
                print(f"  Waypoints remaining: {len(controller.current_waypoints)}")
            else:
                print("  No waypoints remaining")
                
            if controller.movement_steps_remaining <= 0:
                print("  Movement completed")
                break
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
            return False
    
    print("\n3. TESTING WITHOUT NAVIGATOR")
    print("-" * 30)
    
    # Test the scenario that was causing the bug
    controller.navigator = None  # Simulate missing navigator
    controller.current_waypoints = [(400, 464), (384, 448)]  # Set some waypoints
    controller.active_movement = "move_to"
    controller.movement_steps_remaining = 10
    
    try:
        result = controller._move_toward_next_waypoint(engine_state)
        print(f"✅ Move toward waypoint without navigator: {result}")
    except Exception as e:
        print(f"❌ Error without navigator: {e}")
        return False
    
    print("\n" + "=" * 40)
    print("🎉 NAVIGATION FIX TEST COMPLETE")
    print("✅ All tests passed - NoneType error fixed!")
    
    return True


if __name__ == "__main__":
    success = test_navigation_fix()
    
    if success:
        print("\n🚀 Navigation system is now stable!")
        print("   The game should work without NoneType errors.")
    
    exit(0 if success else 1)