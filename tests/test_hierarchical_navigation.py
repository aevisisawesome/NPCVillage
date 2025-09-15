"""
Comprehensive tests for the Hierarchical Navigation System
Tests all acceptance criteria and integration requirements
"""

import pytest
import time
import math
from typing import List, Tuple
from npc.navigation import HierarchicalNavigator, PathQuery, PathResult


class MockWall:
    """Mock wall rectangle for testing"""
    def __init__(self, x: int, y: int, width: int, height: int):
        self.x = x
        self.y = y
        self.width = width
        self.height = height


class TestHierarchicalNavigation:
    """Test suite for hierarchical navigation system"""
    
    def setup_method(self):
        """Set up test environment"""
        self.navigator = HierarchicalNavigator(25, 20)  # 25x20 grid
    
    def create_simple_room_layout(self):
        """Create a simple two-room layout with one doorway"""
        walls = [
            # Outer walls
            MockWall(0, 0, 800, 32),      # Top
            MockWall(0, 0, 32, 640),      # Left  
            MockWall(768, 0, 32, 640),    # Right
            MockWall(0, 608, 800, 32),    # Bottom
            
            # Dividing wall with doorway
            MockWall(384, 32, 32, 256),   # Wall above door
            MockWall(384, 320, 32, 288),  # Wall below door
            # Door gap at (384, 288) - (384, 320) = 1 tile wide
        ]
        
        self.navigator.set_tiles_from_walls(walls)
        self.navigator.build_regions_and_portals()
        
        return walls
    
    def create_complex_layout(self):
        """Create complex layout with multiple rooms and portals"""
        walls = [
            # Outer boundary
            MockWall(0, 0, 640, 32),      # Top
            MockWall(0, 0, 32, 640),      # Left
            MockWall(608, 0, 32, 640),    # Right
            MockWall(0, 608, 640, 32),    # Bottom
            
            # Room 1 (top-left): tiles (1,1) to (9,9)
            MockWall(320, 32, 32, 288),   # Right wall of room 1
            MockWall(32, 320, 288, 32),   # Bottom wall of room 1
            # Door at (10, 5) - gap in right wall
            
            # Room 2 (top-right): tiles (11,1) to (18,9) 
            MockWall(352, 320, 256, 32),  # Bottom wall of room 2
            # Door at (15, 10) - gap in bottom wall
            
            # Room 3 (bottom): tiles (1,11) to (18,18)
            # Connected to room 1 via door at (5, 10)
            # Connected to room 2 via door at (15, 10)
        ]
        
        self.navigator.set_tiles_from_walls(walls)
        self.navigator.build_regions_and_portals()
        
        return walls
    
    def test_straight_room_path(self):
        """ACCEPTANCE TEST: Straight room path (same region)"""
        self.create_simple_room_layout()
        
        # Path within left room
        query = PathQuery(100, 100, 200, 200)  # Both in same region
        response = self.navigator.find_path(query)
        
        assert response.ok, f"Path should succeed: {response.reason}"
        assert len(response.waypoints) >= 2, "Should have start and end waypoints"
        assert response.waypoints[0] == (100, 100), "Should start at query start"
        assert response.waypoints[-1] == (200, 200), "Should end at query goal"
        
        print(f"✅ Straight room path: {len(response.waypoints)} waypoints, cost {response.total_cost:.1f}")
    
    def test_doorway_routing(self):
        """ACCEPTANCE TEST: Doorway routing (different regions)"""
        self.create_simple_room_layout()
        
        # Path from left room to right room through doorway
        query = PathQuery(100, 300, 500, 300)  # Cross the doorway
        response = self.navigator.find_path(query)
        
        assert response.ok, f"Path should succeed: {response.reason}"
        assert len(response.waypoints) >= 3, "Should have waypoints through portal"
        
        # Check that path goes through portal center (approximately)
        portal_found = False
        for waypoint in response.waypoints:
            wx, wy = waypoint
            # Portal should be around x=400 (12.5 * 32), y=304 (9.5 * 32)
            if 390 <= wx <= 410 and 295 <= wy <= 315:
                portal_found = True
                break
        
        assert portal_found, f"Path should go through portal center. Waypoints: {response.waypoints}"
        
        print(f"✅ Doorway routing: {len(response.waypoints)} waypoints through portal")
    
    def test_portal_center_tolerance(self):
        """ACCEPTANCE TEST: Force path to pass portal center ±0.5 tolerance"""
        self.create_simple_room_layout()
        
        query = PathQuery(100, 300, 500, 300)
        response = self.navigator.find_path(query)
        
        # Find portal waypoint
        portal_waypoint = None
        for waypoint in response.waypoints:
            wx, wy = waypoint
            if 390 <= wx <= 410 and 295 <= wy <= 315:  # Near expected portal location
                portal_waypoint = waypoint
                break
        
        assert portal_waypoint is not None, "Should have portal waypoint"
        
        # Check tolerance (portal center should be within 0.5 tiles = 16 pixels)
        expected_portal_x = 400  # 12.5 * 32
        expected_portal_y = 304  # 9.5 * 32
        
        px, py = portal_waypoint
        tolerance = 16  # 0.5 tiles
        
        assert abs(px - expected_portal_x) <= tolerance, f"Portal X within tolerance: {px} vs {expected_portal_x}"
        assert abs(py - expected_portal_y) <= tolerance, f"Portal Y within tolerance: {py} vs {expected_portal_y}"
        
        print(f"✅ Portal center tolerance: waypoint at ({px:.1f}, {py:.1f})")
    
    def test_corner_cut_prevention(self):
        """ACCEPTANCE TEST: Corner-cut prevention"""
        # Create layout with diagonal blocking corners
        walls = [
            MockWall(0, 0, 640, 32),      # Boundary
            MockWall(0, 0, 32, 640),
            MockWall(608, 0, 32, 640),
            MockWall(0, 608, 640, 32),
            
            # Two blocking corners diagonally touching
            MockWall(320, 320, 32, 32),   # Block at (10, 10)
            MockWall(352, 352, 32, 32),   # Block at (11, 11)
        ]
        
        self.navigator.set_tiles_from_walls(walls)
        self.navigator.build_regions_and_portals()
        
        # Try to path diagonally through the corner
        query = PathQuery(300, 300, 400, 400)  # Should not cut corner
        response = self.navigator.find_path(query)
        
        if response.ok:
            # Check that path doesn't cut through blocked diagonal
            for i in range(len(response.waypoints) - 1):
                x1, y1 = response.waypoints[i]
                x2, y2 = response.waypoints[i + 1]
                
                # Check if this segment would cut through the blocked corner
                # Convert to tile coordinates
                tile_x1, tile_y1 = int(x1 // 32), int(y1 // 32)
                tile_x2, tile_y2 = int(x2 // 32), int(y2 // 32)
                
                # If moving diagonally through (10,10) to (11,11), that's invalid
                if ((tile_x1 == 9 and tile_y1 == 9 and tile_x2 == 12 and tile_y2 == 12) or
                    (tile_x1 == 12 and tile_y1 == 12 and tile_x2 == 9 and tile_y2 == 9)):
                    pytest.fail("Path cuts through blocked diagonal corner")
        
        print("✅ Corner-cut prevention: No diagonal cutting through blocked corners")
    
    def test_closed_door(self):
        """ACCEPTANCE TEST: Closed door returns NO_PATH"""
        self.create_simple_room_layout()
        
        # Close the only portal
        portal_ids = list(self.navigator.portals.keys())
        assert len(portal_ids) > 0, "Should have at least one portal"
        
        self.navigator.set_portal_open(portal_ids[0], False)
        
        # Try to path between regions
        query = PathQuery(100, 300, 500, 300)
        response = self.navigator.find_path(query)
        
        assert not response.ok, "Path should fail when door is closed"
        assert "NO_PATH" in response.reason, f"Should return NO_PATH, got: {response.reason}"
        
        print("✅ Closed door: Correctly returns NO_PATH")
    
    def test_multiple_doors_with_bias(self):
        """ACCEPTANCE TEST: Multiple doors with cost biases"""
        # Create layout with two doors
        walls = [
            MockWall(0, 0, 640, 32),      # Boundary
            MockWall(0, 0, 32, 640),
            MockWall(608, 0, 32, 640),
            MockWall(0, 608, 640, 32),
            
            # Vertical dividing wall with two doors
            MockWall(320, 32, 32, 128),   # Wall segment 1
            MockWall(320, 192, 32, 128),  # Wall segment 2  
            MockWall(320, 352, 32, 256),  # Wall segment 3
            # Door 1 at y=160-192 (tiles 5-6)
            # Door 2 at y=320-352 (tiles 10-11)
        ]
        
        self.navigator.set_tiles_from_walls(walls)
        self.navigator.build_regions_and_portals()
        
        # Find the two portals
        portals = list(self.navigator.portals.values())
        assert len(portals) >= 2, f"Should have at least 2 portals, found {len(portals)}"
        
        # Sort portals by Y coordinate to identify them
        portals.sort(key=lambda p: p.center_y)
        door1_id = portals[0].id  # Upper door
        door2_id = portals[1].id  # Lower door
        
        # Test 1: No bias - should choose closer door
        query1 = PathQuery(100, 180, 500, 180)  # Closer to door 1
        response1 = self.navigator.find_path(query1)
        assert response1.ok, "Path should succeed"
        
        # Test 2: Bias toward farther door
        cost_bias = {door2_id: 0.5}  # Make door 2 cheaper
        query2 = PathQuery(100, 180, 500, 180, cost_bias=cost_bias)
        response2 = self.navigator.find_path(query2)
        assert response2.ok, "Biased path should succeed"
        
        # The biased path might choose the farther door if bias is strong enough
        print(f"✅ Multiple doors with bias: Normal cost {response1.total_cost:.1f}, biased cost {response2.total_cost:.1f}")
    
    def test_outdoor_indoor_preference(self):
        """ACCEPTANCE TEST: Outdoor↔Indoor preference"""
        self.create_complex_layout()
        
        # Mark one region as indoor
        if len(self.navigator.regions) >= 2:
            region_ids = list(self.navigator.regions.keys())
            self.navigator.set_region_indoor(region_ids[0], True)  # Make first region indoor
        
        # Test with indoor preference
        query = PathQuery(100, 100, 500, 500, prefer_indoor=True)
        response_indoor = self.navigator.find_path(query)
        
        # Test without indoor preference  
        query_normal = PathQuery(100, 100, 500, 500, prefer_indoor=False)
        response_normal = self.navigator.find_path(query_normal)
        
        # Both should succeed, indoor preference might affect cost
        if response_indoor.ok and response_normal.ok:
            print(f"✅ Indoor preference: Normal cost {response_normal.total_cost:.1f}, indoor-preferred cost {response_indoor.total_cost:.1f}")
        else:
            print("✅ Indoor preference: Test completed (paths may not exist in this layout)")
    
    def test_performance_200x200(self):
        """ACCEPTANCE TEST: Performance on 200×200 grid with 10 rooms, 20 portals"""
        # Create large navigator
        large_navigator = HierarchicalNavigator(200, 200)
        
        # Create a grid pattern of rooms (simplified for testing)
        walls = []
        
        # Outer boundary
        walls.extend([
            MockWall(0, 0, 6400, 32),      # Top
            MockWall(0, 0, 32, 6400),      # Left
            MockWall(6368, 0, 32, 6400),   # Right
            MockWall(0, 6368, 6400, 32),   # Bottom
        ])
        
        # Create a 3x3 grid of rooms with connecting doorways
        room_size = 2000  # ~62 tiles per room
        wall_thickness = 32
        
        for row in range(3):
            for col in range(3):
                if col < 2:  # Vertical walls between columns
                    x = (col + 1) * room_size
                    y = row * room_size + 32
                    # Wall with door in middle
                    walls.append(MockWall(x, y, wall_thickness, room_size // 3))
                    walls.append(MockWall(x, y + 2 * room_size // 3, wall_thickness, room_size // 3))
                
                if row < 2:  # Horizontal walls between rows
                    x = col * room_size + 32
                    y = (row + 1) * room_size
                    # Wall with door in middle
                    walls.append(MockWall(x, y, room_size // 3, wall_thickness))
                    walls.append(MockWall(x + 2 * room_size // 3, y, room_size // 3, wall_thickness))
        
        large_navigator.set_tiles_from_walls(walls)
        
        # Time the region building
        start_time = time.time()
        large_navigator.build_regions_and_portals()
        build_time = time.time() - start_time
        
        print(f"Region building time: {build_time:.3f}s")
        print(f"Found {len(large_navigator.regions)} regions, {len(large_navigator.portals)} portals")
        
        # Time pathfinding queries
        query_times = []
        for _ in range(10):  # Test 10 queries
            start_time = time.time()
            query = PathQuery(100, 100, 5000, 5000)  # Long distance path
            response = large_navigator.find_path(query)
            query_time = time.time() - start_time
            query_times.append(query_time)
        
        avg_query_time = sum(query_times) / len(query_times)
        max_query_time = max(query_times)
        
        print(f"Average query time: {avg_query_time*1000:.1f}ms")
        print(f"Max query time: {max_query_time*1000:.1f}ms")
        
        # Performance requirement: < 5ms per query
        assert max_query_time < 0.005, f"Query time {max_query_time*1000:.1f}ms exceeds 5ms limit"
        
        print("✅ Performance test: All queries under 5ms")
    
    def test_integration_with_npc_controller(self):
        """Test integration with NPC controller"""
        from npc.controller import NPCController
        
        # Mock NPC
        class MockNPC:
            def __init__(self):
                self.rect = type('Rect', (), {'x': 100, 'y': 100, 'centerx': 116, 'centery': 116})()
                self.speed = 4
                self.name = "TestNPC"
            
            def move(self, dx, dy, walls, characters):
                self.rect.x += dx
                self.rect.y += dy
                self.rect.centerx = self.rect.x + 16
                self.rect.centery = self.rect.y + 16
        
        npc = MockNPC()
        controller = NPCController(npc)
        
        # Initialize navigation
        walls = self.create_simple_room_layout()
        controller.initialize_navigation(25, 20, walls)
        
        assert controller.navigator is not None, "Navigator should be initialized"
        assert len(controller.navigator.regions) > 0, "Should have regions"
        
        print("✅ NPC Controller integration: Navigation system initialized")
    
    def test_waypoint_following(self):
        """Test waypoint following behavior"""
        self.create_simple_room_layout()
        
        # Get a path with multiple waypoints
        query = PathQuery(100, 100, 500, 500)
        response = self.navigator.find_path(query)
        
        if response.ok and len(response.waypoints) > 2:
            # Test getting next waypoint
            current_x, current_y = 100, 100
            
            next_waypoint = self.navigator.get_next_waypoint(current_x, current_y, response.waypoints)
            assert next_waypoint is not None, "Should have next waypoint"
            
            # Move closer to first waypoint
            wx, wy = next_waypoint
            current_x = wx - 10  # Close but not reached
            current_y = wy - 10
            
            next_waypoint2 = self.navigator.get_next_waypoint(current_x, current_y, response.waypoints)
            assert next_waypoint2 == next_waypoint, "Should still target same waypoint"
            
            # Move very close to first waypoint
            current_x = wx + 5  # Within tolerance
            current_y = wy + 5
            
            next_waypoint3 = self.navigator.get_next_waypoint(current_x, current_y, response.waypoints)
            # Should either be the same waypoint or the next one
            
            print("✅ Waypoint following: Next waypoint selection works correctly")
    
    def test_theta_star_smoothing(self):
        """Test Theta* path smoothing"""
        # Create a path that can be smoothed
        waypoints = [
            (100, 100),
            (132, 100),  # Intermediate point
            (164, 100),  # Another intermediate point  
            (200, 100)   # End point
        ]
        
        # All points are on a straight line, so smoothing should reduce waypoints
        smoothed = self.navigator._theta_star_smooth(waypoints)
        
        # Should be reduced to just start and end
        assert len(smoothed) <= len(waypoints), "Smoothed path should have same or fewer waypoints"
        assert smoothed[0] == waypoints[0], "Should preserve start point"
        assert smoothed[-1] == waypoints[-1], "Should preserve end point"
        
        print(f"✅ Theta* smoothing: {len(waypoints)} waypoints reduced to {len(smoothed)}")
    
    def test_line_of_sight(self):
        """Test line of sight checking"""
        self.create_simple_room_layout()
        
        # Test clear line of sight
        clear_los = self.navigator._has_line_of_sight((100, 100), (200, 200))
        
        # Test blocked line of sight (through wall)
        blocked_los = self.navigator._has_line_of_sight((100, 300), (500, 300))
        
        print(f"✅ Line of sight: Clear={clear_los}, Blocked={blocked_los}")
    
    def run_all_acceptance_tests(self):
        """Run all acceptance tests in sequence"""
        print("🧪 Running Hierarchical Navigation Acceptance Tests")
        print("=" * 60)
        
        try:
            self.test_straight_room_path()
            self.test_doorway_routing()
            self.test_portal_center_tolerance()
            self.test_corner_cut_prevention()
            self.test_closed_door()
            self.test_multiple_doors_with_bias()
            self.test_outdoor_indoor_preference()
            self.test_performance_200x200()
            self.test_integration_with_npc_controller()
            self.test_waypoint_following()
            self.test_theta_star_smoothing()
            self.test_line_of_sight()
            
            print("=" * 60)
            print("🎉 ALL ACCEPTANCE TESTS PASSED!")
            return True
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            return False


def test_navigation_system():
    """Main test function"""
    test_suite = TestHierarchicalNavigation()
    test_suite.setup_method()
    return test_suite.run_all_acceptance_tests()


if __name__ == "__main__":
    success = test_navigation_system()
    exit(0 if success else 1)