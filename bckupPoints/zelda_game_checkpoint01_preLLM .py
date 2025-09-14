import pygame
import sys
import random
import math

# Initialize Pygame
pygame.init()

# Constants
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
TILE_SIZE = 32
FPS = 60

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREEN = (0, 128, 0)
BROWN = (139, 69, 19)
GRAY = (128, 128, 128)
BLUE = (0, 0, 255)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)

class Player:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = TILE_SIZE - 4
        self.height = TILE_SIZE - 4
        self.speed = 4
        self.rect = pygame.Rect(x, y, self.width, self.height)
        
        # Animation variables
        self.is_moving = False
        self.animation_frame = 0
        self.animation_timer = 0
        self.animation_speed = 200  # milliseconds between frames
        
        # Speech system
        self.speech_text = ""
        self.speech_timer = 0
        self.speech_duration = 3000  # 3 seconds
        
        # HUD system
        self.name = "Player"
        self.max_health = 100
        self.current_health = 100
        self.inventory = [None, None, None]  # 3 inventory slots
        self.hud_color = (0, 255, 0)  # Green for player
    
    def move(self, dx, dy, walls, other_characters=None):
        # Check X and Y movement separately to allow sliding along walls
        moved = False
        
        # Try X movement first
        if dx != 0:
            new_rect_x = self.rect.copy()
            new_rect_x.x += dx
            
            # Check X boundaries
            x_valid = new_rect_x.left >= 0 and new_rect_x.right <= SCREEN_WIDTH
            
            # Check X collisions
            x_collision = False
            if x_valid:
                for wall in walls:
                    if new_rect_x.colliderect(wall):
                        x_collision = True
                        break
                
                # Check character collisions for X movement
                if not x_collision and other_characters:
                    for char in other_characters:
                        if char != self and new_rect_x.colliderect(char.rect):
                            x_collision = True
                            break
            
            # Apply X movement if valid
            if x_valid and not x_collision:
                self.rect.x = new_rect_x.x
                moved = True
        
        # Try Y movement
        if dy != 0:
            new_rect_y = self.rect.copy()
            new_rect_y.y += dy
            
            # Check Y boundaries
            y_valid = new_rect_y.top >= 0 and new_rect_y.bottom <= SCREEN_HEIGHT
            
            # Check Y collisions
            y_collision = False
            if y_valid:
                for wall in walls:
                    if new_rect_y.colliderect(wall):
                        y_collision = True
                        break
                
                # Check character collisions for Y movement
                if not y_collision and other_characters:
                    for char in other_characters:
                        if char != self and new_rect_y.colliderect(char.rect):
                            y_collision = True
                            break
            
            # Apply Y movement if valid
            if y_valid and not y_collision:
                self.rect.y = new_rect_y.y
                moved = True
        
        # Update position variables and animation state
        self.x = self.rect.x
        self.y = self.rect.y
        self.is_moving = moved
    
    def update(self, dt):
        # Update animation
        if self.is_moving:
            self.animation_timer += dt
            if self.animation_timer >= self.animation_speed:
                self.animation_frame = (self.animation_frame + 1) % 2
                self.animation_timer = 0
        else:
            self.animation_frame = 0
            self.animation_timer = 0
        
        # Update speech bubble timer
        if self.speech_text:
            self.speech_timer += dt
            if self.speech_timer >= self.speech_duration:
                self.speech_text = ""
                self.speech_timer = 0
    
    def draw_sprite_frame(self, screen, frame):
        # Character colors
        RED_SHIRT = (200, 50, 50)
        GRAY_ARMOR = (150, 150, 150)
        SKIN = (255, 220, 177)
        DARK_GRAY = (80, 80, 80)
        YELLOW = (255, 255, 0)
        
        # Base position
        x, y = self.rect.x, self.rect.y
        
        # Draw character based on frame (pixel art style)
        if frame == 0:  # Standing/Frame 1
            # Head
            pygame.draw.rect(screen, SKIN, (x + 10, y + 2, 8, 8))
            # Hair
            pygame.draw.rect(screen, DARK_GRAY, (x + 8, y, 12, 6))
            # Body (red shirt)
            pygame.draw.rect(screen, RED_SHIRT, (x + 8, y + 10, 12, 10))
            # Arms
            pygame.draw.rect(screen, SKIN, (x + 4, y + 12, 4, 8))
            pygame.draw.rect(screen, SKIN, (x + 20, y + 12, 4, 8))
            # Legs
            pygame.draw.rect(screen, GRAY_ARMOR, (x + 10, y + 20, 8, 8))
            # Feet
            pygame.draw.rect(screen, DARK_GRAY, (x + 8, y + 26, 4, 2))
            pygame.draw.rect(screen, DARK_GRAY, (x + 16, y + 26, 4, 2))
        else:  # Walking frame 2
            # Head
            pygame.draw.rect(screen, SKIN, (x + 10, y + 2, 8, 8))
            # Hair
            pygame.draw.rect(screen, DARK_GRAY, (x + 8, y, 12, 6))
            # Body (red shirt)
            pygame.draw.rect(screen, RED_SHIRT, (x + 8, y + 10, 12, 10))
            # Arms (slightly different position)
            pygame.draw.rect(screen, SKIN, (x + 6, y + 12, 4, 8))
            pygame.draw.rect(screen, SKIN, (x + 18, y + 12, 4, 8))
            # Legs (walking position)
            pygame.draw.rect(screen, GRAY_ARMOR, (x + 8, y + 20, 4, 8))
            pygame.draw.rect(screen, GRAY_ARMOR, (x + 16, y + 20, 4, 8))
            # Feet (walking position)
            pygame.draw.rect(screen, DARK_GRAY, (x + 6, y + 26, 4, 2))
            pygame.draw.rect(screen, DARK_GRAY, (x + 18, y + 26, 4, 2))
            # Add a small yellow detail (belt/buckle)
            pygame.draw.rect(screen, YELLOW, (x + 14, y + 16, 2, 2))
    
    def say(self, message, notify_characters=None):
        """Make the character say something"""
        self.speech_text = message
        self.speech_timer = 0
        
        # Notify nearby characters if provided
        if notify_characters:
            self.notify_nearby_characters(message, notify_characters)
    
    def notify_nearby_characters(self, message, characters):
        """Notify nearby characters that this character spoke"""
        hearing_distance = 100  # pixels
        
        for char in characters:
            if char != self:
                # Calculate distance
                dx = char.rect.centerx - self.rect.centerx
                dy = char.rect.centery - self.rect.centery
                distance = math.sqrt(dx*dx + dy*dy)
                
                # If character is close enough and has a reaction method
                if distance <= hearing_distance and hasattr(char, 'react_to_speech'):
                    char.react_to_speech(message, self)
    
    def draw_speech_bubble(self, screen):
        """Draw speech bubble above character"""
        if not self.speech_text:
            return
        
        font = pygame.font.Font(None, 24)
        
        # Split long messages into multiple lines
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
        
        # Calculate bubble dimensions
        line_height = font.get_height()
        bubble_width = max(font.size(line)[0] for line in lines) + 20
        bubble_height = len(lines) * line_height + 20
        
        # Position bubble above character
        bubble_x = self.rect.centerx - bubble_width // 2
        bubble_y = self.rect.top - bubble_height - 10
        
        # Keep bubble on screen
        bubble_x = max(5, min(bubble_x, SCREEN_WIDTH - bubble_width - 5))
        bubble_y = max(5, bubble_y)
        
        # Draw bubble background
        bubble_rect = pygame.Rect(bubble_x, bubble_y, bubble_width, bubble_height)
        pygame.draw.rect(screen, WHITE, bubble_rect)
        pygame.draw.rect(screen, BLACK, bubble_rect, 2)
        
        # Draw speech bubble tail
        tail_points = [
            (self.rect.centerx - 5, bubble_y + bubble_height),
            (self.rect.centerx + 5, bubble_y + bubble_height),
            (self.rect.centerx, bubble_y + bubble_height + 8)
        ]
        pygame.draw.polygon(screen, WHITE, tail_points)
        pygame.draw.polygon(screen, BLACK, tail_points, 2)
        
        # Draw text lines
        for i, line in enumerate(lines):
            text_surface = font.render(line, True, BLACK)
            text_x = bubble_x + 10
            text_y = bubble_y + 10 + i * line_height
            screen.blit(text_surface, (text_x, text_y))
    
    def draw_hud(self, screen):
        """Draw character HUD (name, health bar, inventory)"""
        # HUD positioning - below character
        hud_x = self.rect.x
        hud_y = self.rect.y + self.rect.height + 5  # 5 pixels below character
        hud_width = max(80, len(self.name) * 8)  # Minimum 80px or based on name length
        
        # Colors
        bg_color = (0, 0, 0, 100)  # More transparent black (reduced from 180 to 100)
        border_color = self.hud_color
        text_color = (255, 255, 255)  # White text
        health_bg_color = (100, 100, 100)  # Gray background for health bar
        # Calculate health percentage for color determination
        health_percentage = self.current_health / self.max_health
        health_color = (255, 0, 0) if health_percentage < 0.3 else (255, 255, 0) if health_percentage < 0.6 else (0, 255, 0)
        
        # Create HUD background surface with transparency
        hud_surface = pygame.Surface((hud_width, 40), pygame.SRCALPHA)
        hud_surface.fill(bg_color)
        
        # Draw border
        pygame.draw.rect(hud_surface, border_color, (0, 0, hud_width, 40), 2)
        
        # Draw character name
        font = pygame.font.Font(None, 16)
        name_text = font.render(self.name, True, text_color)
        hud_surface.blit(name_text, (4, 2))
        
        # Draw health bar
        health_bar_width = hud_width - 8
        health_bar_height = 6
        health_bar_y = 16
        
        # Health bar background
        pygame.draw.rect(hud_surface, health_bg_color, (4, health_bar_y, health_bar_width, health_bar_height))
        
        # Health bar fill
        health_fill_width = int(health_bar_width * health_percentage)
        pygame.draw.rect(hud_surface, health_color, (4, health_bar_y, health_fill_width, health_bar_height))
        
        # Health bar border
        pygame.draw.rect(hud_surface, border_color, (4, health_bar_y, health_bar_width, health_bar_height), 1)
        
        # Draw inventory slots
        slot_size = 8
        slot_spacing = 2
        inventory_y = 26
        
        for i in range(3):
            slot_x = 4 + i * (slot_size + slot_spacing)
            slot_rect = (slot_x, inventory_y, slot_size, slot_size)
            
            # Draw slot background
            pygame.draw.rect(hud_surface, (50, 50, 50), slot_rect)
            pygame.draw.rect(hud_surface, border_color, slot_rect, 1)
            
            # Draw item if present (placeholder for now)
            if self.inventory[i] is not None:
                pygame.draw.rect(hud_surface, (200, 200, 0), (slot_x + 1, inventory_y + 1, slot_size - 2, slot_size - 2))
        
        # Blit HUD to screen
        screen.blit(hud_surface, (hud_x, hud_y))
    
    def draw(self, screen):
        self.draw_sprite_frame(screen, self.animation_frame)
        self.draw_speech_bubble(screen)
        self.draw_hud(screen)

