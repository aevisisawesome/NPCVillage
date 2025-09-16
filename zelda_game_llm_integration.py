"""
Integration of LLM-driven NPC system into the existing Zelda game.
This file shows how to modify the existing game to use the new NPC controller.
"""

import pygame
import sys
import random
import math
import time
from npc.controller import NPCController
from npc.observation import build_observation
from llm_config import get_llm_config, print_config_info


# Modify the existing NPC class to integrate with LLM controller
class LLMDrivenNPC:
    """Enhanced NPC class with LLM-driven behavior"""
    
    def __init__(self, x, y, name="NPC", npc_role="generic"):
        # Initialize base NPC properties (from original NPC class)
        self.x = x
        self.y = y
        self.width = 32 - 12  # Reduced collision box for easier doorway navigation
        self.height = 32 - 12  # Reduced collision box for easier doorway navigation
        self.speed = 4  # Match player speed for more visible movement
        self.rect = pygame.Rect(x, y, self.width, self.height)
        
        # Character identity
        self.name = name
        self.npc_role = npc_role
        self.character_type = "npc"
        
        # Animation and visual
        self.is_moving = False
        self.animation_frame = 0
        self.animation_timer = 0
        self.animation_speed = 200
        
        # Speech system
        self.speech_text = ""
        self.speech_timer = 0
        self.speech_duration = 3000
        
        # Stats
        self.max_health = 100
        self.current_health = 100
        self.inventory_size = 8
        self.inventory = [None] * self.inventory_size
        self.gold = 200
        
        # Visual appearance
        self.hud_color = (0, 100, 255)
        self.shirt_color = (128, 0, 128)
        self.hair_color = (128, 128, 128)
        self.skin_color = (255, 220, 177)
        self.pants_color = (139, 69, 19)
        
        # LLM Controller - use configuration
        config = get_llm_config()
        self.llm_controller = NPCController(self, 
                                          llm_endpoint=config["endpoint"],
                                          use_tool_calls=config["use_tool_calls"])
        
        # Game integration
        self.last_player_speech = None
        self.last_player_speech_time = 0
        self.recent_speech_from = None  # Track who spoke to us recently
        
        # Set role-specific properties and character description
        if npc_role == "shopkeeper":
            self.set_role_appearance("shopkeeper")
            self.stock_shop()
            self.character_description = self.get_shopkeeper_description()
        elif npc_role == "innkeeper":
            self.character_description = self.get_innkeeper_description()
        else:
            self.character_description = f"You are {name}, a {npc_role}. Act according to your role."
        
        # By default, only respond when spoken to
        self.llm_controller.enable_idle_behavior(False)
        
        # Set movement distance to 2 tiles for visible movement
        self.llm_controller.set_movement_distance(2.0)
    
    def get_shopkeeper_description(self):
        """Get character description for Garruk the shopkeeper"""
        return """You are **Garruk Ironhand**, a grizzled shopkeeper who runs an equipment shop. 

PERSONALITY: Blunt, impatient, and practical. You speak in short, direct sentences. You've been running this shop for decades and have little patience for small talk, but you're honest in your dealings.

BACKGROUND: You're a former adventurer who settled down to run this equipment shop. You know the value of good gear and take pride in your inventory. You've seen many heroes come and go.

SPEECH STYLE: Gruff and to the point. Use short sentences. Occasionally grumble about business or reminisce briefly about your adventuring days."""

    def get_innkeeper_description(self):
        """Get character description for Marta the innkeeper"""
        return """You are **Marta Brewkeeper**, the warm-hearted innkeeper of The Prancing Pony Tavern.

PERSONALITY: Friendly, welcoming, and chatty. You genuinely care about your guests and love hearing stories from travelers. You're the social heart of the community.

BACKGROUND: You inherited the tavern from your family and have been running it for years. You know all the local gossip and news. You take pride in your ale, food, and comfortable rooms.

SPEECH STYLE: Warm and conversational. You often ask about travelers' journeys and share local news. You're more talkative than most, but still keep responses concise."""

    def set_role_appearance(self, role):
        """Set appearance based on NPC role"""
        if role == "shopkeeper":
            self.inventory_size = 12
            self.inventory = [None] * self.inventory_size
            self.gold = 500
            self.llm_controller.set_goals(["greet player", "sell items", "discuss inventory"])
        elif role == "innkeeper":
            self.inventory_size = 10
            self.inventory = [None] * self.inventory_size
            self.gold = 300
            self.llm_controller.set_goals(["welcome travelers", "serve drinks and food", "offer rooms for rent"])
    
    def stock_shop(self):
        """Stock the shop with initial items"""
        if self.npc_role == "shopkeeper":
            shop_items = [
                ("health_potion", 5),
                ("mana_potion", 3),
                ("iron_sword", 2),
                ("leather_armor", 1),
                ("rope", 10),
                ("torch", 8)
            ]
            
            for item_id, quantity in shop_items:
                self.add_item(item_id, quantity)
    
    def add_item(self, item_id, quantity=1):
        """Add an item to inventory (simplified for demo)"""
        for i in range(self.inventory_size):
            if self.inventory[i] is None:
                # Create a simple item object
                item = type('Item', (), {
                    'id': item_id,
                    'name': item_id.replace('_', ' ').title(),
                    'color': (100, 100, 200)
                })()
                self.inventory[i] = {"item": item, "quantity": quantity}
                return True
        return False
    
    def remove_item(self, item_id, quantity=1):
        """Remove an item from inventory"""
        for i in range(self.inventory_size):
            if (self.inventory[i] and 
                self.inventory[i]["item"].id == item_id):
                
                if self.inventory[i]["quantity"] <= quantity:
                    removed_qty = self.inventory[i]["quantity"]
                    self.inventory[i] = None
                    return removed_qty
                else:
                    self.inventory[i]["quantity"] -= quantity
                    return quantity
        return 0
    
    def has_item(self, item_id):
        """Check if NPC has an item"""
        for slot in self.inventory:
            if slot and slot["item"].id == item_id:
                return slot["quantity"]
        return 0
    
    def get_inventory_list(self):
        """Get a list of items in inventory for LLM"""
        items = []
        for slot in self.inventory:
            if slot:
                item = slot["item"]
                qty = slot["quantity"]
                items.append(f"{qty}x {item.name}")
        return items if items else ["Empty"]
    
    def move(self, dx, dy, walls, other_characters=None):
        """Move the NPC with collision detection"""
        moved = False
        
        # Try X movement first
        if dx != 0:
            new_rect_x = self.rect.copy()
            new_rect_x.x += dx
            
            x_valid = new_rect_x.left >= 0 and new_rect_x.right <= 800  # Screen width
            x_collision = False
            
            if x_valid:
                for wall in walls:
                    if new_rect_x.colliderect(wall):
                        x_collision = True
                        break
                
                if not x_collision and other_characters:
                    for char in other_characters:
                        if char != self and new_rect_x.colliderect(char.rect):
                            x_collision = True
                            break
            
            if x_valid and not x_collision:
                self.rect.x = new_rect_x.x
                moved = True
        
        # Try Y movement
        if dy != 0:
            new_rect_y = self.rect.copy()
            new_rect_y.y += dy
            
            y_valid = new_rect_y.top >= 0 and new_rect_y.bottom <= 600  # Screen height
            y_collision = False
            
            if y_valid:
                for wall in walls:
                    if new_rect_y.colliderect(wall):
                        y_collision = True
                        break
                
                if not y_collision and other_characters:
                    for char in other_characters:
                        if char != self and new_rect_y.colliderect(char.rect):
                            y_collision = True
                            break
            
            if y_valid and not y_collision:
                self.rect.y = new_rect_y.y
                moved = True
        
        self.x = self.rect.x
        self.y = self.rect.y
        self.is_moving = moved
        
        # Debug output for movement
        if moved:
            print(f"DEBUG: {self.name} moved to ({self.rect.x}, {self.rect.y})")
    
    def say(self, message):
        """Make the NPC say something"""
        print(f"DEBUG: {self.name} saying: '{message}'")
        self.speech_text = message
        self.speech_timer = 0
    
    def react_to_speech(self, message, speaker):
        """React to speech from nearby characters (called by hearing system)"""
        print(f"DEBUG: {self.name} heard '{message}' from {speaker.name}")
        self.last_player_speech = message
        self.last_player_speech_time = time.time() * 1000
        self.recent_speech_from = speaker
    
    def update(self, dt, walls, other_characters, player):
        """Update NPC with LLM-driven behavior"""
        
        # Update animation
        if self.is_moving:
            self.animation_timer += dt
            if self.animation_timer >= self.animation_speed:
                self.animation_frame = (self.animation_frame + 1) % 2
                self.animation_timer = 0
        else:
            self.animation_frame = 0
            self.animation_timer = 0
        
        # Update speech timer
        if self.speech_text:
            self.speech_timer += dt
            if self.speech_timer >= self.speech_duration:
                self.speech_text = ""
                self.speech_timer = 0
        
        # Check if someone spoke to us recently (via react_to_speech)
        player_spoke = False
        current_time = time.time() * 1000
        
        # Only consider it "recent" if it happened within the last 500ms
        if (self.last_player_speech and 
            current_time - self.last_player_speech_time < 500):
            player_spoke = True
            # Clear the speech after processing to avoid repeated responses
            self.last_player_speech = None
        
        # Prepare engine state for LLM controller (current_time already defined above)
        
        # Create simple entities list (doors, etc.)
        entities = []
        # In a full implementation, you'd populate this with interactive objects
        
        engine_state = {
            "npc": self,
            "player": player,
            "walls": walls,
            "entities": entities,
            "characters": other_characters,
            "current_time": current_time,
            "player_spoke": player_spoke,
            "tick": int(current_time / 16.67)  # Approximate tick at 60fps
        }
        
        # Run LLM decision tick
        result = self.llm_controller.npc_decision_tick(engine_state)
        
        if result:
            print(f"DEBUG: NPC decision result: {result}")
    
    def draw_sprite_frame(self, screen, frame):
        """Draw character sprite (same as original)"""
        x, y = self.rect.x, self.rect.y
        
        if frame == 0:  # Standing
            pygame.draw.rect(screen, self.skin_color, (x + 10, y + 2, 8, 8))  # Head
            pygame.draw.rect(screen, self.hair_color, (x + 8, y, 12, 6))      # Hair
            pygame.draw.rect(screen, self.shirt_color, (x + 8, y + 10, 12, 10))  # Body
            pygame.draw.rect(screen, self.skin_color, (x + 4, y + 12, 4, 8))  # Left arm
            pygame.draw.rect(screen, self.skin_color, (x + 20, y + 12, 4, 8)) # Right arm
            pygame.draw.rect(screen, self.pants_color, (x + 10, y + 20, 8, 8))  # Legs
            pygame.draw.rect(screen, self.hair_color, (x + 8, y + 26, 4, 2))  # Left foot
            pygame.draw.rect(screen, self.hair_color, (x + 16, y + 26, 4, 2)) # Right foot
        else:  # Walking
            pygame.draw.rect(screen, self.skin_color, (x + 10, y + 2, 8, 8))  # Head
            pygame.draw.rect(screen, self.hair_color, (x + 8, y, 12, 6))      # Hair
            pygame.draw.rect(screen, self.shirt_color, (x + 8, y + 10, 12, 10))  # Body
            pygame.draw.rect(screen, self.skin_color, (x + 6, y + 12, 4, 8))  # Left arm
            pygame.draw.rect(screen, self.skin_color, (x + 18, y + 12, 4, 8)) # Right arm
            pygame.draw.rect(screen, self.pants_color, (x + 8, y + 20, 4, 8))  # Left leg
            pygame.draw.rect(screen, self.pants_color, (x + 16, y + 20, 4, 8)) # Right leg
            pygame.draw.rect(screen, self.hair_color, (x + 6, y + 26, 4, 2))  # Left foot
            pygame.draw.rect(screen, self.hair_color, (x + 18, y + 26, 4, 2)) # Right foot
    
    def draw_speech_bubble(self, screen):
        """Draw speech bubble above character (same as original)"""
        if not self.speech_text:
            return
        
        font = pygame.font.Font(None, 24)
        words = self.speech_text.split(' ')
        lines = []
        current_line = ""
        max_width = 200
        
        for word in words:
            test_line = current_line + (" " if current_line else "") + word
            text_width = font.size(test_line)[0]
            if text_width <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)
        
        line_height = font.get_height()
        bubble_width = max(font.size(line)[0] for line in lines) + 20
        bubble_height = len(lines) * line_height + 20
        
        bubble_x = self.rect.centerx - bubble_width // 2
        bubble_y = self.rect.top - bubble_height - 10
        
        bubble_x = max(5, min(bubble_x, 800 - bubble_width - 5))
        bubble_y = max(5, bubble_y)
        
        bubble_rect = pygame.Rect(bubble_x, bubble_y, bubble_width, bubble_height)
        pygame.draw.rect(screen, (255, 255, 255), bubble_rect)
        pygame.draw.rect(screen, (0, 0, 0), bubble_rect, 2)
        
        tail_points = [
            (self.rect.centerx - 5, bubble_y + bubble_height),
            (self.rect.centerx + 5, bubble_y + bubble_height),
            (self.rect.centerx, bubble_y + bubble_height + 8)
        ]
        pygame.draw.polygon(screen, (255, 255, 255), tail_points)
        pygame.draw.polygon(screen, (0, 0, 0), tail_points, 2)
        
        for i, line in enumerate(lines):
            text_surface = font.render(line, True, (0, 0, 0))
            text_x = bubble_x + 10
            text_y = bubble_y + 10 + i * line_height
            screen.blit(text_surface, (text_x, text_y))
    
    def draw_hud(self, screen):
        """Draw character HUD (simplified)"""
        hud_x = self.rect.x
        hud_y = self.rect.y + self.rect.height + 5
        hud_width = max(80, len(self.name) * 8)
        
        # Simple name display
        font = pygame.font.Font(None, 16)
        name_text = font.render(self.name, True, (255, 255, 255))
        
        # Background
        bg_rect = pygame.Rect(hud_x, hud_y, hud_width, 20)
        pygame.draw.rect(screen, (0, 0, 0, 100), bg_rect)
        pygame.draw.rect(screen, self.hud_color, bg_rect, 2)
        
        screen.blit(name_text, (hud_x + 4, hud_y + 2))
    
    def draw(self, screen):
        """Draw the NPC"""
        self.draw_sprite_frame(screen, self.animation_frame)
        self.draw_speech_bubble(screen)
        self.draw_hud(screen)


