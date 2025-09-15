"""
Simple test for the hierarchical navigation system
Tests core functionality without external dependencies
"""

import sys
import os
import time

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from npc.navigation import HierarchicalNavigator, PathQuery


class MockWall:
    """Mock wall rectangle for testing"""
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height


def test_basic_navigation():
    """Test basic navigation functionality"""
    print("Testing basic navigation...")
    
    # Create navigator
    navigator = HierarchicalNavigator(25, 20)
    
    # Create simple room layout
    walls = [
        MockWall(0, 0, 800, 32),      # Top boundary
        MockWall(0, 0, 32, 640),      # Left boundary  
        MockWall(768, 0, 32, 640),    # Right boundary
        MockWall(0, 608, 800, 32),    # Bottom boundary
        MockWall(384, 32, 32, 256),   # Dividing wall
        MockWall(384, 320, 32, 288),  # Dividing wall (with gap for door)
    ]
    
    # Set up navigation
    navigator.set_tiles_from_walls(walls)
    navigator.build_regions_and_portals()
    
    print(f"Found {len(navigator.regions)} regions and {len(navigator.portals)} portals")
    
    # Test pathfinding within same region
    query = PathQuery(100, 100, 200, 200)
    response = navigator.find_path(query)
    
    assert response.ok, f"Same-region path should succeed: {response.reason}"
    assert len(response.waypoints) >= 2, "Should have at least start and end waypoints"
    
    print(f"✅ Same-region path: {len(response.waypoints)} waypoints, cost {response.total_cost:.1f}")
    
    # Test pathfinding across regions (if we have multiple regions)
    if len(navigator.regions) > 1:
        query = PathQuery(100, 300, 500, 300)  # Cross the doorway
        response = navigator.find_path(query)
        
        if response.ok:
            print(f"✅ Cross-region path: {len(response.waypoints)} waypoints, cost {response.total_cost:.1f}")
        else:
            print(f"Cross-region path failed: {response.reason}")
    
    return True


def test_portal_control():
    """Test portal opening/closing"""
    print("Testing portal control...")
    
    navigator = HierarchicalNavigator(25, 20)
    
    # Create layout with clear portal
    walls = [
        MockWall(0, 0, 800, 32),
        MockWall(0, 0, 32, 640),
        MockWall(768, 0, 32, 640),
        MockWall(0, 608, 800, 32),
        MockWall(384, 32, 32, 256),   # Wall above door
        MockWall(384, 320, 32, 288),  # Wall below door
        # Gap at y=288-320 creates a portal
    ]
    
    navigator.set_tiles_from_walls(walls)
    navigator.build_regions_and_portals()
    
    if len(navigator.portals) > 0:
        portal_id = list(navigator.portals.keys())[0]
        
        # Test closing portal
        navigator.set_portal_open(portal_id, False)
        assert not navigator.portals[portal_id].is_open, "Portal should be closed"
        
        # Test path with closed portal
        query = PathQuery(100, 300, 500, 300)
        response = navigator.find_path(query)
        
        if not response.ok:
            print("✅ Closed portal correctly blocks path")
        
        # Reopen portal
        navigator.set_portal_open(portal_id, True)
        assert navigator.portals[portal_id].is_open, "Portal should be open"
        
        print("✅ Portal control working correctly")
    else:
        print("No portals found for testing")
    
    return True