class Shopkeeper(Player):
    def __init__(self, x, y):
        super().__init__(x, y)
        self.speed = 2  # Slower than player
        
        # Override HUD properties for NPC
        self.name = "Shopkeeper"
        self.max_health = 80
        self.current_health = 44  # 55% health to test yellow bar
        self.inventory = ["Potion", "Sword", None]  # Sample inventory
        self.hud_color = (0, 100, 255)  # Blue for NPC
        
        # AI behavior variables
        self.ai_timer = 0
        self.ai_action_duration = 2000  # 2 seconds per action
        self.current_action = "idle"
        self.target_x = x
        self.target_y = y
        self.patrol_points = [
            (370, 250),  # Behind counter left
            (420, 250),  # Behind counter right
            (400, 240),  # Behind counter center
        ]
        self.current_patrol_index = 0
        
        # Speech system for AI
        self.speech_timer_ai = 0
        self.speech_interval = 8000  # Speak every 8 seconds
        
        # Reaction system
        self.reaction_delay = 1000  # 1 second delay before reacting
        self.pending_reaction = None
        self.reaction_timer = 0
        
    def ai_update(self, dt, walls, other_characters):
        self.ai_timer += dt
        
        if self.ai_timer >= self.ai_action_duration:
            # Choose new action
            actions = ["idle", "patrol", "wander"]
            self.current_action = random.choice(actions)
            self.ai_timer = 0
            
            if self.current_action == "patrol":
                self.target_x, self.target_y = self.patrol_points[self.current_patrol_index]
                self.current_patrol_index = (self.current_patrol_index + 1) % len(self.patrol_points)
            elif self.current_action == "wander":
                # Wander within shop area
                self.target_x = random.randint(330, 470)
                self.target_y = random.randint(230, 270)
        
        # Execute current action
        if self.current_action == "patrol" or self.current_action == "wander":
            self.move_towards_target(walls, other_characters)
        
        # Update animation
        self.update(dt)
        
        # AI speech system (only if not reacting)
        if not self.pending_reaction:
            self.speech_timer_ai += dt
            if self.speech_timer_ai >= self.speech_interval:
                self.ai_speak()
                self.speech_timer_ai = 0
        
        # Handle pending reactions
        if self.pending_reaction:
            self.reaction_timer += dt
            if self.reaction_timer >= self.reaction_delay:
                self.say(self.pending_reaction)
                self.pending_reaction = None
                self.reaction_timer = 0
    
    def move_towards_target(self, walls, other_characters):
        dx = self.target_x - self.rect.centerx
        dy = self.target_y - self.rect.centery
        
        # Calculate distance
        distance = math.sqrt(dx*dx + dy*dy)
        
        if distance > 5:  # If not close enough to target
            # Normalize movement
            if distance > 0:
                dx = (dx / distance) * self.speed
                dy = (dy / distance) * self.speed
                
                # Move towards target
                self.move(dx, dy, walls, other_characters)
        else:
            # Reached target, stop moving
            self.is_moving = False
    
    def draw_sprite_frame(self, screen, frame):
        # Shopkeeper colors (different from player)
        PURPLE_SHIRT = (128, 0, 128)
        BROWN_APRON = (139, 69, 19)
        SKIN = (255, 220, 177)
        GRAY_HAIR = (128, 128, 128)
        YELLOW = (255, 255, 0)
        
        # Base position
        x, y = self.rect.x, self.rect.y
        
        # Draw shopkeeper based on frame (pixel art style)
        if frame == 0:  # Standing/Frame 1
            # Head
            pygame.draw.rect(screen, SKIN, (x + 10, y + 2, 8, 8))
            # Hair (gray for older shopkeeper)
            pygame.draw.rect(screen, GRAY_HAIR, (x + 8, y, 12, 6))
            # Body (purple shirt)
            pygame.draw.rect(screen, PURPLE_SHIRT, (x + 8, y + 10, 12, 10))
            # Apron
            pygame.draw.rect(screen, BROWN_APRON, (x + 10, y + 12, 8, 8))
            # Arms
            pygame.draw.rect(screen, SKIN, (x + 4, y + 12, 4, 8))
            pygame.draw.rect(screen, SKIN, (x + 20, y + 12, 4, 8))
            # Legs
            pygame.draw.rect(screen, BROWN_APRON, (x + 10, y + 20, 8, 8))
            # Feet
            pygame.draw.rect(screen, GRAY_HAIR, (x + 8, y + 26, 4, 2))
            pygame.draw.rect(screen, GRAY_HAIR, (x + 16, y + 26, 4, 2))
        else:  # Walking frame 2
            # Head
            pygame.draw.rect(screen, SKIN, (x + 10, y + 2, 8, 8))
            # Hair
            pygame.draw.rect(screen, GRAY_HAIR, (x + 8, y, 12, 6))
            # Body (purple shirt)
            pygame.draw.rect(screen, PURPLE_SHIRT, (x + 8, y + 10, 12, 10))
            # Apron
            pygame.draw.rect(screen, BROWN_APRON, (x + 10, y + 12, 8, 8))
            # Arms (slightly different position)
            pygame.draw.rect(screen, SKIN, (x + 6, y + 12, 4, 8))
            pygame.draw.rect(screen, SKIN, (x + 18, y + 12, 4, 8))
            # Legs (walking position)
            pygame.draw.rect(screen, BROWN_APRON, (x + 8, y + 20, 4, 8))
            pygame.draw.rect(screen, BROWN_APRON, (x + 16, y + 20, 4, 8))
            # Feet (walking position)
            pygame.draw.rect(screen, GRAY_HAIR, (x + 6, y + 26, 4, 2))
            pygame.draw.rect(screen, GRAY_HAIR, (x + 18, y + 26, 4, 2))
            # Add a small yellow detail (apron tie)
            pygame.draw.rect(screen, YELLOW, (x + 14, y + 16, 2, 2))
    
    def ai_speak(self):
        """AI method for shopkeeper to say random things"""
        messages = [
            "Welcome to my shop!",
            "Best equipment in town!",
            "Looking for something special?",
            "Fresh stock just arrived!",
            "Quality gear at fair prices!",
            "Come back anytime!",
            "I have what you need!"
        ]
        message = random.choice(messages)
        self.say(message)
    
    def react_to_speech(self, message, speaker):
        """React to what another character said"""
        # Don't react if already speaking or have a pending reaction
        if self.speech_text or self.pending_reaction:
            return
        
        message_lower = message.lower()
        
        # Greeting responses
        if any(word in message_lower for word in ['hello', 'hi', 'hey', 'greetings']):
            responses = [
                "Hello there, traveler!",
                "Greetings! Welcome to my shop!",
                "Well hello! How can I help you?",
                "Good day to you!"
            ]
        
        # Shop-related responses
        elif any(word in message_lower for word in ['shop', 'buy', 'sell', 'equipment', 'gear', 'weapon', 'armor']):
            responses = [
                "Ah, interested in my wares?",
                "I have the finest equipment!",
                "Looking to upgrade your gear?",
                "You've come to the right place!",
                "I have just what you need!"
            ]
        
        # Price/money responses
        elif any(word in message_lower for word in ['price', 'cost', 'money', 'gold', 'cheap', 'expensive']):
            responses = [
                "My prices are very fair!",
                "Quality costs, but it's worth it!",
                "I offer the best value in town!",
                "You get what you pay for!"
            ]
        
        # Compliment responses
        elif any(word in message_lower for word in ['good', 'great', 'nice', 'excellent', 'amazing', 'wonderful']):
            responses = [
                "Why thank you!",
                "You're too kind!",
                "I appreciate that!",
                "That means a lot!"
            ]
        
        # Question responses
        elif '?' in message:
            responses = [
                "Hmm, let me think about that...",
                "That's a good question!",
                "I'm not sure about that.",
                "Interesting question!"
            ]
        
        # Goodbye responses
        elif any(word in message_lower for word in ['bye', 'goodbye', 'farewell', 'see you', 'later']):
            responses = [
                "Farewell, friend!",
                "Come back soon!",
                "Safe travels!",
                "Until next time!"
            ]
        
        # Default responses for anything else
        else:
            responses = [
                "Is that so?",
                "Interesting...",
                "I see.",
                "Hmm, indeed.",
                "You don't say!",
                "That's something to consider.",
                "Quite right!"
            ]
        
        # Set a random response with delay
        self.pending_reaction = random.choice(responses)
        self.reaction_timer = 0