def create_llm_shopkeeper(x, y):
    """Factory function to create an LLM-driven shopkeeper"""
    return LLMDrivenNPC(x, y, "Garruk Ironhand", "shopkeeper")

def create_llm_innkeeper(x, y):
    """Factory function to create an LLM-driven innkeeper"""
    innkeeper = LLMDrivenNPC(x, y, "Marta Brewkeeper", "innkeeper")
    
    # Set innkeeper-specific appearance
    innkeeper.shirt_color = (139, 69, 19)  # Brown shirt
    innkeeper.hair_color = (160, 82, 45)   # Auburn hair
    innkeeper.pants_color = (85, 107, 47)  # Dark olive pants
    innkeeper.hud_color = (255, 140, 0)    # Orange HUD
    
    # Set innkeeper-specific properties
    innkeeper.inventory_size = 10
    innkeeper.inventory = [None] * innkeeper.inventory_size
    innkeeper.gold = 300
    
    # Stock tavern with drinks and food
    tavern_items = [
        ("ale", 8),
        ("wine", 4),
        ("bread", 6),
        ("cheese", 5),
        ("stew", 3),
        ("room_key", 2)
    ]
    
    for item_id, quantity in tavern_items:
        innkeeper.add_item(item_id, quantity)
    
    # Set innkeeper-specific role properties
    innkeeper.set_role_appearance("innkeeper")
    
    # Set innkeeper goals
    innkeeper.llm_controller.set_goals([
        "welcome travelers", 
        "serve drinks and food", 
        "offer rooms for rent",
        "share local gossip"
    ])
    
    return innkeeper


