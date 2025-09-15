# Hierarchical Navigation System

## Overview

The Hierarchical Navigation System implements a 2-layer pathfinding solution for 2D top-down maps, providing intelligent NPC movement that can navigate complex environments with multiple rooms and doorways.

## Architecture

### Two-Layer System

1. **Low Level**: Tile-grid pathfinding using A* with Theta* smoothing
2. **High Level**: Portal graph connecting regions via doorway portals

### Key Components

- **HierarchicalNavigator**: Main navigation system
- **Region**: Connected areas of walkable tiles
- **Portal**: Doorways connecting regions
- **PathQuery/PathResponse**: API for pathfinding requests

## Features

### ✅ Implemented Features

- **A* Pathfinding**: Optimal path finding within regions
- **Theta* Smoothing**: Removes unnecessary waypoints for natural movement
- **Portal Detection**: Automatically finds doorways between regions
- **Region Analysis**: Flood-fill algorithm to identify connected areas
- **Cost Biasing**: Prefer certain portals with cost multipliers
- **Indoor/Outdoor Preference**: Slight preference for indoor routes
- **Dynamic Portal Control**: Open/close doors at runtime
- **Performance Optimized**: <5ms queries on large maps
- **Corner-Cut Prevention**: Prevents diagonal movement through blocked corners
- **Line-of-Sight**: Efficient visibility checking for path smoothing

### 🎯 Integration Points

- **NPC Controller**: Seamless integration with existing LLM-driven NPCs
- **Observation System**: Navigation info included in LLM observations
- **Move-To Actions**: Enhanced with hierarchical pathfinding
- **Real-time Replanning**: Automatic path recalculation when blocked

## API Reference

### Core Classes

#### HierarchicalNavigator

```python
navigator = HierarchicalNavigator(grid_width, grid_height)

# Setup
navigator.set_tiles_from_walls(walls)  # Configure walkable tiles
navigator.build_regions_and_portals()  # Analyze map structure

# Pathfinding
query = PathQuery(start_x, start_y, goal_x, goal_y)
response = navigator.find_path(query)

# Dynamic control
navigator.set_portal_open(portal_id, is_open)
navigator.set_region_indoor(region_id, is_indoor)
```

#### PathQuery

```python
query = PathQuery(
    start_x=100, start_y=100,
    goal_x=500, goal_y=500,
    cost_bias={"portal_1": 0.5},  # Make portal_1 cheaper
    prefer_indoor=True            # Prefer indoor routes
)
```

#### PathResponse

```python
response = navigator.find_path(query)

if response.ok:
    waypoints = response.waypoints      # List of (x, y) coordinates
    total_cost = response.total_cost    # Total path cost
else:
    reason = response.reason            # "NO_PATH", "INVALID_START", etc.
```

### NPC Controller Integration

```python
# Initialize navigation in NPC controller
controller.initialize_navigation(grid_width, grid_height, walls)

# Navigation happens automatically when NPC uses move_to actions
# LLM can see navigation progress in observations
```

## Acceptance Tests

All acceptance tests pass:

### ✅ Straight Room Path
- **Test**: Path within same region
- **Result**: Direct A* path with Theta* smoothing

### ✅ Doorway Routing  
- **Test**: Path between different regions
- **Result**: Routes through portal centers

### ✅ Portal Center Tolerance
- **Test**: Force path through portal center ±0.5 tiles
- **Result**: All portal waypoints within tolerance

### ✅ Corner-Cut Prevention
- **Test**: Diagonal movement through blocked corners
- **Result**: No illegal diagonal movement allowed

### ✅ Closed Door
- **Test**: Path when only portal is closed
- **Result**: Returns NO_PATH correctly

### ✅ Multiple Doors with Bias
- **Test**: Two portals with cost bias toward farther door
- **Result**: Cost bias affects portal selection

### ✅ Outdoor↔Indoor Preference
- **Test**: Slight preference for indoor routes
- **Result**: Indoor preference affects pathfinding

### ✅ Performance 200×200
- **Test**: Large grid with 10 rooms, 20 portals
- **Result**: All queries complete in <5ms

## Usage Examples

### Basic Setup

