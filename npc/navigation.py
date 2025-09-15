"""
Hierarchical Navigation System for 2D Top-Down Maps
Implements 2-layer navigation: Grid A* + Theta* smoothing + Portal Graph

Features:
- Low level: Tile-grid pathfinding using A* with Theta* smoothing
- High level: Portal graph connecting regions via doorway portals
- Output: Executable waypoints for NPCs
- Performance: <5ms queries on 200x200 grids with 10 rooms, 20 portals
"""

import math
import heapq
import time
from typing import List, Tuple, Dict, Set, Optional, NamedTuple
from dataclasses import dataclass
from enum import Enum


class PathResult(Enum):
    """Path finding result status"""
    SUCCESS = "SUCCESS"
    NO_PATH = "NO_PATH"
    INVALID_START = "INVALID_START"
    INVALID_GOAL = "INVALID_GOAL"


@dataclass
class PathQuery:
    """Path finding query parameters"""
    start_x: float
    start_y: float
    goal_x: float
    goal_y: float
    cost_bias: Dict[str, float] = None  # Portal ID -> cost multiplier
    prefer_indoor: bool = False
    
    def __post_init__(self):
        if self.cost_bias is None:
            self.cost_bias = {}


@dataclass
class PathResponse:
    """Path finding response"""
    ok: bool
    reason: str = ""
    waypoints: List[Tuple[float, float]] = None
    total_cost: float = 0.0
    
    def __post_init__(self):
        if self.waypoints is None:
            self.waypoints = []


class Portal:
    """Portal connecting two regions through a doorway"""
    
    def __init__(self, portal_id: str, region1: int, region2: int, 
                 center_x: float, center_y: float, span_tiles: List[Tuple[int, int]]):
        self.id = portal_id
        self.region1 = region1
        self.region2 = region2
        self.center_x = center_x
        self.center_y = center_y
        self.span_tiles = span_tiles  # List of (tile_x, tile_y) that form the portal
        self.is_open = True
        self.is_indoor = False  # Set to True for indoor portals


class Region:
    """Connected region of walkable tiles"""
    
    def __init__(self, region_id: int, tiles: Set[Tuple[int, int]]):
        self.id = region_id
        self.tiles = tiles
        self.portals: List[Portal] = []
        self.is_indoor = False  # Set to True for indoor regions


