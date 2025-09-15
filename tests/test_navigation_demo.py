"""
Demonstration of the Hierarchical Navigation System
Shows the system working with a proper multi-region layout
"""

import sys
import os
import time

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from npc.navigation import HierarchicalNavigator, PathQuery


class MockWall:
    """Mock wall rectangle for testing"""
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height


def create_working_multi_region_layout():
    """Create a layout that definitely has multiple regions"""
    navigator = HierarchicalNavigator(30, 20)
    
    # Start with all tiles blocked
    for y in range(20):
        for x in range(30):
            navigator.set_tile_walkable(x, y, False)
    
    # Create Room 1 (left side)
    for y in range(5, 15):
        for x in range(5, 12):
            navigator.set_tile_walkable(x, y, True)
    
    # Create Room 2 (right side)  
    for y in range(5, 15):
        for x in range(18, 25):
            navigator.set_tile_walkable(x, y, True)
    
    # Create connecting hallway
    for x in range(12, 18):
        navigator.set_tile_walkable(x, 10, True)  # Horizontal hallway
    
    # Connect hallway to rooms
    navigator.set_tile_walkable(12, 10, True)  # Connection to room 1
    navigator.set_tile_walkable(17, 10, True)  # Connection to room 2
    
    navigator.build_regions_and_portals()
    
    print(f"Created layout: {len(navigator.regions)} regions, {len(navigator.portals)} portals")
    navigator.debug_print_grid(highlight_regions=True)
    
    return navigator


