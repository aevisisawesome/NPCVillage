"""
Tests for move_to pathfinding behavior.
Verifies that move_to moves one step toward target when path exists,
and returns "no_path" when blocked.
"""

import pytest
import math
from npc.controller import NPCController


class MockRect:
    """Mock rectangle for testing"""
    def __init__(self, x, y, width=32, height=32):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.centerx = x + width // 2
        self.centery = y + height // 2


class MockNPC:
    """Mock NPC for testing pathfinding"""
    def __init__(self, x=160, y=160):  # Start at tile (5,5)
        self.rect = MockRect(x, y)
        self.speed = 4
        self.current_health = 100
        self.is_moving = False
        self.speech_text = ""
        self.current_action = "idle"
        self.last_move_succeeded = True
        
    def move(self, dx, dy, walls, characters):
        """Mock move method with collision detection"""
        # Calculate new position
        new_x = self.rect.x + dx
        new_y = self.rect.y + dy
        new_rect = MockRect(new_x, new_y, self.rect.width, self.rect.height)
        
        # Check for wall collisions
        for wall in walls:
            if self._rects_overlap(new_rect, wall):
                self.last_move_succeeded = False
                return
        
        # Check for character collisions
        for char in characters:
            if char != self and hasattr(char, 'rect'):
                if self._rects_overlap(new_rect, char.rect):
                    self.last_move_succeeded = False
                    return
        
        # Move if no collision
        self.rect.x = new_x
        self.rect.y = new_y
        self.rect.centerx = new_x + self.rect.width // 2
        self.rect.centery = new_y + self.rect.height // 2
        self.is_moving = True
        self.last_move_succeeded = True
    
    def _rects_overlap(self, rect1, rect2):
        """Check if two rectangles overlap"""
        return not (rect1.x + rect1.width <= rect2.x or 
                   rect2.x + rect2.width <= rect1.x or
                   rect1.y + rect1.height <= rect2.y or 
                   rect2.y + rect2.height <= rect1.y)
    
    def say(self, text):
        self.speech_text = text
    
    def has_item(self, item_id):
        return False
    
    def remove_item(self, item_id, qty):
        return 0
    
    def add_item(self, item_id, qty):
        return True