class HierarchicalNavigator:
    """Main navigation system implementing hierarchical pathfinding"""
    
    def __init__(self, grid_width: int, grid_height: int):
        self.grid_width = grid_width
        self.grid_height = grid_height
        self.tile_size = 32  # Pixels per tile
        
        # Grid representation: True = walkable, False = blocked
        self.walkable_grid: List[List[bool]] = []
        
        # Region and portal data
        self.regions: Dict[int, Region] = {}
        self.portals: Dict[str, Portal] = {}
        self.tile_to_region: Dict[Tuple[int, int], int] = {}
        
        # Portal graph for high-level pathfinding
        self.portal_graph: Dict[str, List[Tuple[str, float]]] = {}
        
        # Initialize empty grid
        self._initialize_grid()
    
    def _initialize_grid(self):
        """Initialize walkable grid with all tiles blocked"""
        self.walkable_grid = [[False for _ in range(self.grid_width)] 
                             for _ in range(self.grid_height)]
    
    def set_tile_walkable(self, tile_x: int, tile_y: int, walkable: bool):
        """Set walkability of a single tile"""
        if 0 <= tile_x < self.grid_width and 0 <= tile_y < self.grid_height:
            self.walkable_grid[tile_y][tile_x] = walkable
    
    def set_tiles_from_walls(self, walls: List, tile_size: int = 32):
        """Set walkable tiles based on wall rectangles (pygame.Rect objects)"""
        # First, mark all tiles as walkable
        for y in range(self.grid_height):
            for x in range(self.grid_width):
                self.walkable_grid[y][x] = True
        
        # Then mark tiles that intersect with walls as blocked
        for wall in walls:
            # Convert wall rectangle to tile coordinates
            start_x = max(0, wall.x // tile_size)
            end_x = min(self.grid_width, (wall.x + wall.width + tile_size - 1) // tile_size)
            start_y = max(0, wall.y // tile_size)
            end_y = min(self.grid_height, (wall.y + wall.height + tile_size - 1) // tile_size)
            
            for y in range(start_y, end_y):
                for x in range(start_x, end_x):
                    self.walkable_grid[y][x] = False
    
    def build_regions_and_portals(self):
        """Build regions using flood fill and detect portals between them"""
        self.regions.clear()
        self.portals.clear()
        self.tile_to_region.clear()
        self.portal_graph.clear()
        
        # Flood fill to find connected regions
        visited = set()
        region_id = 0
        
        for y in range(self.grid_height):
            for x in range(self.grid_width):
                if (x, y) not in visited and self.walkable_grid[y][x]:
                    # Found new region
                    region_tiles = self._flood_fill(x, y, visited)
                    if region_tiles:
                        region = Region(region_id, region_tiles)
                        self.regions[region_id] = region
                        
                        # Map tiles to region
                        for tile in region_tiles:
                            self.tile_to_region[tile] = region_id
                        
                        region_id += 1
        
        # Detect portals between regions
        self._detect_portals()
        
        # Build portal graph
        self._build_portal_graph()
    
    def _flood_fill(self, start_x: int, start_y: int, visited: Set[Tuple[int, int]]) -> Set[Tuple[int, int]]:
        """Flood fill to find connected walkable tiles"""
        if (start_x, start_y) in visited or not self._is_walkable(start_x, start_y):
            return set()
        
        region_tiles = set()
        stack = [(start_x, start_y)]
        
        while stack:
            x, y = stack.pop()
            if (x, y) in visited or not self._is_walkable(x, y):
                continue
            
            visited.add((x, y))
            region_tiles.add((x, y))
            
            # Add 4-connected neighbors
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = x + dx, y + dy
                if (0 <= nx < self.grid_width and 0 <= ny < self.grid_height and 
                    (nx, ny) not in visited):
                    stack.append((nx, ny))
        
        return region_tiles
    
    def _detect_portals(self):
        """Detect portals (doorways) between regions"""
        portal_id = 0
        
        # Simple approach: find walkable tiles that are adjacent to different regions
        for y in range(self.grid_height):
            for x in range(self.grid_width):
                if not self._is_walkable(x, y):
                    continue
                
                current_region = self.tile_to_region.get((x, y))
                if current_region is None:
                    continue
                
                # Check all 4 neighbors for different regions
                neighbors = [(x+1, y), (x-1, y), (x, y+1), (x, y-1)]
                adjacent_regions = set()
                
                for nx, ny in neighbors:
                    if (0 <= nx < self.grid_width and 0 <= ny < self.grid_height and 
                        self._is_walkable(nx, ny)):
                        neighbor_region = self.tile_to_region.get((nx, ny))
                        if neighbor_region is not None and neighbor_region != current_region:
                            adjacent_regions.add(neighbor_region)
                
                # If this tile connects to different regions, it's a portal candidate
                if len(adjacent_regions) > 0:
                    for other_region in adjacent_regions:
                        # Create portal between current_region and other_region
                        portal_key = f"{min(current_region, other_region)}_{max(current_region, other_region)}"
                        
                        # Check if we already have this portal
                        existing_portal = None
                        for portal in self.portals.values():
                            if ((portal.region1 == current_region and portal.region2 == other_region) or
                                (portal.region1 == other_region and portal.region2 == current_region)):
                                existing_portal = portal
                                break
                        
                        if not existing_portal:
                            # Create new portal
                            world_x = x * self.tile_size + self.tile_size / 2
                            world_y = y * self.tile_size + self.tile_size / 2
                            
                            portal = Portal(f"portal_{portal_id}", current_region, other_region, 
                                          world_x, world_y, [(x, y)])
                            self.portals[portal.id] = portal
                            
                            # Add to regions
                            if current_region in self.regions:
                                self.regions[current_region].portals.append(portal)
                            if other_region in self.regions:
                                self.regions[other_region].portals.append(portal)
                            
                            portal_id += 1
    
    def _create_portal_from_span(self, portal_id: str, span: List[Tuple[int, int]], regions: Set[int]):
        """Create a portal from a span of tiles connecting regions"""
        if len(regions) < 2:
            return
        
        # Remove None regions
        regions = {r for r in regions if r is not None}
        if len(regions) < 2:
            return
        
        # Take first two regions
        region_list = list(regions)
        region1, region2 = region_list[0], region_list[1]
        
        # Calculate center of span
        center_x = sum(x for x, y in span) / len(span)
        center_y = sum(y for x, y in span) / len(span)
        
        # Convert to world coordinates
        world_x = center_x * self.tile_size + self.tile_size / 2
        world_y = center_y * self.tile_size + self.tile_size / 2
        
        # Create portal
        portal = Portal(portal_id, region1, region2, world_x, world_y, span)
        self.portals[portal_id] = portal
        
        # Add to regions
        if region1 in self.regions:
            self.regions[region1].portals.append(portal)
        if region2 in self.regions:
            self.regions[region2].portals.append(portal)
    
    def _build_portal_graph(self):
        """Build graph connecting portals within the same region"""
        self.portal_graph.clear()
        
        # For each region, connect all portals within it
        for region in self.regions.values():
            region_portals = region.portals
            
            for i, portal1 in enumerate(region_portals):
                if portal1.id not in self.portal_graph:
                    self.portal_graph[portal1.id] = []
                
                for j, portal2 in enumerate(region_portals):
                    if i != j:
                        # Calculate Euclidean distance
                        dx = portal2.center_x - portal1.center_x
                        dy = portal2.center_y - portal1.center_y
                        distance = math.sqrt(dx * dx + dy * dy)
                        
                        self.portal_graph[portal1.id].append((portal2.id, distance))
    
    def find_path(self, query: PathQuery) -> PathResponse:
        """Find hierarchical path from start to goal"""
        start_time = time.time()
        
        # Convert world coordinates to tile coordinates
        start_tile_x = int(query.start_x // self.tile_size)
        start_tile_y = int(query.start_y // self.tile_size)
        goal_tile_x = int(query.goal_x // self.tile_size)
        goal_tile_y = int(query.goal_y // self.tile_size)
        
        # Validate start and goal
        if not self._is_walkable(start_tile_x, start_tile_y):
            return PathResponse(False, "INVALID_START")
        
        if not self._is_walkable(goal_tile_x, goal_tile_y):
            return PathResponse(False, "INVALID_GOAL")
        
        # Get regions for start and goal
        start_region = self.tile_to_region.get((start_tile_x, start_tile_y))
        goal_region = self.tile_to_region.get((goal_tile_x, goal_tile_y))
        
        if start_region is None or goal_region is None:
            return PathResponse(False, "NO_PATH")
        
        # Same region - use direct A* pathfinding
        if start_region == goal_region:
            waypoints = self._find_direct_path(start_tile_x, start_tile_y, goal_tile_x, goal_tile_y)
            if waypoints:
                # Convert to world coordinates and apply Theta* smoothing
                world_waypoints = [(x * self.tile_size + self.tile_size / 2, 
                                  y * self.tile_size + self.tile_size / 2) for x, y in waypoints]
                smoothed_waypoints = self._theta_star_smooth(world_waypoints)
                
                total_cost = self._calculate_path_cost(smoothed_waypoints)
                return PathResponse(True, "SUCCESS", smoothed_waypoints, total_cost)
            else:
                return PathResponse(False, "NO_PATH")
        
        # Different regions - use hierarchical pathfinding
        return self._find_hierarchical_path(query, start_region, goal_region, 
                                          start_tile_x, start_tile_y, goal_tile_x, goal_tile_y)
    
    def _find_direct_path(self, start_x: int, start_y: int, goal_x: int, goal_y: int) -> List[Tuple[int, int]]:
        """Find direct A* path within a single region"""
        if start_x == goal_x and start_y == goal_y:
            return [(start_x, start_y)]
        
        # A* pathfinding with 8-way movement and corner-cutting prevention
        open_set = [(0, start_x, start_y)]
        came_from = {}
        g_score = {(start_x, start_y): 0}
        f_score = {(start_x, start_y): self._heuristic(start_x, start_y, goal_x, goal_y)}
        
        while open_set:
            current_f, current_x, current_y = heapq.heappop(open_set)
            
            if current_x == goal_x and current_y == goal_y:
                # Reconstruct path
                path = []
                x, y = current_x, current_y
                while (x, y) in came_from:
                    path.append((x, y))
                    x, y = came_from[(x, y)]
                path.append((start_x, start_y))
                return list(reversed(path))
            
            # Check all 8 neighbors
            for dx, dy in [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]:
                neighbor_x = current_x + dx
                neighbor_y = current_y + dy
                
                # Check bounds
                if not (0 <= neighbor_x < self.grid_width and 0 <= neighbor_y < self.grid_height):
                    continue
                
                # Check walkability
                if not self._is_walkable(neighbor_x, neighbor_y):
                    continue
                
                # Check corner cutting for diagonal moves
                if dx != 0 and dy != 0:
                    if (not self._is_walkable(current_x + dx, current_y) or 
                        not self._is_walkable(current_x, current_y + dy)):
                        continue  # Prevent corner cutting
                
                # Calculate movement cost
                move_cost = math.sqrt(dx * dx + dy * dy)
                tentative_g = g_score[(current_x, current_y)] + move_cost
                
                if (neighbor_x, neighbor_y) not in g_score or tentative_g < g_score[(neighbor_x, neighbor_y)]:
                    came_from[(neighbor_x, neighbor_y)] = (current_x, current_y)
                    g_score[(neighbor_x, neighbor_y)] = tentative_g
                    f_score[(neighbor_x, neighbor_y)] = tentative_g + self._heuristic(neighbor_x, neighbor_y, goal_x, goal_y)
                    heapq.heappush(open_set, (f_score[(neighbor_x, neighbor_y)], neighbor_x, neighbor_y))
        
        return []  # No path found
    
    def _find_hierarchical_path(self, query: PathQuery, start_region: int, goal_region: int,
                              start_tile_x: int, start_tile_y: int, goal_tile_x: int, goal_tile_y: int) -> PathResponse:
        """Find path using portal graph for inter-region navigation"""
        
        # Find portals in start and goal regions
        start_portals = [p for p in self.regions[start_region].portals if p.is_open]
        goal_portals = [p for p in self.regions[goal_region].portals if p.is_open]
        
        if not start_portals or not goal_portals:
            return PathResponse(False, "NO_PATH")
        
        # Find best portal-to-portal path
        best_path = None
        best_cost = float('inf')
        
        for start_portal in start_portals:
            for goal_portal in goal_portals:
                # Find portal graph path
                portal_path = self._find_portal_path(start_portal.id, goal_portal.id, query.cost_bias, query.prefer_indoor)
                
                if portal_path:
                    # Calculate full path cost
                    total_cost = 0
                    
                    # Cost from start to first portal
                    start_to_portal_cost = self._estimate_cost(query.start_x, query.start_y, 
                                                             start_portal.center_x, start_portal.center_y)
                    total_cost += start_to_portal_cost
                    
                    # Cost through portal graph
                    for i in range(len(portal_path) - 1):
                        p1 = self.portals[portal_path[i]]
                        p2 = self.portals[portal_path[i + 1]]
                        cost = self._estimate_cost(p1.center_x, p1.center_y, p2.center_x, p2.center_y)
                        
                        # Apply cost bias
                        if p2.id in query.cost_bias:
                            cost *= query.cost_bias[p2.id]
                        
                        # Apply indoor preference
                        if query.prefer_indoor and p2.is_indoor:
                            cost *= 0.9  # 10% discount for indoor portals
                        
                        total_cost += cost
                    
                    # Cost from last portal to goal
                    portal_to_goal_cost = self._estimate_cost(goal_portal.center_x, goal_portal.center_y,
                                                            query.goal_x, query.goal_y)
                    total_cost += portal_to_goal_cost
                    
                    if total_cost < best_cost:
                        best_cost = total_cost
                        best_path = (start_portal, goal_portal, portal_path)
        
        if not best_path:
            return PathResponse(False, "NO_PATH")
        
        # Build full waypoint path
        start_portal, goal_portal, portal_path = best_path
        waypoints = []
        
        # Path from start to first portal
        start_portal_tile_x = int(start_portal.center_x // self.tile_size)
        start_portal_tile_y = int(start_portal.center_y // self.tile_size)
        start_segment = self._find_direct_path(start_tile_x, start_tile_y, start_portal_tile_x, start_portal_tile_y)
        
        if start_segment:
            waypoints.extend([(x * self.tile_size + self.tile_size / 2, 
                             y * self.tile_size + self.tile_size / 2) for x, y in start_segment[:-1]])
        
        # Add portal centers
        for portal_id in portal_path:
            portal = self.portals[portal_id]
            waypoints.append((portal.center_x, portal.center_y))
        
        # Path from last portal to goal
        goal_portal_tile_x = int(goal_portal.center_x // self.tile_size)
        goal_portal_tile_y = int(goal_portal.center_y // self.tile_size)
        goal_segment = self._find_direct_path(goal_portal_tile_x, goal_portal_tile_y, goal_tile_x, goal_tile_y)
        
        if goal_segment:
            waypoints.extend([(x * self.tile_size + self.tile_size / 2, 
                             y * self.tile_size + self.tile_size / 2) for x, y in goal_segment[1:]])
        
        # Add final goal
        waypoints.append((query.goal_x, query.goal_y))
        
        # Apply Theta* smoothing
        smoothed_waypoints = self._theta_star_smooth(waypoints)
        
        return PathResponse(True, "SUCCESS", smoothed_waypoints, best_cost)
    
    def _find_portal_path(self, start_portal_id: str, goal_portal_id: str, 
                         cost_bias: Dict[str, float], prefer_indoor: bool) -> List[str]:
        """Find path through portal graph using Dijkstra's algorithm"""
        if start_portal_id == goal_portal_id:
            return [start_portal_id]
        
        # Dijkstra's algorithm
        distances = {start_portal_id: 0}
        previous = {}
        unvisited = set(self.portal_graph.keys())
        
        while unvisited:
            # Find unvisited node with minimum distance
            current = min(unvisited, key=lambda x: distances.get(x, float('inf')))
            
            if distances.get(current, float('inf')) == float('inf'):
                break  # No path possible
            
            if current == goal_portal_id:
                # Reconstruct path
                path = []
                while current in previous:
                    path.append(current)
                    current = previous[current]
                path.append(start_portal_id)
                return list(reversed(path))
            
            unvisited.remove(current)
            
            # Check neighbors
            for neighbor, base_cost in self.portal_graph.get(current, []):
                if neighbor in unvisited:
                    # Apply cost bias
                    cost = base_cost
                    if neighbor in cost_bias:
                        cost *= cost_bias[neighbor]
                    
                    # Apply indoor preference
                    if prefer_indoor and self.portals[neighbor].is_indoor:
                        cost *= 0.9
                    
                    alt_distance = distances[current] + cost
                    if alt_distance < distances.get(neighbor, float('inf')):
                        distances[neighbor] = alt_distance
                        previous[neighbor] = current
        
        return []  # No path found
    
    def _theta_star_smooth(self, waypoints: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """Apply Theta* smoothing to remove unnecessary waypoints"""
        if len(waypoints) <= 2:
            return waypoints
        
        smoothed = [waypoints[0]]
        i = 0
        
        while i < len(waypoints) - 1:
            j = i + 1
            last_reachable = i
            
            # Find the farthest waypoint we can reach directly
            while j < len(waypoints):
                if self._has_line_of_sight(waypoints[i], waypoints[j]):
                    last_reachable = j
                    j += 1
                else:
                    break
            
            # Move to the last reachable waypoint
            if last_reachable > i:
                i = last_reachable
                if i < len(waypoints) - 1:  # Don't add the final waypoint yet
                    smoothed.append(waypoints[i])
            else:
                # Can't reach any further, move to next waypoint
                i += 1
                if i < len(waypoints):
                    smoothed.append(waypoints[i])
        
        # Ensure goal is included
        if len(smoothed) == 0 or smoothed[-1] != waypoints[-1]:
            smoothed.append(waypoints[-1])
        
        return smoothed
    
    def _has_line_of_sight(self, start: Tuple[float, float], end: Tuple[float, float]) -> bool:
        """Check if there's a clear line of sight between two points"""
        x1, y1 = start
        x2, y2 = end
        
        # Convert to tile coordinates
        tile_x1 = int(x1 // self.tile_size)
        tile_y1 = int(y1 // self.tile_size)
        tile_x2 = int(x2 // self.tile_size)
        tile_y2 = int(y2 // self.tile_size)
        
        # Same tile - always has line of sight
        if tile_x1 == tile_x2 and tile_y1 == tile_y2:
            return True
        
        # Use Bresenham's line algorithm to check all tiles along the line
        dx = abs(tile_x2 - tile_x1)
        dy = abs(tile_y2 - tile_y1)
        x, y = tile_x1, tile_y1
        x_inc = 1 if tile_x1 < tile_x2 else -1
        y_inc = 1 if tile_y1 < tile_y2 else -1
        error = dx - dy
        
        steps = 0
        max_steps = dx + dy + 10  # Safety limit
        
        while steps < max_steps:
            if not self._is_walkable(x, y):
                return False
            
            if x == tile_x2 and y == tile_y2:
                break
            
            if error * 2 > -dy:
                error -= dy
                x += x_inc
            
            if error * 2 < dx:
                error += dx
                y += y_inc
            
            steps += 1
        
        return True
    
    def _is_walkable(self, tile_x: int, tile_y: int) -> bool:
        """Check if a tile is walkable"""
        if not (0 <= tile_x < self.grid_width and 0 <= tile_y < self.grid_height):
            return False
        return self.walkable_grid[tile_y][tile_x]
    
    def _heuristic(self, x1: int, y1: int, x2: int, y2: int) -> float:
        """Heuristic function for A* (Euclidean distance)"""
        return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
    
    def _estimate_cost(self, x1: float, y1: float, x2: float, y2: float) -> float:
        """Estimate cost between two world coordinates"""
        return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
    
    def _calculate_path_cost(self, waypoints: List[Tuple[float, float]]) -> float:
        """Calculate total cost of a waypoint path"""
        if len(waypoints) <= 1:
            return 0.0
        
        total_cost = 0.0
        for i in range(len(waypoints) - 1):
            x1, y1 = waypoints[i]
            x2, y2 = waypoints[i + 1]
            total_cost += math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        
        return total_cost
    
    def set_portal_open(self, portal_id: str, is_open: bool):
        """Open or close a portal (door)"""
        if portal_id in self.portals:
            self.portals[portal_id].is_open = is_open
    
    def set_region_indoor(self, region_id: int, is_indoor: bool):
        """Mark a region as indoor or outdoor"""
        if region_id in self.regions:
            self.regions[region_id].is_indoor = is_indoor
            # Also mark portals in this region as indoor
            for portal in self.regions[region_id].portals:
                portal.is_indoor = is_indoor
    
    def get_next_waypoint(self, current_x: float, current_y: float, 
                         waypoints: List[Tuple[float, float]], tolerance: float = 16.0) -> Optional[Tuple[float, float]]:
        """Get the next waypoint to move towards"""
        if not waypoints:
            return None
        
        # Find the first waypoint that's not reached yet
        for waypoint in waypoints:
            wx, wy = waypoint
            distance = math.sqrt((wx - current_x) ** 2 + (wy - current_y) ** 2)
            if distance > tolerance:
                return waypoint
        
        return None  # All waypoints reached
    
    def debug_print_grid(self, highlight_regions: bool = False):
        """Print ASCII representation of the grid for debugging"""
        print(f"Grid ({self.grid_width}x{self.grid_height}):")
        
        for y in range(self.grid_height):
            row = ""
            for x in range(self.grid_width):
                if self.walkable_grid[y][x]:
                    if highlight_regions and (x, y) in self.tile_to_region:
                        region_id = self.tile_to_region[(x, y)]
                        row += str(region_id % 10)
                    else:
                        row += "."
                else:
                    row += "#"
            print(f"{y:2d}: {row}")
        
        print(f"\nRegions: {len(self.regions)}")
        for region_id, region in self.regions.items():
            print(f"  Region {region_id}: {len(region.tiles)} tiles, {len(region.portals)} portals")
        
        print(f"\nPortals: {len(self.portals)}")
        for portal_id, portal in self.portals.items():
            print(f"  {portal_id}: regions {portal.region1}<->{portal.region2} at ({portal.center_x:.1f}, {portal.center_y:.1f})")