def demo_basic_pathfinding():
    """Demonstrate basic pathfinding capabilities"""
    print("🎯 HIERARCHICAL NAVIGATION SYSTEM DEMO")
    print("=" * 50)
    
    navigator = create_working_multi_region_layout()
    
    print("\n1. SAME REGION PATHFINDING")
    print("-" * 30)
    
    # Path within Room 1
    query = PathQuery(6*32, 8*32, 10*32, 12*32)  # Within left room
    response = navigator.find_path(query)
    
    if response.ok:
        print(f"✅ Same region path: {len(response.waypoints)} waypoints")
        print(f"   Cost: {response.total_cost:.1f}")
        print(f"   Waypoints: {[(int(x//32), int(y//32)) for x, y in response.waypoints]}")
    else:
        print(f"❌ Same region path failed: {response.reason}")
    
    print("\n2. CROSS-REGION PATHFINDING")
    print("-" * 30)
    
    if len(navigator.regions) > 1:
        # Path from Room 1 to Room 2
        query = PathQuery(8*32, 10*32, 20*32, 10*32)  # Left room to right room
        response = navigator.find_path(query)
        
        if response.ok:
            print(f"✅ Cross-region path: {len(response.waypoints)} waypoints")
            print(f"   Cost: {response.total_cost:.1f}")
            print(f"   Waypoints: {[(int(x//32), int(y//32)) for x, y in response.waypoints]}")
            
            # Check if path goes through expected portal areas
            portal_used = False
            for waypoint in response.waypoints:
                wx, wy = waypoint
                tile_x, tile_y = int(wx // 32), int(wy // 32)
                if 12 <= tile_x <= 17 and tile_y == 10:  # Hallway area
                    portal_used = True
                    break
            
            if portal_used:
                print("✅ Path correctly uses portal/hallway")
            else:
                print("⚠️ Path may not use expected portal")
        else:
            print(f"❌ Cross-region path failed: {response.reason}")
    else:
        print("⚠️ Only one region found - cannot test cross-region pathfinding")
    
    print("\n3. PORTAL CONTROL")
    print("-" * 30)
    
    if len(navigator.portals) > 0:
        portal_id = list(navigator.portals.keys())[0]
        
        # Close portal
        navigator.set_portal_open(portal_id, False)
        print(f"Closed portal: {portal_id}")
        
        # Try pathfinding with closed portal
        query = PathQuery(8*32, 10*32, 20*32, 10*32)
        response = navigator.find_path(query)
        
        if not response.ok:
            print(f"✅ Closed portal blocks path: {response.reason}")
        else:
            print(f"⚠️ Path found despite closed portal (may have alternate route)")
        
        # Reopen portal
        navigator.set_portal_open(portal_id, True)
        print(f"Reopened portal: {portal_id}")
    else:
        print("⚠️ No portals found for testing")
    
    print("\n4. THETA* SMOOTHING")
    print("-" * 30)
    
    # Create a path that can be smoothed
    waypoints = [
        (100, 100),
        (132, 100),
        (164, 100),
        (196, 100),
        (228, 100)
    ]
    
    smoothed = navigator._theta_star_smooth(waypoints)
    
    print(f"Original waypoints: {len(waypoints)}")
    print(f"Smoothed waypoints: {len(smoothed)}")
    print(f"Reduction: {len(waypoints) - len(smoothed)} waypoints removed")
    
    if len(smoothed) < len(waypoints):
        print("✅ Theta* smoothing working correctly")
    else:
        print("⚠️ No smoothing applied (may be due to obstacles)")
    
    print("\n5. WAYPOINT FOLLOWING")
    print("-" * 30)
    
    test_waypoints = [(100, 100), (200, 100), (300, 100)]
    
    # Test getting next waypoint from different positions
    positions = [(90, 90), (150, 100), (290, 90)]
    
    for pos in positions:
        next_wp = navigator.get_next_waypoint(pos[0], pos[1], test_waypoints, tolerance=16)
        print(f"From {pos} -> Next waypoint: {next_wp}")
    
    print("\n6. PERFORMANCE TEST")
    print("-" * 30)
    
    # Time multiple pathfinding queries
    query_times = []
    
    for i in range(10):
        start_time = time.time()
        query = PathQuery(6*32 + i*10, 8*32, 20*32 - i*5, 12*32)
        response = navigator.find_path(query)
        query_time = time.time() - start_time
        query_times.append(query_time)
    
    avg_time = sum(query_times) / len(query_times)
    max_time = max(query_times)
    
    print(f"Average query time: {avg_time*1000:.1f}ms")
    print(f"Maximum query time: {max_time*1000:.1f}ms")
    
    if max_time < 0.005:
        print("✅ Performance excellent (<5ms)")
    elif max_time < 0.050:
        print("✅ Performance good (<50ms)")
    else:
        print("⚠️ Performance could be improved")
    
    print("\n" + "=" * 50)
    print("🎉 HIERARCHICAL NAVIGATION DEMO COMPLETE")
    
    # Summary
    print(f"\nSUMMARY:")
    print(f"- Regions found: {len(navigator.regions)}")
    print(f"- Portals found: {len(navigator.portals)}")
    print(f"- Grid size: {navigator.grid_width}x{navigator.grid_height}")
    print(f"- Average query time: {avg_time*1000:.1f}ms")
    
    return True


def demo_integration_with_npc():
    """Demonstrate integration with NPC controller"""
    print("\n🤖 NPC INTEGRATION DEMO")
    print("-" * 30)
    
    try:
        from npc.controller import NPCController
        
        # Mock NPC
        class MockNPC:
            def __init__(self):
                self.rect = type('Rect', (), {'x': 100, 'y': 100, 'centerx': 116, 'centery': 116})()
                self.speed = 4
                self.name = "DemoNPC"
                self.current_health = 100
                self.is_moving = False
                self.speech_text = ""
                self.current_action = "idle"
            
            def move(self, dx, dy, walls, characters):
                self.rect.x += dx
                self.rect.y += dy
                self.rect.centerx = self.rect.x + 16
                self.rect.centery = self.rect.y + 16
                self.is_moving = True
            
            def say(self, text):
                self.speech_text = text
        
        npc = MockNPC()
        controller = NPCController(npc)
        
        # Initialize navigation
        navigator = create_working_multi_region_layout()
        controller.navigator = navigator
        
        print("✅ NPC Controller integration successful")
        print(f"   Navigator: {type(controller.navigator).__name__}")
        print(f"   Regions: {len(controller.navigator.regions)}")
        print(f"   Portals: {len(controller.navigator.portals)}")
        
        # Test move_to with navigation
        from npc.actions import MoveToArgs
        
        args = MoveToArgs(x=20, y=10)  # Target tile
        engine_state = {
            "npc": npc,
            "walls": [],
            "characters": [npc],
            "current_time": 1000
        }
        
        result = controller._execute_move_to(args, engine_state)
        print(f"✅ Move_to execution: {result}")
        
        if controller.current_waypoints:
            print(f"   Generated waypoints: {len(controller.current_waypoints)}")
        
        return True
        
    except ImportError as e:
        print(f"⚠️ NPC integration test skipped: {e}")
        return True


if __name__ == "__main__":
    success = demo_basic_pathfinding()
    
    if success:
        demo_integration_with_npc()
    
    print("\n🎯 Demo completed successfully!")
    exit(0)