"""
Tests for blocked movement scenarios.
Verifies that wall collisions return appropriate "blocked:wall" results.
"""

import pytest
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
    """Mock NPC for testing movement"""
    def __init__(self, x=100, y=100):
        self.rect = MockRect(x, y)
        self.speed = 4
        self.current_health = 100
        self.is_moving = False
        self.speech_text = ""
        self.current_action = "idle"
        self.move_blocked = False  # Flag to simulate blocked movement
        
    def move(self, dx, dy, walls, characters):
        """Mock move method that can simulate blocked movement"""
        if self.move_blocked:
            # Don't move if blocked
            return
        
        # Check for wall collisions
        new_x = self.rect.x + dx
        new_y = self.rect.y + dy
        new_rect = MockRect(new_x, new_y, self.rect.width, self.rect.height)
        
        # Simple collision detection
        for wall in walls:
            if self._rects_overlap(new_rect, wall):
                self.move_blocked = True
                return
        
        # Move if no collision
        self.rect.x = new_x
        self.rect.y = new_y
        self.rect.centerx = new_x + self.rect.width // 2
        self.rect.centery = new_y + self.rect.height // 2
        self.is_moving = True
    
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


class TestBlockedMovement:
    """Test blocked movement scenarios"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.npc = MockNPC(100, 100)
        # Don't create actual LLM client for unit tests
        self.controller = NPCController(self.npc, llm_endpoint="mock://test")
        self.controller.llm_client = None  # Disable LLM for unit tests
    
    def test_move_dir_blocked_by_wall(self):
        """Test that movement blocked by wall returns 'blocked:wall'"""
        
        # Create a wall directly to the north of the NPC
        # NPC is at (100,100), moving north by speed=4, so new position would be (100,96)
        walls = [MockRect(100, 96, 32, 32)]  # Wall at y=96, blocking northward movement
        
        engine_state = {
            "walls": walls,
            "characters": [self.npc]
        }
        
        # Create move_dir action going north (should hit wall)
        from npc.actions import Action, MoveDirArgs
        action = Action(action="move_dir", args=MoveDirArgs(direction="N"))
        
        result = self.controller._execute_move_dir(action.args, engine_state)
        
        assert result == "blocked:wall"
    
    def test_move_dir_success_no_wall(self):
        """Test that movement succeeds when no wall blocks it"""
        
        # No walls in the way
        walls = []
        
        engine_state = {
            "walls": walls,
            "characters": [self.npc]
        }
        
        from npc.actions import Action, MoveDirArgs
        action = Action(action="move_dir", args=MoveDirArgs(direction="N"))
        
        # Store original position
        original_y = self.npc.rect.y
        
        result = self.controller._execute_move_dir(action.args, engine_state)
        
        assert result == "ok"
        assert self.npc.rect.y < original_y  # Should have moved north
    
    def test_move_dir_all_directions_blocked(self):
        """Test all directions blocked by walls"""
        
        # Surround NPC with walls
        npc_x, npc_y = self.npc.rect.x, self.npc.rect.y
        walls = [
            MockRect(npc_x, npc_y - 32, 32, 32),      # North
            MockRect(npc_x + 32, npc_y, 32, 32),      # East  
            MockRect(npc_x, npc_y + 32, 32, 32),      # South
            MockRect(npc_x - 32, npc_y, 32, 32),      # West
        ]
        
        engine_state = {
            "walls": walls,
            "characters": [self.npc]
        }
        
        directions = ["N", "E", "S", "W"]
        
        for direction in directions:
            from npc.actions import Action, MoveDirArgs
            action = Action(action="move_dir", args=MoveDirArgs(direction=direction))
            
            result = self.controller._execute_move_dir(action.args, engine_state)
            assert result == "blocked:wall", f"Direction {direction} should be blocked"
    
    def test_move_dir_with_cooldown(self):
        """Test that movement respects cooldown"""
        
        # Set movement cooldown
        self.controller.cooldowns["move"] = 1000
        
        engine_state = {
            "walls": [],
            "characters": [self.npc]
        }
        
        from npc.actions import Action, MoveDirArgs
        action = Action(action="move_dir", args=MoveDirArgs(direction="N"))
        
        result = self.controller._execute_move_dir(action.args, engine_state)
        
        assert result == "cooldown"
    
    def test_move_to_blocked_path(self):
        """Test move_to when path is blocked"""
        
        # Create wall between NPC and target
        walls = [MockRect(100, 68, 32, 32)]  # Wall blocking northward movement
        
        engine_state = {
            "walls": walls,
            "characters": [self.npc]
        }
        
        from npc.actions import Action, MoveToArgs
        # Try to move to a position north of the wall
        action = Action(action="move_to", args=MoveToArgs(x=3, y=1))  # Tile coordinates
        
        result = self.controller._execute_move_to(action.args, engine_state)
        
        # Should either be "no_path" or "blocked:wall" depending on implementation
        assert result in ["no_path", "blocked:wall"]
    
    def test_move_to_success(self):
        """Test successful move_to action"""
        
        # No walls blocking movement
        walls = []
        
        engine_state = {
            "walls": walls,
            "characters": [self.npc]
        }
        
        from npc.actions import Action, MoveToArgs
        # Move to nearby tile
        action = Action(action="move_to", args=MoveToArgs(x=4, y=3))
        
        original_x = self.npc.rect.x
        
        result = self.controller._execute_move_to(action.args, engine_state)
        
        assert result == "ok"
        # Should have moved toward target
        assert self.npc.rect.x != original_x
    
    def test_move_to_already_at_target(self):
        """Test move_to when already at target location"""
        
        # Calculate current tile position
        current_tile_x = self.npc.rect.centerx // 32
        current_tile_y = self.npc.rect.centery // 32
        
        engine_state = {
            "walls": [],
            "characters": [self.npc]
        }
        
        from npc.actions import Action, MoveToArgs
        # Try to move to current position
        action = Action(action="move_to", args=MoveToArgs(x=current_tile_x, y=current_tile_y))
        
        result = self.controller._execute_move_to(action.args, engine_state)
        
        assert result == "ok"


def test_wall_collision_detection():
    """Test the wall collision detection logic"""
    
    npc = MockNPC(100, 100)
    
    # Test collision with wall directly above
    walls = [MockRect(100, 68, 32, 32)]
    
    # Move north (should collide)
    npc.move(0, -4, walls, [])
    
    # Should not have moved due to collision
    assert npc.rect.y == 100
    assert npc.move_blocked == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])