# Example of how to integrate into the main game
def integrate_llm_npc_into_game():
    """
    Example showing how to replace the existing NPC with LLM-driven version.
    
    In your main game file, you would:
    1. Replace the existing shopkeeper creation with create_llm_shopkeeper()
    2. Update the game loop to call npc.update() with the required parameters
    3. Ensure the LLM server is running at the configured endpoint
    """
    
    print("LLM NPC Integration Example")
    print("=" * 40)
    
    # Create LLM-driven shopkeeper
    shopkeeper = create_llm_shopkeeper(400, 250)
    
    print(f"Created {shopkeeper.name} with LLM controller")
    print(f"Goals: {shopkeeper.llm_controller.goals}")
    print(f"Inventory: {shopkeeper.get_inventory_list()}")
    
    # Test the observation builder
    from npc.observation import build_observation
    
    # Mock player for testing
    class MockPlayer:
        def __init__(self):
            self.rect = pygame.Rect(450, 250, 28, 28)
            self.speech_text = "Hello there!"
            self.current_health = 100
    
    player = MockPlayer()
    walls = [pygame.Rect(300, 200, 200, 10)]  # Simple wall
    
    engine_state = {
        "npc": shopkeeper,
        "player": player,
        "walls": walls,
        "entities": [],
        "tick": 100,
        "last_result": None,
        "goals": ["greet player"],
        "cooldowns": {"move": 0, "interact": 0}
    }
    
    observation = build_observation(engine_state)
    
    print("\nSample Observation:")
    print("-" * 20)
    from npc.observation import format_observation_for_llm
    print(format_observation_for_llm(observation))
    
    print("\nIntegration complete!")
    print("To use in your game:")
    print("1. Replace 'create_shopkeeper()' with 'create_llm_shopkeeper()'")
    print("2. Update game loop to call 'npc.update(dt, walls, characters, player)'")
    print("3. Start your local LLM server at http://127.0.0.1:1234")


if __name__ == "__main__":
    # Initialize pygame for testing
    pygame.init()
    
    integrate_llm_npc_into_game()