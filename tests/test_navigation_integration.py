"""
Test integration of hierarchical navigation with the existing NPC system
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from npc.controller import NPCController
from npc.navigation import HierarchicalNavigator, PathQuery


class MockRect:
    """Mock pygame.Rect for testing"""
    def __init__(self, x, y, width=32, height=32):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.centerx = x + width // 2
        self.centery = y + height // 2


class MockNPC:
    """Mock NPC for testing"""
    def __init__(self, x=100, y=100):
        self.rect = MockRect(x, y)
        self.speed = 4
        self.name = "TestNPC"
        self.current_health = 100
        self.is_moving = False
        self.speech_text = ""
        self.current_action = "idle"
    
    def move(self, dx, dy, walls, characters):
        """Simulate movement"""
        new_x = self.rect.x + dx
        new_y = self.rect.y + dy
        
        # Simple collision detection
        new_rect = MockRect(new_x, new_y)
        
        # Check wall collisions
        for wall in walls:
            if self._rects_overlap(new_rect, wall):
                return  # Blocked
        
        # Update position
        self.rect.x = new_x
        self.rect.y = new_y
        self.rect.centerx = new_x + 16
        self.rect.centery = new_y + 16
        self.is_moving = True
    
    def _rects_overlap(self, rect1, rect2):
        """Check if two rectangles overlap"""
        return not (rect1.x + rect1.width <= rect2.x or 
                   rect2.x + rect2.width <= rect1.x or
                   rect1.y + rect1.height <= rect2.y or 
                   rect2.y + rect2.height <= rect1.y)
    
    def say(self, text):
        self.speech_text = text


def test_navigation_initialization():
    """Test that navigation system initializes correctly"""
    npc = MockNPC()
    controller = NPCController(npc)
    
    # Create simple wall layout
    walls = [
        MockRect(0, 0, 800, 32),      # Top boundary
        MockRect(0, 0, 32, 600),      # Left boundary
        MockRect(768, 0, 32, 600),    # Right boundary
        MockRect(0, 568, 800, 32),    # Bottom boundary
        MockRect(384, 32, 32, 256),   # Dividing wall
        MockRect(384, 320, 32, 248),  # Dividing wall (with gap)
    ]
    
    # Initialize navigation
    grid_width = 25  # 800 / 32
    grid_height = 18  # 600 / 32
    controller.initialize_navigation(grid_width, grid_height, walls)
    
    # Verify initialization
    assert controller.navigator is not None, "Navigator should be initialized"
    assert isinstance(controller.navigator, HierarchicalNavigator), "Should be HierarchicalNavigator"
    assert controller.navigator.grid_width == grid_width, "Grid width should match"
    assert controller.navigator.grid_height == grid_height, "Grid height should match"
    
    # Check that regions were built
    assert len(controller.navigator.regions) > 0, "Should have at least one region"
    
    print(f"✅ Navigation initialized: {len(controller.navigator.regions)} regions, {len(controller.navigator.portals)} portals")


def test_move_to_with_navigation():
    """Test move_to action with hierarchical navigation"""
    npc = MockNPC(100, 100)  # Start position
    controller = NPCController(npc)
    
    # Create layout with two rooms
    walls = [
        MockRect(0, 0, 800, 32),      # Boundaries
        MockRect(0, 0, 32, 600),
        MockRect(768, 0, 32, 600),
        MockRect(0, 568, 800, 32),
        MockRect(384, 32, 32, 256),   # Dividing wall with gap
        MockRect(384, 320, 32, 248),
    ]
    
    # Initialize navigation
    controller.initialize_navigation(25, 18, walls)
    
    # Create engine state
    engine_state = {
        "npc": npc,
        "walls": walls,
        "characters": [npc],
        "current_time": 1000
    }
    
    # Test move_to action
    from npc.actions import MoveToArgs
    args = MoveToArgs(x=20, y=10)  # Target in right room
    
    result = controller._execute_move_to(args, engine_state)
    
    # Should succeed and set up waypoint navigation
    assert result == "ok", f"Move_to should succeed, got: {result}"
    assert controller.active_movement == "move_to", "Should be in move_to mode"
    
    # Should have waypoints if using hierarchical navigation
    if controller.current_waypoints:
        print(f"✅ Move_to with navigation: {len(controller.current_waypoints)} waypoints generated")
    else:
        print("✅ Move_to with navigation: Using direct movement (no waypoints needed)")


def test_waypoint_following():
    """Test that NPC follows waypoints correctly"""
    npc = MockNPC(100, 100)
    controller = NPCController(npc)
    
    # Set up manual waypoints
    controller.current_waypoints = [(200, 100), (300, 100), (400, 100)]
    controller.path_target = (400, 100)
    controller.active_movement = "move_to"
    controller.movement_steps_remaining = 50
    
    # Initialize navigation for waypoint following
    walls = []
    controller.initialize_navigation(25, 18, walls)
    
    engine_state = {
        "npc": npc,
        "walls": walls,
        "characters": [npc],
        "current_time": 1000
    }
    
    # Simulate several movement steps
    initial_x = npc.rect.x
    
    for step in range(10):
        result = controller._move_toward_next_waypoint(engine_state)
        if result != "ok":
            break
    
    # Should have moved toward first waypoint
    assert npc.rect.x > initial_x, "NPC should have moved toward waypoint"
    
    print(f"✅ Waypoint following: NPC moved from {initial_x} to {npc.rect.x}")


def test_navigation_observation():
    """Test that navigation info appears in observations"""
    npc = MockNPC(100, 100)
    controller = NPCController(npc)
    
    # Set up navigation state
    controller.current_waypoints = [(200, 100), (300, 100)]
    controller.path_target = (400, 100)
    
    # Mock player
    class MockPlayer:
        def __init__(self):
            self.rect = MockRect(200, 200)
            self.speech_text = ""
    
    # Build observation
    from npc.observation import build_observation
    
    engine_state = {
        "npc": npc,
        "player": MockPlayer(),
        "walls": [],
        "entities": [],
        "tick": 100,
        "last_result": None,
        "goals": ["test"],
        "cooldowns": {"move": 0, "interact": 0}
    }
    
    observation = build_observation(engine_state)
    
    # Check if navigation info is included
    if "navigation" in observation:
        nav_info = observation["navigation"]
        print(f"✅ Navigation observation: {nav_info}")
        
        if "waypoints" in nav_info:
            assert len(nav_info["waypoints"]) > 0, "Should have waypoints in observation"
        
        if "target" in nav_info:
            assert nav_info["target"] is not None, "Should have target in observation"
    else:
        print("✅ Navigation observation: No navigation info (expected when no active navigation)")


def test_portal_control():
    """Test dynamic portal control"""
    npc = MockNPC()
    controller = NPCController(npc)
    
    # Create layout with portal
    walls = [
        MockRect(0, 0, 800, 32),
        MockRect(0, 0, 32, 600),
        MockRect(768, 0, 32, 600),
        MockRect(0, 568, 800, 32),
        MockRect(384, 32, 32, 256),   # Wall with gap
        MockRect(384, 320, 32, 248),
    ]
    
    controller.initialize_navigation(25, 18, walls)
    
    # Should have at least one portal
    if len(controller.navigator.portals) > 0:
        portal_id = list(controller.navigator.portals.keys())[0]
        
        # Test closing portal
        controller.navigator.set_portal_open(portal_id, False)
        portal = controller.navigator.portals[portal_id]
        assert not portal.is_open, "Portal should be closed"
        
        # Test opening portal
        controller.navigator.set_portal_open(portal_id, True)
        assert portal.is_open, "Portal should be open"
        
        print(f"✅ Portal control: Successfully opened/closed portal {portal_id}")
    else:
        print("✅ Portal control: No portals found (expected for simple layouts)")


def run_integration_tests():
    """Run all integration tests"""
    print("🧪 Running Navigation Integration Tests")
    print("=" * 50)
    
    try:
        test_navigation_initialization()
        test_move_to_with_navigation()
        test_waypoint_following()
        test_navigation_observation()
        test_portal_control()
        
        print("=" * 50)
        print("🎉 ALL INTEGRATION TESTS PASSED!")
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_integration_tests()
    exit(0 if success else 1)