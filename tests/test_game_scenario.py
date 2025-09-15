"""
Test the exact game scenario that was causing the NoneType error
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from npc.controller import NPCController
from npc.actions import MoveToArgs


def test_game_scenario():
    """Test the exact scenario from the game that was failing"""
    print("🎮 TESTING GAME SCENARIO")
    print("=" * 40)
    
    # Mock NPC that matches the game NPC
    class MockNPC:
        def __init__(self):
            self.rect = type('Rect', (), {'x': 410, 'y': 260, 'centerx': 410, 'centery': 260})()
            self.speed = 4
            self.name = "Garruk Ironhand"
            self.current_health = 100
            self.is_moving = False
            self.speech_text = ""
            self.current_action = "idle"
        
        def move(self, dx, dy, walls, characters):
            # Simulate movement like in the game
            old_x, old_y = self.rect.x, self.rect.y
            self.rect.x += dx
            self.rect.y += dy
            self.rect.centerx = self.rect.x + 16
            self.rect.centery = self.rect.y + 16
            self.is_moving = True
            print(f"DEBUG: {self.name} moved to ({self.rect.x}, {self.rect.y})")
        
        def say(self, text):
            self.speech_text = text
    
    # Create controller and initialize navigation like in the game
    npc = MockNPC()
    controller = NPCController(npc)
    
    # Mock shop walls like in the game
    class MockWall:
        def __init__(self, x, y, width, height):
            self.x = x
            self.y = y
            self.width = width
            self.height = height
    
    walls = [
        MockWall(300, 200, 200, 10),  # Top wall
        MockWall(300, 390, 80, 10),   # Bottom left
        MockWall(420, 390, 80, 10),   # Bottom right
        MockWall(300, 200, 10, 190),  # Left wall
        MockWall(490, 200, 10, 190),  # Right wall
    ]
    
    # Initialize navigation like in the game
    grid_width = 25  # 800 / 32
    grid_height = 18  # 600 / 32
    controller.initialize_navigation(grid_width, grid_height, walls)
    
    print(f"✅ Navigation initialized: {controller.navigator is not None}")
    
    # Simulate the exact scenario from the game
    print("\n1. SIMULATING PLAYER COMMAND: 'move to me'")
    print("-" * 50)
    
    # This is what the LLM decided: move_to (12, 14)
    args = MoveToArgs(x=12, y=14)
    engine_state = {
        "npc": npc,
        "player": type('Player', (), {'rect': type('Rect', (), {'centerx': 400, 'centery': 450})()})(),
        "walls": walls,
        "characters": [npc],
        "current_time": 1000,
        "player_spoke": True,
        "tick": 100
    }
    
    # Execute the initial move_to
    result = controller._execute_move_to(args, engine_state)
    print(f"Initial move_to result: {result}")
    print(f"Active movement: {controller.active_movement}")
    print(f"Movement steps remaining: {controller.movement_steps_remaining}")
    print(f"Current waypoints: {len(controller.current_waypoints) if controller.current_waypoints else 0}")
    
    print("\n2. SIMULATING CONTINUED MOVEMENT (THE PROBLEMATIC PART)")
    print("-" * 50)
    
    # This is where the error was occurring - during continued movement
    for step in range(10):
        print(f"\nStep {step + 1}:")
        
        # Update engine state for next tick
        engine_state["current_time"] += 200
        engine_state["player_spoke"] = False  # Only first tick has player speech
        
        try:
            # This calls npc_decision_tick which was causing the error
            result = controller.npc_decision_tick(engine_state)
            print(f"  Decision result: {result}")
            
            if controller.movement_steps_remaining <= 0:
                print("  Movement completed!")
                break
                
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            print(f"  Movement target: {controller.movement_target}")
            print(f"  Active movement: {controller.active_movement}")
            return False
    
    print("\n3. TESTING EDGE CASES")
    print("-" * 30)
    
    # Test case where movement_target becomes None
    controller.active_movement = "move_to"
    controller.movement_steps_remaining = 5
    controller.movement_target = None  # This was causing the error
    
    try:
        result = controller.npc_decision_tick(engine_state)
        print(f"✅ Handled None movement_target: {result}")
    except Exception as e:
        print(f"❌ Error with None movement_target: {e}")
        return False
    
    print("\n" + "=" * 40)
    print("🎉 GAME SCENARIO TEST COMPLETE")
    print("✅ All scenarios handled correctly!")
    
    return True


if __name__ == "__main__":
    success = test_game_scenario()
    
    if success:
        print("\n🚀 The game should now work without errors!")
        print("   Try: venv\\Scripts\\python.exe zelda_game_with_llm_npc.py")
        print("   Then say: 'move to me' or 'come to me'")
    
    exit(0 if success else 1)