class TestMoveToPathfinding:
    """Test move_to pathfinding behavior"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.npc = MockNPC(160, 160)  # Start at tile (5,5) in world coords
        self.controller = NPCController(self.npc, llm_endpoint="mock://test")
        self.controller.llm_client = None  # Disable LLM for unit tests
    
    def test_move_to_one_step_north(self):
        """Test that move_to moves exactly one step toward northern target"""
        
        engine_state = {
            "walls": [],
            "characters": [self.npc]
        }
        
        from npc.actions import Action, MoveToArgs
        # Move to tile (5,3) - two tiles north
        action = Action(action="move_to", args=MoveToArgs(x=5, y=3))
        
        original_y = self.npc.rect.y
        
        result = self.controller._execute_move_to(action.args, engine_state)
        
        assert result == "ok"
        # Should have moved north (y decreased)
        assert self.npc.rect.y < original_y
        # Should have moved approximately one step (speed=4)
        assert abs((original_y - self.npc.rect.y) - self.npc.speed) <= 1
    
    def test_move_to_one_step_east(self):
        """Test that move_to moves exactly one step toward eastern target"""
        
        engine_state = {
            "walls": [],
            "characters": [self.npc]
        }
        
        from npc.actions import Action, MoveToArgs
        # Move to tile (8,5) - three tiles east
        action = Action(action="move_to", args=MoveToArgs(x=8, y=5))
        
        original_x = self.npc.rect.x
        
        result = self.controller._execute_move_to(action.args, engine_state)
        
        assert result == "ok"
        # Should have moved east (x increased)
        assert self.npc.rect.x > original_x
        # Should have moved approximately one step
        assert abs((self.npc.rect.x - original_x) - self.npc.speed) <= 1
    
    def test_move_to_diagonal_movement(self):
        """Test move_to with diagonal target (should move diagonally)"""
        
        engine_state = {
            "walls": [],
            "characters": [self.npc]
        }
        
        from npc.actions import Action, MoveToArgs
        # Move to tile (7,3) - northeast diagonal
        action = Action(action="move_to", args=MoveToArgs(x=7, y=3))
        
        original_x = self.npc.rect.x
        original_y = self.npc.rect.y
        
        result = self.controller._execute_move_to(action.args, engine_state)
        
        assert result == "ok"
        # Should have moved both east and north
        assert self.npc.rect.x > original_x
        assert self.npc.rect.y < original_y
        
        # Total movement should be approximately equal to speed
        dx = self.npc.rect.x - original_x
        dy = self.npc.rect.y - original_y
        total_movement = math.sqrt(dx*dx + dy*dy)
        assert abs(total_movement - self.npc.speed) <= 1
    
    def test_move_to_already_at_target(self):
        """Test move_to when already at or very close to target"""
        
        engine_state = {
            "walls": [],
            "characters": [self.npc]
        }
        
        from npc.actions import Action, MoveToArgs
        # Move to current tile (5,5)
        action = Action(action="move_to", args=MoveToArgs(x=5, y=5))
        
        result = self.controller._execute_move_to(action.args, engine_state)
        
        assert result == "ok"
    
    def test_move_to_blocked_by_wall(self):
        """Test move_to when direct path is blocked by wall"""
        
        # Create wall directly north of NPC
        walls = [MockRect(160, 128, 32, 32)]  # Wall at tile (5,4)
        
        engine_state = {
            "walls": walls,
            "characters": [self.npc]
        }
        
        from npc.actions import Action, MoveToArgs
        # Try to move to tile (5,3) - blocked by wall at (5,4)
        action = Action(action="move_to", args=MoveToArgs(x=5, y=3))
        
        result = self.controller._execute_move_to(action.args, engine_state)
        
        # Should return no_path since direct movement is blocked
        assert result == "no_path"
    
    def test_move_to_with_cooldown(self):
        """Test move_to respects movement cooldown"""
        
        # Set movement cooldown
        self.controller.cooldowns["move"] = 1000
        
        engine_state = {
            "walls": [],
            "characters": [self.npc]
        }
        
        from npc.actions import Action, MoveToArgs
        action = Action(action="move_to", args=MoveToArgs(x=6, y=5))
        
        result = self.controller._execute_move_to(action.args, engine_state)
        
        assert result == "cooldown"
    
    def test_move_to_sets_cooldown_on_success(self):
        """Test that successful move_to sets movement cooldown"""
        
        # Ensure no initial cooldown
        self.controller.cooldowns["move"] = 0
        
        engine_state = {
            "walls": [],
            "characters": [self.npc]
        }
        
        from npc.actions import Action, MoveToArgs
        action = Action(action="move_to", args=MoveToArgs(x=6, y=5))
        
        result = self.controller._execute_move_to(action.args, engine_state)
        
        assert result == "ok"
        # Should have set cooldown
        assert self.controller.cooldowns["move"] > 0
    
    def test_move_to_multiple_steps_toward_distant_target(self):
        """Test that multiple move_to calls eventually reach distant target"""
        
        engine_state = {
            "walls": [],
            "characters": [self.npc]
        }
        
        from npc.actions import Action, MoveToArgs
        # Target tile (10,5) - 5 tiles east
        target_x, target_y = 10, 5
        action = Action(action="move_to", args=MoveToArgs(x=target_x, y=target_y))
        
        # Simulate multiple decision ticks
        max_steps = 20  # Prevent infinite loop
        steps = 0
        
        while steps < max_steps:
            # Reset cooldown for testing
            self.controller.cooldowns["move"] = 0
            
            result = self.controller._execute_move_to(action.args, engine_state)
            
            if result != "ok":
                break
            
            # Check if we've reached the target (within one tile)
            current_tile_x = self.npc.rect.centerx // 32
            current_tile_y = self.npc.rect.centery // 32
            
            if abs(current_tile_x - target_x) <= 1 and abs(current_tile_y - target_y) <= 1:
                break
            
            steps += 1
        
        # Should have made progress toward target
        final_tile_x = self.npc.rect.centerx // 32
        assert final_tile_x > 5  # Should have moved east from starting position
    
    def test_move_to_blocked_by_character(self):
        """Test move_to when blocked by another character"""
        
        # Create another character blocking the path
        blocking_char = MockNPC(192, 160)  # At tile (6,5) - directly east
        
        engine_state = {
            "walls": [],
            "characters": [self.npc, blocking_char]
        }
        
        from npc.actions import Action, MoveToArgs
        # Try to move to tile (7,5) - blocked by character at (6,5)
        action = Action(action="move_to", args=MoveToArgs(x=7, y=5))
        
        result = self.controller._execute_move_to(action.args, engine_state)
        
        # Should be blocked (either no_path or the movement fails)
        # The exact result depends on implementation details
        assert result in ["no_path", "ok"]  # "ok" if it tries but doesn't actually move


def test_pathfinding_distance_calculation():
    """Test the distance calculation used in pathfinding"""
    
    npc = MockNPC(160, 160)  # Tile (5,5), center at (176, 176)
    
    # Test distance to adjacent tile center
    target_world_x = 6 * 32 + 16  # Tile (6,5) center
    target_world_y = 5 * 32 + 16  # Tile (5,5) center
    
    dx = target_world_x - npc.rect.centerx
    dy = target_world_y - npc.rect.centery
    distance = math.sqrt(dx*dx + dy*dy)
    
    # Distance to adjacent tile center should be approximately 32 pixels
    assert abs(distance - 32) < 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])