```python
from npc.navigation import HierarchicalNavigator, PathQuery

# Create navigator for 25x20 tile grid
navigator = HierarchicalNavigator(25, 20)

# Configure from pygame walls
navigator.set_tiles_from_walls(wall_rectangles)
navigator.build_regions_and_portals()

# Find path
query = PathQuery(100, 100, 500, 300)
response = navigator.find_path(query)

if response.ok:
    for waypoint in response.waypoints:
        print(f"Move to {waypoint}")
```

### Advanced Features

```python
# Cost biasing - make door_2 50% cheaper
cost_bias = {"door_2": 0.5}
query = PathQuery(start_x, start_y, goal_x, goal_y, cost_bias=cost_bias)

# Indoor preference
query = PathQuery(start_x, start_y, goal_x, goal_y, prefer_indoor=True)

# Dynamic door control
navigator.set_portal_open("door_1", False)  # Close door
navigator.set_portal_open("door_1", True)   # Open door

# Mark regions as indoor
navigator.set_region_indoor(region_id, True)
```

### NPC Integration

```python
# In your game initialization
npc.llm_controller.initialize_navigation(grid_width, grid_height, walls)

# NPCs automatically use hierarchical navigation for move_to actions
# No additional code needed - works with existing LLM system
```

## Performance Characteristics

- **Region Building**: O(n) where n = number of tiles
- **Portal Detection**: O(n) scan for doorways  
- **Path Queries**: O(p log p) where p = number of portals
- **Memory Usage**: O(n + p) for grid and portal graph
- **Real-world Performance**: <5ms on 200×200 grids

## Integration with LLM NPCs

The navigation system seamlessly integrates with the existing LLM-driven NPC system:

### Automatic Integration
- NPCs use `move_to` actions as before
- Navigation system handles complex pathfinding automatically
- No changes needed to LLM prompts or action schemas

### Enhanced Observations
```json
{
  "navigation": {
    "waypoints": [[12, 8], [15, 10], [18, 12]],
    "target": [20, 15]
  }
}
```

### Intelligent Replanning
- Automatic path recalculation when movement is blocked
- Dynamic response to door state changes
- Efficient waypoint following with tolerance

## File Structure

```
npc/
├── navigation.py           # Core navigation system
├── controller.py          # Integration with NPC controller
└── observation.py         # Navigation info in observations

tests/
└── test_hierarchical_navigation.py  # Comprehensive test suite

docs/
└── HIERARCHICAL_NAVIGATION.md      # This documentation
```

## Future Enhancements

### Potential Improvements
- **Dynamic Obstacles**: Real-time obstacle avoidance
- **Multi-Agent Coordination**: Prevent NPC collisions
- **Hierarchical Regions**: Nested region structures
- **Pathfinding Caching**: Cache common paths
- **Visual Debug Tools**: In-game path visualization

### Extension Points
- **Custom Cost Functions**: Domain-specific path costs
- **Portal Behaviors**: Special portal types (teleporters, etc.)
- **Region Properties**: Different movement speeds per region
- **Path Constraints**: Avoid certain areas or routes

## Troubleshooting

### Common Issues

**No Path Found**
- Check that start and goal are in walkable areas
- Verify portals are open between regions
- Ensure regions are properly connected

**Poor Performance**
- Reduce grid size if possible
- Limit number of portals
- Use cost biasing to guide pathfinding

**Incorrect Paths**
- Verify wall configuration matches game layout
- Check portal detection with debug output
- Ensure tile size matches game coordinates

### Debug Tools

```python
# Print grid layout
navigator.debug_print_grid(highlight_regions=True)

# Check regions and portals
print(f"Regions: {len(navigator.regions)}")
print(f"Portals: {len(navigator.portals)}")

# Test specific paths
query = PathQuery(start_x, start_y, goal_x, goal_y)
response = navigator.find_path(query)
print(f"Path result: {response.ok}, reason: {response.reason}")
```

## Conclusion

The Hierarchical Navigation System provides robust, efficient pathfinding for complex 2D environments while maintaining seamless integration with the existing LLM-driven NPC system. All acceptance criteria are met with excellent performance characteristics.