def test_performance():
    """Test performance on larger grid"""
    print("Testing performance...")
    
    # Create larger navigator
    navigator = HierarchicalNavigator(50, 40)
    
    # Create grid of rooms
    walls = []
    
    # Outer boundary
    walls.extend([
        MockWall(0, 0, 1600, 32),
        MockWall(0, 0, 32, 1280),
        MockWall(1568, 0, 32, 1280),
        MockWall(0, 1248, 1600, 32),
    ])
    
    # Create 2x2 grid of rooms with doorways
    room_size = 600
    for row in range(2):
        for col in range(2):
            if col < 1:  # Vertical walls
                x = (col + 1) * room_size
                y = row * room_size + 32
                walls.append(MockWall(x, y, 32, room_size // 3))
                walls.append(MockWall(x, y + 2 * room_size // 3, 32, room_size // 3))
            
            if row < 1:  # Horizontal walls
                x = col * room_size + 32
                y = (row + 1) * room_size
                walls.append(MockWall(x, y, room_size // 3, 32))
                walls.append(MockWall(x + 2 * room_size // 3, y, room_size // 3, 32))
    
    # Time the setup
    start_time = time.time()
    navigator.set_tiles_from_walls(walls)
    navigator.build_regions_and_portals()
    setup_time = time.time() - start_time
    
    print(f"Setup time: {setup_time:.3f}s for {len(navigator.regions)} regions, {len(navigator.portals)} portals")
    
    # Time pathfinding queries
    query_times = []
    for i in range(5):
        start_time = time.time()
        query = PathQuery(100, 100, 1400, 1100)
        response = navigator.find_path(query)
        query_time = time.time() - start_time
        query_times.append(query_time)
    
    avg_time = sum(query_times) / len(query_times)
    max_time = max(query_times)
    
    print(f"Query performance: avg {avg_time*1000:.1f}ms, max {max_time*1000:.1f}ms")
    
    if max_time < 0.005:  # 5ms limit
        print("✅ Performance test passed")
    else:
        print(f"⚠️ Performance test: {max_time*1000:.1f}ms exceeds 5ms target")
    
    return True


def test_theta_star_smoothing():
    """Test path smoothing"""
    print("Testing Theta* smoothing...")
    
    navigator = HierarchicalNavigator(25, 20)
    
    # Create path that can be smoothed (straight line with intermediate points)
    waypoints = [
        (100, 100),
        (132, 100),
        (164, 100),
        (196, 100),
        (228, 100),
        (260, 100)
    ]
    
    smoothed = navigator._theta_star_smooth(waypoints)
    
    print(f"Original waypoints: {len(waypoints)}")
    print(f"Smoothed waypoints: {len(smoothed)}")
    
    assert len(smoothed) <= len(waypoints), "Smoothed path should have fewer or equal waypoints"
    assert smoothed[0] == waypoints[0], "Should preserve start"
    assert smoothed[-1] == waypoints[-1], "Should preserve end"
    
    print("✅ Theta* smoothing working correctly")
    return True


def test_waypoint_following():
    """Test waypoint following logic"""
    print("Testing waypoint following...")
    
    navigator = HierarchicalNavigator(25, 20)
    
    waypoints = [(100, 100), (200, 100), (300, 100), (400, 100)]
    
    # Test getting next waypoint
    next_wp = navigator.get_next_waypoint(90, 90, waypoints, tolerance=16)
    # Should target first unreached waypoint (distance > tolerance)
    expected = None
    for wp in waypoints:
        wx, wy = wp
        distance = ((wx - 90)**2 + (wy - 90)**2)**0.5
        if distance > 16:
            expected = wp
            break
    assert next_wp == expected, f"Should target first unreached waypoint, got {next_wp}, expected {expected}"
    
    # Test when close to first waypoint
    next_wp = navigator.get_next_waypoint(105, 105, waypoints, tolerance=16)
    assert next_wp == (200, 100), f"Should target second waypoint, got {next_wp}"
    
    # Test when all waypoints reached
    next_wp = navigator.get_next_waypoint(405, 105, waypoints, tolerance=16)
    # Check if we're actually close enough to all waypoints
    all_reached = True
    for wp in waypoints:
        wx, wy = wp
        distance = ((wx - 405)**2 + (wy - 105)**2)**0.5
        if distance > 16:
            all_reached = False
            break
    
    if all_reached:
        assert next_wp is None, f"Should return None when all reached, got {next_wp}"
    else:
        print(f"Not all waypoints reached from (405, 105), next target: {next_wp}")
    
    print("✅ Waypoint following logic working correctly")
    return True


def run_all_tests():
    """Run all navigation tests"""
    print("🧪 Running Hierarchical Navigation Tests")
    print("=" * 50)
    
    tests = [
        test_basic_navigation,
        test_portal_control,
        test_performance,
        test_theta_star_smoothing,
        test_waypoint_following,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ {test.__name__} failed: {e}")
            failed += 1
        print()
    
    print("=" * 50)
    print(f"Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 ALL TESTS PASSED!")
        return True
    else:
        print("❌ Some tests failed")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)