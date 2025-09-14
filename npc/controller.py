"""
NPC controller that integrates LLM decision-making with game engine.
Handles the main decision loop and action execution.
"""

import time
import math
from typing import Dict, Any, Optional, List, Tuple
from .observation import build_observation
from .llm_client import LLMClient
from .actions import parse_action, Action


class NPCController:
    """Controls LLM-driven NPC behavior"""
    
    def __init__(self, npc, llm_endpoint: str = None):
        self.npc = npc
        self.llm_client = LLMClient(llm_endpoint)
        
        # Decision timing
        self.decision_interval = 4000  # ms between decisions (4-10 game ticks at 60fps)
        self.last_decision_time = 0
        
        # State tracking
        self.last_result = None
        self.goals = ["greet player"]
        self.cooldowns = {"move": 0, "interact": 0}
        self.memory = ""
        
        # Error handling
        self.consecutive_errors = 0
        self.max_consecutive_errors = 3
        self.error_backoff_time = 2000  # ms to wait after errors
        
        # Pathfinding for move_to
        self.current_path = []
        self.path_target = None
        
        # Behavior settings
        self._idle_behavior_enabled = False  # Set to True to enable occasional idle actions
        self.idle_speech_chance = 0.1  # 10% chance of idle speech when making idle decisions
        
        # Movement state for autonomous movement completion
        self.active_movement = None  # "move_dir" or "move_to" when actively moving
        self.movement_target = None  # Target position for move_to
        self.movement_steps_remaining = 0  # Steps left in current movement
        self.movement_direction = None  # Direction for move_dir sequences
        self.movement_steps_per_command = 15  # Default: 16 steps = 2 tiles
        
    def should_make_decision(self, current_time: int, player_spoke: bool = False, player_nearby: bool = False) -> bool:
        """Check if NPC should make a new decision"""
        
        # Always decide if player just spoke
        if player_spoke:
            return True
        
        # Continue active movement sequences (this is key!)
        if self.active_movement and self.movement_steps_remaining > 0:
            time_since_last = current_time - self.last_decision_time
            # Continue movement every 200ms (faster than normal decisions)
            return time_since_last >= 200
        
        # For now, only make decisions when player speaks (unless actively moving)
        if not self._idle_behavior_enabled:
            return False
        
        # Optional idle behavior when enabled
        if player_nearby and self._idle_behavior_enabled:
            time_since_last = current_time - self.last_decision_time
            # Much longer interval for idle behavior (30+ seconds)
            return time_since_last >= (self.decision_interval * 8)
        
        return False
    
    def npc_decision_tick(self, engine_state: Dict[str, Any]) -> Optional[str]:
        """
        Main decision tick - called by game engine.
        
        Args:
            engine_state: Dictionary with game state information
            
        Returns:
            Result string or None if no decision made
        """
        current_time = engine_state.get("current_time", 0)
        player_spoke = engine_state.get("player_spoke", False)
        
        # Calculate if player is nearby (for future idle behavior)
        player_nearby = False
        if "player" in engine_state and "npc" in engine_state:
            player = engine_state["player"]
            npc = engine_state["npc"]
            dx = player.rect.centerx - npc.rect.centerx
            dy = player.rect.centery - npc.rect.centery
            distance = (dx*dx + dy*dy) ** 0.5
            player_nearby = distance < 200  # Within ~6 tiles
        
        # Check if we should make a decision
        if not self.should_make_decision(current_time, player_spoke, player_nearby):
            return None
        
        # Skip if too many consecutive errors
        if self.consecutive_errors >= self.max_consecutive_errors:
            if current_time - self.last_decision_time < self.error_backoff_time:
                return None
            else:
                self.consecutive_errors = 0  # Reset after backoff
        
        # Update cooldowns
        dt = current_time - self.last_decision_time if self.last_decision_time > 0 else 0
        self.cooldowns["move"] = max(0, self.cooldowns["move"] - dt)
        self.cooldowns["interact"] = max(0, self.cooldowns["interact"] - dt)
        
        try:
            # Handle active movement sequences (continue without LLM)
            if self.active_movement and self.movement_steps_remaining > 0:
                print(f"DEBUG: Continuing movement sequence: {self.movement_steps_remaining} steps remaining")
                
                # Continue the movement automatically
                if self.active_movement == "move_dir":
                    from .actions import MoveArgs
                    args = MoveArgs(direction=self.movement_direction, distance=1.0)  # Distance doesn't matter for continuation
                    result = self._execute_move_dir(args, engine_state, distance_tiles=1.0)  # Continue with same distance
                    
                    # Update state
                    self.last_result = result
                    self.last_decision_time = current_time
                    
                    if not result.startswith("invalid") and not result.startswith("parse_error"):
                        self.consecutive_errors = 0
                    else:
                        self.consecutive_errors += 1
                    
                    return result
                
                elif self.active_movement == "move_to":
                    from .actions import MoveToArgs
                    args = MoveToArgs(x=self.movement_target[0] // 32, y=self.movement_target[1] // 32)
                    result = self._continue_move_to(args, engine_state)
                    
                    # Update state
                    self.last_result = result
                    self.last_decision_time = current_time
                    
                    if not result.startswith("invalid") and not result.startswith("parse_error"):
                        self.consecutive_errors = 0
                    else:
                        self.consecutive_errors += 1
                    
                    return result
            
            # Step 1: Build observation
            obs_state = {
                "npc": self.npc,
                "player": engine_state["player"],
                "walls": engine_state.get("walls", []),
                "entities": engine_state.get("entities", []),
                "tick": engine_state.get("tick", 0),
                "last_result": self.last_result,
                "goals": self.goals,
                "cooldowns": self.cooldowns
            }
            
            observation = build_observation(obs_state)
            
            # Debug: Show what triggered this decision
            player_speech = observation.get("player", {}).get("last_said")
            if player_speech:
                print(f"DEBUG: Player said: '{player_speech}' - LLM making decision...")
            else:
                print(f"DEBUG: Autonomous movement continuation...")
            
            # Step 2: Get LLM decision
            raw_response, llm_error = self.llm_client.decide(observation, self.memory)
            
            if llm_error:
                self.last_result = llm_error
                self.consecutive_errors += 1
                self.last_decision_time = current_time
                return llm_error
            
            print(f"DEBUG: LLM raw response: {raw_response}")
            
            # Step 3: Parse and validate action
            action, parse_error = parse_action(raw_response)
            
            if parse_error:
                self.last_result = parse_error
                self.consecutive_errors += 1
                self.last_decision_time = current_time
                return parse_error
            
            print(f"DEBUG: LLM chose action: {action.action} with args: {action.args}")
            
            # Step 4: Execute action
            result = self.execute_action(action, engine_state)
            
            # Step 5: Update state
            self.last_result = result
            self.last_decision_time = current_time
            
            # Reset error count on successful decision
            if not result.startswith("invalid") and not result.startswith("parse_error"):
                self.consecutive_errors = 0
            else:
                self.consecutive_errors += 1
            
            return result
            
        except Exception as e:
            error_msg = f"decision_error: {str(e)}"
            self.last_result = error_msg
            self.consecutive_errors += 1
            self.last_decision_time = current_time
            return error_msg
    
    def execute_action(self, action: Action, engine_state: Dict[str, Any]) -> str:
        """
        Execute a validated action in the game engine.
        
        Args:
            action: Validated Action object
            engine_state: Current game state
            
        Returns:
            Result string ("ok", "blocked:reason", "invalid:reason", etc.)
        """
        
        if action.action == "say":
            print(f"DEBUG: Executing SAY action: '{action.args.text}'")
            return self._execute_say(action.args, engine_state)
        elif action.action == "move":
            print(f"DEBUG: Executing MOVE action: {action.args.direction} ({action.args.distance} tiles)")
            return self._execute_move_dir(action.args, engine_state, distance_tiles=action.args.distance)
        elif action.action == "move_to":
            print(f"DEBUG: Executing MOVE_TO action: ({action.args.x}, {action.args.y})")
            return self._execute_move_to(action.args, engine_state)
        elif action.action == "interact":
            print(f"DEBUG: Executing INTERACT action: {action.args.entity_id}")
            return self._execute_interact(action.args, engine_state)
        elif action.action == "transfer_item":
            print(f"DEBUG: Executing TRANSFER_ITEM action: {action.args.item_id} to {action.args.entity_id}")
            return self._execute_transfer_item(action.args, engine_state)
        else:
            print(f"DEBUG: UNKNOWN ACTION: {action.action}")
            return f"invalid: Unknown action {action.action}"
    
    def _execute_say(self, args, engine_state: Dict[str, Any]) -> str:
        """Execute say action"""
        try:
            # Make NPC say the text
            self.npc.say(args.text)
            return "ok"
        except Exception as e:
            return f"invalid: Say failed - {str(e)}"
    
    def _execute_move_dir(self, args, engine_state: Dict[str, Any], distance_tiles: float = 1.0) -> str:
        """Execute move_dir action with configurable distance"""
        
        # Check move cooldown
        if self.cooldowns["move"] > 0:
            return "cooldown"
        
        # Convert direction to movement delta
        direction_map = {
            "N": (0, -self.npc.speed),
            "S": (0, self.npc.speed),
            "E": (self.npc.speed, 0),
            "W": (-self.npc.speed, 0)
        }
        
        dx, dy = direction_map[args.direction]
        
        # Store original position
        old_x, old_y = self.npc.rect.x, self.npc.rect.y
        
        # Attempt movement
        walls = engine_state.get("walls", [])
        other_characters = engine_state.get("characters", [])
        
        self.npc.move(dx, dy, walls, other_characters)
        
        # Check if movement succeeded
        if self.npc.rect.x != old_x or self.npc.rect.y != old_y:
            # Set cooldown (shorter for movement sequences)
            self.cooldowns["move"] = 200  # 200ms cooldown for smoother movement
            distance_moved = ((self.npc.rect.x - old_x)**2 + (self.npc.rect.y - old_y)**2)**0.5
            print(f"DEBUG: NPC moved {args.direction} by {distance_moved:.1f} pixels to ({self.npc.rect.x}, {self.npc.rect.y})")
            
            # Set up movement sequence (continue moving in same direction)
            if not self.active_movement:
                # Calculate steps based on distance
                steps_per_tile = 32 // self.npc.speed  # 32 pixels per tile / pixels per step
                total_steps = max(1, int(distance_tiles * steps_per_tile))
                total_pixels = total_steps * self.npc.speed
                
                print(f"DEBUG: Movement calculation:")
                print(f"  - Distance requested: {distance_tiles} tiles")
                print(f"  - NPC speed: {self.npc.speed} pixels/step")
                print(f"  - Steps per tile: {steps_per_tile}")
                print(f"  - Total steps: {total_steps}")
                print(f"  - Total pixels: {total_pixels}")
                
                # Start new movement sequence - move multiple steps
                self.active_movement = "move_dir"
                self.movement_steps_remaining = total_steps - 1  # -1 because first step is immediate
                self.movement_direction = args.direction
                print(f"DEBUG: Starting movement sequence: {total_steps} steps {args.direction} ({distance_tiles} tiles)")
            else:
                # Continue existing movement sequence
                self.movement_steps_remaining -= 1
                print(f"DEBUG: Movement sequence: {self.movement_steps_remaining} steps remaining")
                
                if self.movement_steps_remaining <= 0:
                    # Movement sequence complete
                    self.active_movement = None
                    self.movement_direction = None
                    print(f"DEBUG: Movement sequence completed")
            
            return "ok"
        else:
            # Movement was blocked - stop sequence
            print(f"DEBUG: NPC movement {args.direction} blocked at ({old_x}, {old_y})")
            self.active_movement = None
            self.movement_steps_remaining = 0
            return "blocked:wall"
    
    def _execute_move_to(self, args, engine_state: Dict[str, Any]) -> str:
        """Execute move_to action with autonomous movement to target"""
        
        # Check move cooldown
        if self.cooldowns["move"] > 0:
            return "cooldown"
        
        target_world_x = args.x * 32  # Convert tile to world coordinates
        target_world_y = args.y * 32
        
        print(f"DEBUG: Move_to target: tile ({args.x}, {args.y}) = world ({target_world_x}, {target_world_y})")
        
        # Check if already at target
        npc_x, npc_y = self.npc.rect.centerx, self.npc.rect.centery
        dx = target_world_x - npc_x
        dy = target_world_y - npc_y
        distance = math.sqrt(dx*dx + dy*dy)
        
        print(f"DEBUG: Current position: ({npc_x}, {npc_y}), distance to target: {distance:.1f}")
        
        if distance < 16:  # Already at target (within half a tile)
            print("DEBUG: Already at target")
            return "ok"
        
        # Set up autonomous movement to target
        self.movement_target = (target_world_x, target_world_y)
        self.active_movement = "move_to"
        
        # Calculate how many steps needed (more generous estimate)
        steps_needed = int(distance / self.npc.speed) + 10  # Add buffer for precision
        self.movement_steps_remaining = min(steps_needed, 200)  # Cap at 200 steps for safety
        
        print(f"DEBUG: Starting autonomous move_to: {steps_needed} steps to reach target")
        
        # Take first step
        if distance > 0:
            move_dx = (dx / distance) * self.npc.speed
            move_dy = (dy / distance) * self.npc.speed
        else:
            return "ok"
        
        # Store original position
        old_x, old_y = self.npc.rect.x, self.npc.rect.y
        
        # Attempt movement
        walls = engine_state.get("walls", [])
        other_characters = engine_state.get("characters", [])
        
        self.npc.move(move_dx, move_dy, walls, other_characters)
        
        # Check if movement succeeded
        if self.npc.rect.x != old_x or self.npc.rect.y != old_y:
            print(f"DEBUG: {self.npc.name} moved toward target to ({self.npc.rect.x}, {self.npc.rect.y})")
            self.cooldowns["move"] = 200  # Shorter cooldown for autonomous movement
            self.movement_steps_remaining -= 1
            return "ok"
        else:
            # Movement blocked
            self.active_movement = None
            self.movement_target = None
            self.movement_steps_remaining = 0
            return "blocked:obstacle"
    
    def _execute_interact(self, args, engine_state: Dict[str, Any]) -> str:
        """Execute interact action"""
        
        # Check interact cooldown
        if self.cooldowns["interact"] > 0:
            return "cooldown"
        
        # Find the entity to interact with
        entities = engine_state.get("entities", [])
        target_entity = None
        
        for entity in entities:
            if entity.get("id") == args.entity_id:
                target_entity = entity
                break
        
        if not target_entity:
            return "invalid: Entity not found"
        
        # Check if entity is reachable (within interaction distance)
        entity_x = target_entity.get("x", 0)
        entity_y = target_entity.get("y", 0)
        npc_x, npc_y = self.npc.rect.centerx, self.npc.rect.centery
        
        distance = math.sqrt((entity_x - npc_x)**2 + (entity_y - npc_y)**2)
        
        if distance > 64:  # Max interaction distance
            return "blocked:too_far"
        
        # Set cooldown and execute interaction
        self.cooldowns["interact"] = 1000  # 1 second cooldown
        
        # For now, just acknowledge the interaction
        # In a full game, this would trigger entity-specific behavior
        return "ok"
    
    def _execute_transfer_item(self, args, engine_state: Dict[str, Any]) -> str:
        """Execute transfer_item action"""
        
        # Find target character
        characters = engine_state.get("characters", [])
        target_char = None
        
        for char in characters:
            if getattr(char, 'name', '') == args.entity_id:
                target_char = char
                break
        
        if not target_char:
            return "invalid: Character not found"
        
        # Check distance
        char_x, char_y = target_char.rect.centerx, target_char.rect.centery
        npc_x, npc_y = self.npc.rect.centerx, self.npc.rect.centery
        distance = math.sqrt((char_x - npc_x)**2 + (char_y - npc_y)**2)
        
        if distance > 64:
            return "blocked:too_far"
        
        # Check if NPC has the item
        if not self.npc.has_item(args.item_id):
            return "invalid: Item not in inventory"
        
        # Transfer item
        removed_qty = self.npc.remove_item(args.item_id, 1)
        if removed_qty > 0:
            if target_char.add_item(args.item_id, removed_qty):
                return "ok"
            else:
                # Target inventory full, give item back
                self.npc.add_item(args.item_id, removed_qty)
                return "blocked:inventory_full"
        
        return "invalid: Transfer failed"
    
    def _continue_move_to(self, args, engine_state: Dict[str, Any]) -> str:
        """Continue autonomous move_to movement"""
        
        if not self.movement_target:
            # No target set, stop movement
            self.active_movement = None
            self.movement_steps_remaining = 0
            return "ok"
        
        target_world_x, target_world_y = self.movement_target
        npc_x, npc_y = self.npc.rect.centerx, self.npc.rect.centery
        
        # Check if we've reached the target
        dx = target_world_x - npc_x
        dy = target_world_y - npc_y
        distance = math.sqrt(dx*dx + dy*dy)
        
        if distance < 16:  # Within half a tile of target
            print(f"DEBUG: Reached move_to target at ({target_world_x}, {target_world_y})")
            self.active_movement = None
            self.movement_target = None
            self.movement_steps_remaining = 0
            return "ok"
        
        # Continue moving toward target
        if distance > 0:
            move_dx = (dx / distance) * self.npc.speed
            move_dy = (dy / distance) * self.npc.speed
        else:
            self.active_movement = None
            self.movement_target = None
            self.movement_steps_remaining = 0
            return "ok"
        
        # Store original position
        old_x, old_y = self.npc.rect.x, self.npc.rect.y
        
        # Attempt movement
        walls = engine_state.get("walls", [])
        other_characters = engine_state.get("characters", [])
        
        self.npc.move(move_dx, move_dy, walls, other_characters)
        
        # Check if movement succeeded
        if self.npc.rect.x != old_x or self.npc.rect.y != old_y:
            print(f"DEBUG: Continuing move_to: ({self.npc.rect.x}, {self.npc.rect.y}) -> target ({target_world_x}, {target_world_y})")
            self.movement_steps_remaining -= 1
            
            # Check if we should stop (safety limit or reached target)
            if self.movement_steps_remaining <= 0:
                print("DEBUG: Move_to reached step limit")
                self.active_movement = None
                self.movement_target = None
                self.movement_steps_remaining = 0
            
            return "ok"
        else:
            # Movement blocked, stop
            print("DEBUG: Move_to blocked by obstacle")
            self.active_movement = None
            self.movement_target = None
            self.movement_steps_remaining = 0
            return "blocked:obstacle"
    
    def set_goals(self, goals: List[str]):
        """Update NPC goals"""
        self.goals = goals
    
    def add_memory(self, memory_text: str):
        """Add to NPC memory"""
        if self.memory:
            self.memory += f"\n{memory_text}"
        else:
            self.memory = memory_text
        
        # Keep memory reasonably short
        lines = self.memory.split('\n')
        if len(lines) > 5:
            self.memory = '\n'.join(lines[-5:])
    
    def enable_idle_behavior(self, enabled: bool = True, speech_chance: float = 0.1):
        """
        Enable or disable idle behavior (thinking out loud, random movement, etc.)
        
        Args:
            enabled: Whether to enable idle behavior
            speech_chance: Probability (0.0-1.0) of speaking during idle decisions
        """
        self._idle_behavior_enabled = enabled
        self.idle_speech_chance = max(0.0, min(1.0, speech_chance))
        
        if enabled:
            print(f"NPC idle behavior enabled (speech chance: {speech_chance:.1%})")
        else:
            print("NPC idle behavior disabled - will only respond when spoken to")
    
    def set_movement_distance(self, tiles: float = 2.0):
        """
        Set how far the NPC moves when given a movement command.
        
        Args:
            tiles: Distance in tiles (1.0 = 32 pixels, 2.0 = 64 pixels, etc.)
        """
        steps_per_tile = 32 // self.npc.speed  # 32 pixels per tile / pixels per step
        self.movement_steps_per_command = max(1, int(tiles * steps_per_tile)) - 1  # -1 because first step is immediate
        print(f"Movement distance set to {tiles} tiles ({self.movement_steps_per_command + 1} steps)")
    
    @property
    def idle_behavior_enabled(self):
        """Check if idle behavior is currently enabled"""
        return self._idle_behavior_enabled


def test_npc_controller():
    """Test the NPC controller with mock objects"""
    
    # Mock NPC class
    class MockNPC:
        def __init__(self):
            self.rect = type('Rect', (), {'x': 320, 'y': 160, 'centerx': 336, 'centery': 176})()
            self.current_health = 100
            self.is_moving = False
            self.speech_text = ""
            self.current_action = "idle"
            self.speed = 4
            
        def say(self, text):
            self.speech_text = text
            print(f"NPC says: {text}")
            
        def move(self, dx, dy, walls, characters):
            self.rect.x += dx
            self.rect.y += dy
            self.rect.centerx = self.rect.x + 16
            self.rect.centery = self.rect.y + 16
            self.is_moving = True
            
        def has_item(self, item_id):
            return False
            
        def remove_item(self, item_id, qty):
            return 0
            
        def add_item(self, item_id, qty):
            return True
    
    # Mock player
    class MockPlayer:
        def __init__(self):
            self.rect = type('Rect', (), {'centerx': 400, 'centery': 176})()
            self.speech_text = "Hello there!"
    
    # Create controller
    npc = MockNPC()
    controller = NPCController(npc)
    
    # Test decision making
    engine_state = {
        "npc": npc,
        "player": MockPlayer(),
        "walls": [],
        "entities": [],
        "characters": [npc],
        "current_time": 5000,
        "player_spoke": True,
        "tick": 100
    }
    
    print("Testing NPC controller...")
    result = controller.npc_decision_tick(engine_state)
    print(f"Decision result: {result}")


if __name__ == "__main__":
    test_npc_controller()