class Shop:
    def __init__(self):
        # Shop walls (outer walls with entrance gap) - Half thickness (10px instead of 20px)
        self.walls = [
            # Top wall
            pygame.Rect(300, 200, 200, 10),
            # Bottom wall - LEFT part (before entrance)
            pygame.Rect(300, 390, 80, 10),
            # Bottom wall - RIGHT part (after entrance)  
            pygame.Rect(420, 390, 80, 10),
            # Left wall
            pygame.Rect(300, 200, 10, 200),
            # Right wall
            pygame.Rect(490, 200, 10, 200),
            # Counter in middle
            pygame.Rect(360, 280, 80, 40)
        ]
        
        # Shop entrance (gap in bottom wall)
        self.entrance = pygame.Rect(380, 390, 40, 10)
        
        # Interaction zone (in front of counter)
        self.interact_zone = pygame.Rect(360, 320, 80, 20)
        
        # Floor area for wooden texture
        self.floor_area = pygame.Rect(310, 210, 180, 180)
        
    def draw_wooden_floor(self, screen):
        """Draw wooden plank flooring with alternating seams - 10x more detailed"""
        # Wooden plank colors
        WOOD_LIGHT = (160, 120, 80)
        WOOD_DARK = (140, 100, 60)
        WOOD_SEAM = (120, 80, 40)
        
        plank_height = 3  # Height of each plank row (5x smaller: 16/5 = 3.2 ≈ 3)
        plank_width = 12  # Width of individual planks (5x smaller: 60/5 = 12)
        
        # Draw planks row by row
        for row in range(self.floor_area.height // plank_height + 1):
            y = self.floor_area.y + row * plank_height
            
            # Alternate the starting offset every two rows for realistic wood pattern
            offset = (plank_width // 2) if (row // 2) % 2 == 1 else 0
            
            # Draw planks in this row
            x = self.floor_area.x - offset
            while x < self.floor_area.right:
                # Determine plank color (alternate between light and dark)
                plank_color = WOOD_LIGHT if (x // plank_width) % 2 == 0 else WOOD_DARK
                
                # Create plank rectangle, clipped to floor area
                plank_rect = pygame.Rect(x, y, plank_width, plank_height)
                clipped_rect = plank_rect.clip(self.floor_area)
                
                if clipped_rect.width > 0 and clipped_rect.height > 0:
                    pygame.draw.rect(screen, plank_color, clipped_rect)
                    
                    # Draw vertical seam lines between planks (only every other plank)
                    if (x // plank_width) % 2 == 0 and x + plank_width < self.floor_area.right and clipped_rect.height > 0:
                        seam_x = x + plank_width
                        if seam_x >= self.floor_area.x and seam_x < self.floor_area.right:
                            pygame.draw.line(screen, WOOD_SEAM, 
                                           (seam_x, clipped_rect.top), 
                                           (seam_x, clipped_rect.bottom), 1)
                
                x += plank_width
            
            # Draw horizontal seam line between rows (every other row)
            if row % 2 == 0 and y + plank_height < self.floor_area.bottom:
                pygame.draw.line(screen, WOOD_SEAM, 
                               (self.floor_area.left, y + plank_height), 
                               (self.floor_area.right, y + plank_height), 1)
        
    def draw(self, screen):
        # Draw wooden floor first (underneath everything)
        self.draw_wooden_floor(screen)
        
        # Draw walls
        for wall in self.walls:
            if wall == self.walls[-1]:  # Counter
                pygame.draw.rect(screen, BROWN, wall)
            else:
                pygame.draw.rect(screen, GRAY, wall)
        
        # Draw entrance (remove part of bottom wall)
        pygame.draw.rect(screen, GREEN, self.entrance)
        
        # Draw interaction indicator
        pygame.draw.rect(screen, YELLOW, self.interact_zone, 2)

class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Zelda-style Game")
        self.clock = pygame.time.Clock()
        
        # Game objects
        self.player = Player(400, 450)
        self.shopkeeper = Shopkeeper(400, 250)  # Start behind counter
        self.shop = Shop()
        self.characters = [self.player, self.shopkeeper]
        
        # Game state
        self.running = True
        self.show_shop_message = False
        
        # Text input system
        self.text_input_active = False
        self.input_text = ""
        self.input_prompt = "What would you like to say? (Press Enter to send, Escape to cancel)"
        
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if self.text_input_active:
                    # Handle text input
                    if event.key == pygame.K_RETURN:
                        if self.input_text.strip():
                            self.player.say(self.input_text.strip(), self.characters)
                        self.text_input_active = False
                        self.input_text = ""
                    elif event.key == pygame.K_ESCAPE:
                        self.text_input_active = False
                        self.input_text = ""
                    elif event.key == pygame.K_BACKSPACE:
                        self.input_text = self.input_text[:-1]
                    else:
                        # Add character to input
                        if len(self.input_text) < 100:  # Limit message length
                            self.input_text += event.unicode
                else:
                    # Normal game controls
                    if event.key == pygame.K_SPACE:
                        self.interact()
                    elif event.key == pygame.K_RETURN:
                        self.text_input_active = True
                        self.input_text = ""
    
    def interact(self):
        # Check if player is in interaction zone
        if self.player.rect.colliderect(self.shop.interact_zone):
            self.show_shop_message = True
        else:
            self.show_shop_message = False
    
    def update(self):
        # Get delta time for animation
        dt = self.clock.get_time()
        
        # Only handle movement if not typing
        if not self.text_input_active:
            # Handle continuous key presses for movement
            keys = pygame.key.get_pressed()
            dx, dy = 0, 0
            
            if keys[pygame.K_LEFT]:
                dx = -self.player.speed
            if keys[pygame.K_RIGHT]:
                dx = self.player.speed
            if keys[pygame.K_UP]:
                dy = -self.player.speed
            if keys[pygame.K_DOWN]:
                dy = self.player.speed
            
            # Reset movement state
            self.player.is_moving = False
            
            # Move player
            if dx != 0 or dy != 0:
                self.player.move(dx, dy, self.shop.walls, self.characters)
        
        # Update player animation
        self.player.update(dt)
        
        # Update shopkeeper AI
        self.shopkeeper.ai_update(dt, self.shop.walls, self.characters)
    
    def draw(self):
        # Clear screen with grass color
        self.screen.fill(GREEN)
        
        # Draw shop
        self.shop.draw(self.screen)
        
        # Draw characters
        self.player.draw(self.screen)
        self.shopkeeper.draw(self.screen)
        
        # Draw UI
        if self.show_shop_message:
            font = pygame.font.Font(None, 36)
            text = font.render("Welcome to the Equipment Shop!", True, WHITE)
            text_rect = text.get_rect(center=(SCREEN_WIDTH // 2, 100))
            pygame.draw.rect(self.screen, BLACK, text_rect.inflate(20, 10))
            self.screen.blit(text, text_rect)
        
        # Draw text input interface
        if self.text_input_active:
            self.draw_text_input()
        
        # Draw instructions
        font = pygame.font.Font(None, 24)
        instructions = [
            "Arrow Keys: Move",
            "Space: Interact (when near counter)",
            "Enter: Say something"
        ]
        for i, instruction in enumerate(instructions):
            text = font.render(instruction, True, WHITE)
            self.screen.blit(text, (10, 10 + i * 25))
        
        pygame.display.flip()
    
    def draw_text_input(self):
        """Draw the text input interface"""
        # Draw semi-transparent overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(128)
        overlay.fill(BLACK)
        self.screen.blit(overlay, (0, 0))
        
        # Draw input box
        box_width = 500
        box_height = 100
        box_x = (SCREEN_WIDTH - box_width) // 2
        box_y = (SCREEN_HEIGHT - box_height) // 2
        
        input_rect = pygame.Rect(box_x, box_y, box_width, box_height)
        pygame.draw.rect(self.screen, WHITE, input_rect)
        pygame.draw.rect(self.screen, BLACK, input_rect, 3)
        
        # Draw prompt
        font = pygame.font.Font(None, 24)
        prompt_surface = font.render(self.input_prompt, True, BLACK)
        prompt_rect = prompt_surface.get_rect(centerx=input_rect.centerx, y=input_rect.y + 10)
        self.screen.blit(prompt_surface, prompt_rect)
        
        # Draw input text
        input_font = pygame.font.Font(None, 32)
        display_text = self.input_text + "|"  # Add cursor
        text_surface = input_font.render(display_text, True, BLACK)
        text_rect = text_surface.get_rect(x=input_rect.x + 10, centery=input_rect.centery + 10)
        
        # Clip text if too long
        if text_rect.width > box_width - 20:
            # Show only the end of the text
            while text_rect.width > box_width - 20 and len(display_text) > 1:
                display_text = display_text[1:]
                text_surface = input_font.render(display_text, True, BLACK)
                text_rect = text_surface.get_rect(x=input_rect.x + 10, centery=input_rect.centery + 10)
        
        self.screen.blit(text_surface, text_rect)
    
    def run(self):
        while self.running:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)
        
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = Game()
    game.run()