"""
Modified version of the Zelda game with LLM-driven NPC integration.
This shows the minimal changes needed to integrate the LLM NPC system.
"""

# Import the original game components
import pygame
import sys
import random
import math
import requests
import json
import threading
from queue import Queue
import time

# Import the new LLM NPC system
from zelda_game_llm_integration import LLMDrivenNPC, create_llm_shopkeeper

# Copy the essential classes from the original game
# (In practice, you'd modify the original file directly)

# Initialize Pygame
pygame.init()

# Constants (same as original)
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
TILE_SIZE = 32
FPS = 60

# Colors (same as original)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREEN = (0, 128, 0)
BROWN = (139, 69, 19)
GRAY = (128, 128, 128)
BLUE = (0, 0, 255)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)

# Simplified Player class for demo
class Player:
    def __init__(self, x, y, name="Player"):
        self.x = x
        self.y = y
        self.width = TILE_SIZE - 4
        self.height = TILE_SIZE - 4
        self.speed = 4
        self.rect = pygame.Rect(x, y, self.width, self.height)
        self.name = name
        self.character_type = "player"
        
        # Animation
        self.is_moving = False
        self.animation_frame = 0
        self.animation_timer = 0
        self.animation_speed = 200
        
        # Speech
        self.speech_text = ""
        self.speech_timer = 0
        self.speech_duration = 3000
        
        # Stats
        self.current_health = 100
        self.max_health = 100
        self.inventory_size = 6
        self.inventory = [None] * self.inventory_size
        self.gold = 100
        
        # Visual
        self.hud_color = (0, 255, 0)
        self.show_inventory = False
        
        # Colors
        self.shirt_color = (200, 50, 50)
        self.hair_color = (80, 80, 80)
        self.skin_color = (255, 220, 177)
        self.pants_color = (150, 150, 150)
    
    def move(self, dx, dy, walls, other_characters=None):
        moved = False
        
        # Try X movement first
        if dx != 0:
            new_rect_x = self.rect.copy()
            new_rect_x.x += dx
            
            x_valid = new_rect_x.left >= 0 and new_rect_x.right <= SCREEN_WIDTH
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
            
            y_valid = new_rect_y.top >= 0 and new_rect_y.bottom <= SCREEN_HEIGHT
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
    
    def update(self, dt):
        if self.is_moving:
            self.animation_timer += dt
            if self.animation_timer >= self.animation_speed:
                self.animation_frame = (self.animation_frame + 1) % 2
                self.animation_timer = 0
        else:
            self.animation_frame = 0
            self.animation_timer = 0
        
        if self.speech_text:
            self.speech_timer += dt
            if self.speech_timer >= self.speech_duration:
                self.speech_text = ""
                self.speech_timer = 0
    
    def say(self, message, notify_characters=None):
        print(f"DEBUG: {self.name} saying: '{message}'")
        self.speech_text = message
        self.speech_timer = 0
        
        if notify_characters:
            self.notify_nearby_characters(message, notify_characters)
    
    def notify_nearby_characters(self, message, characters):
        hearing_distance = 300
        
        for char in characters:
            if char != self:
                dx = char.rect.centerx - self.rect.centerx
                dy = char.rect.centery - self.rect.centery
                distance = math.sqrt(dx*dx + dy*dy)
                
                if distance <= hearing_distance and hasattr(char, 'react_to_speech'):
                    char.react_to_speech(message, self)
    
    def draw_sprite_frame(self, screen, frame):
        x, y = self.rect.x, self.rect.y
        
        if frame == 0:  # Standing
            pygame.draw.rect(screen, self.skin_color, (x + 10, y + 2, 8, 8))
            pygame.draw.rect(screen, self.hair_color, (x + 8, y, 12, 6))
            pygame.draw.rect(screen, self.shirt_color, (x + 8, y + 10, 12, 10))
            pygame.draw.rect(screen, self.skin_color, (x + 4, y + 12, 4, 8))
            pygame.draw.rect(screen, self.skin_color, (x + 20, y + 12, 4, 8))
            pygame.draw.rect(screen, self.pants_color, (x + 10, y + 20, 8, 8))
            pygame.draw.rect(screen, self.hair_color, (x + 8, y + 26, 4, 2))
            pygame.draw.rect(screen, self.hair_color, (x + 16, y + 26, 4, 2))
        else:  # Walking
            pygame.draw.rect(screen, self.skin_color, (x + 10, y + 2, 8, 8))
            pygame.draw.rect(screen, self.hair_color, (x + 8, y, 12, 6))
            pygame.draw.rect(screen, self.shirt_color, (x + 8, y + 10, 12, 10))
            pygame.draw.rect(screen, self.skin_color, (x + 6, y + 12, 4, 8))
            pygame.draw.rect(screen, self.skin_color, (x + 18, y + 12, 4, 8))
            pygame.draw.rect(screen, self.pants_color, (x + 8, y + 20, 4, 8))
            pygame.draw.rect(screen, self.pants_color, (x + 16, y + 20, 4, 8))
            pygame.draw.rect(screen, self.hair_color, (x + 6, y + 26, 4, 2))
            pygame.draw.rect(screen, self.hair_color, (x + 18, y + 26, 4, 2))
    
    def draw_speech_bubble(self, screen):
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
        
        bubble_x = max(5, min(bubble_x, SCREEN_WIDTH - bubble_width - 5))
        bubble_y = max(5, bubble_y)
        
        bubble_rect = pygame.Rect(bubble_x, bubble_y, bubble_width, bubble_height)
        pygame.draw.rect(screen, WHITE, bubble_rect)
        pygame.draw.rect(screen, BLACK, bubble_rect, 2)
        
        tail_points = [
            (self.rect.centerx - 5, bubble_y + bubble_height),
            (self.rect.centerx + 5, bubble_y + bubble_height),
            (self.rect.centerx, bubble_y + bubble_height + 8)
        ]
        pygame.draw.polygon(screen, WHITE, tail_points)
        pygame.draw.polygon(screen, BLACK, tail_points, 2)
        
        for i, line in enumerate(lines):
            text_surface = font.render(line, True, BLACK)
            text_x = bubble_x + 10
            text_y = bubble_y + 10 + i * line_height
            screen.blit(text_surface, (text_x, text_y))
    
    def draw(self, screen):
        self.draw_sprite_frame(screen, self.animation_frame)
        self.draw_speech_bubble(screen)

# Simplified Shop class
class Shop:
    def __init__(self):
        self.walls = [
            pygame.Rect(300, 200, 200, 10),  # Top wall
            pygame.Rect(300, 390, 80, 10),   # Bottom left
            pygame.Rect(420, 390, 80, 10),   # Bottom right
            pygame.Rect(300, 200, 10, 190),  # Left wall
            pygame.Rect(490, 200, 10, 190),  # Right wall
        ]
        
        self.counter = pygame.Rect(350, 240, 100, 20)
        self.interact_zone = pygame.Rect(350, 260, 100, 40)
        self.floor_area = pygame.Rect(310, 210, 180, 180)
    
    def draw_wooden_floor(self, screen):
        plank_height = 12
        plank_width = 60
        colors = [(180, 120, 80), (200, 140, 100), (220, 180, 120)]
        seam_color = (150, 110, 70)
        
        for row_index, y in enumerate(range(self.floor_area.top, self.floor_area.bottom, plank_height)):
            offset = (plank_width // 2) if row_index % 2 == 1 else 0
            x = self.floor_area.left - offset
            plank_count = 0
            
            while x < self.floor_area.right:
                random.seed(row_index * 1000 + plank_count)
                color = random.choice(colors)
                random.seed()
                
                plank_rect = pygame.Rect(x, y, plank_width, plank_height)
                clipped_rect = plank_rect.clip(self.floor_area)
                
                if clipped_rect.width > 0 and clipped_rect.height > 0:
                    pygame.draw.rect(screen, color, clipped_rect)
                    
                    seam_x = x + plank_width
                    if (seam_x >= self.floor_area.left and seam_x < self.floor_area.right and 
                        clipped_rect.height > 0):
                        pygame.draw.line(screen, seam_color, 
                                       (seam_x, clipped_rect.top), 
                                       (seam_x, clipped_rect.bottom), 1)
                
                x += plank_width
                plank_count += 1
            
            if y + plank_height < self.floor_area.bottom:
                pygame.draw.line(screen, seam_color, 
                               (self.floor_area.left, y + plank_height), 
                               (self.floor_area.right, y + plank_height), 1)
    
    def draw(self, screen):
        self.draw_wooden_floor(screen)
        
        for wall in self.walls:
            pygame.draw.rect(screen, BROWN, wall)
        
        pygame.draw.rect(screen, BROWN, self.counter)
        pygame.draw.rect(screen, BLACK, self.counter, 2)

# Modified Game class with LLM NPC integration
class GameWithLLMNPC:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Zelda-style RPG with LLM-driven NPC")
        self.clock = pygame.time.Clock()
        self.running = True
        
        # Game objects
        self.player = Player(400, 450)
        self.shop = Shop()
        
        # *** KEY CHANGE: Use LLM-driven shopkeeper instead of regular NPC ***
        self.shopkeeper = create_llm_shopkeeper(400, 250)
        
        # Configure NPC behavior - only respond when spoken to
        self.shopkeeper.llm_controller.enable_idle_behavior(False)
        
        # *** NEW: Initialize hierarchical navigation system ***
        grid_width = SCREEN_WIDTH // TILE_SIZE  # 25 tiles
        grid_height = SCREEN_HEIGHT // TILE_SIZE  # 18 tiles
        self.shopkeeper.llm_controller.initialize_navigation(grid_width, grid_height, self.shop.walls)
        print(f"Navigation system initialized for {grid_width}x{grid_height} grid")
        
        self.characters = [self.player, self.shopkeeper]
        
        # Game state
        self.show_shop_message = False
        self.text_input_active = False
        self.input_text = ""
        self.input_prompt = "What would you like to say? (Press Enter to send, Escape to cancel)"
    
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if self.text_input_active:
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
                        if len(self.input_text) < 100:
                            self.input_text += event.unicode
                else:
                    if event.key == pygame.K_SPACE:
                        self.interact()
                    elif event.key == pygame.K_RETURN:
                        self.text_input_active = True
                        self.input_text = ""
                    elif event.key == pygame.K_t:  # Toggle idle behavior
                        current_idle = self.shopkeeper.llm_controller.idle_behavior_enabled
                        self.shopkeeper.llm_controller.enable_idle_behavior(not current_idle, 0.2)
                        print(f"Idle behavior: {'ON' if not current_idle else 'OFF'}")
    
    def interact(self):
        if self.player.rect.colliderect(self.shop.interact_zone):
            self.show_shop_message = True
        else:
            self.show_shop_message = False
    
    def update(self):
        dt = self.clock.get_time()
        
        if not self.text_input_active:
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
            
            self.player.is_moving = False
            
            if dx != 0 or dy != 0:
                self.player.move(dx, dy, self.shop.walls, self.characters)
        
        self.player.update(dt)
        
        # *** KEY CHANGE: Update LLM-driven NPC ***
        self.shopkeeper.update(dt, self.shop.walls, self.characters, self.player)
    
    def draw(self):
        self.screen.fill(GREEN)
        
        self.shop.draw(self.screen)
        
        self.player.draw(self.screen)
        self.shopkeeper.draw(self.screen)
        
        if self.show_shop_message:
            font = pygame.font.Font(None, 36)
            text = font.render("Welcome to the Equipment Shop!", True, WHITE)
            text_rect = text.get_rect(center=(SCREEN_WIDTH // 2, 100))
            pygame.draw.rect(self.screen, BLACK, text_rect.inflate(20, 10))
            self.screen.blit(text, text_rect)
        
        if self.text_input_active:
            self.draw_text_input()
        
        # Instructions
        font = pygame.font.Font(None, 24)
        instructions = [
            "Arrow Keys: Move",
            "Space: Interact (when near counter)",
            "Enter: Say something to the LLM-driven shopkeeper",
            "T: Toggle NPC idle behavior (thinking out loud)",
            "ESC: Quit"
        ]
        for i, instruction in enumerate(instructions):
            text = font.render(instruction, True, WHITE)
            self.screen.blit(text, (10, 10 + i * 25))
        
        # LLM Status
        llm_status = "LLM NPC: Active" if self.shopkeeper.llm_controller else "LLM NPC: Disabled"
        status_color = GREEN if self.shopkeeper.llm_controller else RED
        status_text = font.render(llm_status, True, status_color)
        self.screen.blit(status_text, (10, SCREEN_HEIGHT - 30))
        
        pygame.display.flip()
    
    def draw_text_input(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(128)
        overlay.fill(BLACK)
        self.screen.blit(overlay, (0, 0))
        
        input_width = 600
        input_height = 100
        input_x = (SCREEN_WIDTH - input_width) // 2
        input_y = (SCREEN_HEIGHT - input_height) // 2
        
        pygame.draw.rect(self.screen, WHITE, (input_x, input_y, input_width, input_height))
        pygame.draw.rect(self.screen, BLACK, (input_x, input_y, input_width, input_height), 3)
        
        font = pygame.font.Font(None, 24)
        prompt_text = font.render(self.input_prompt, True, BLACK)
        self.screen.blit(prompt_text, (input_x + 10, input_y + 10))
        
        input_text = font.render(self.input_text + "|", True, BLACK)
        self.screen.blit(input_text, (input_x + 10, input_y + 40))
    
    def run(self):
        print("Starting Zelda game with LLM-driven NPC...")
        print("Make sure your local LLM server is running at http://127.0.0.1:1234")
        
        # Show LLM configuration
        from llm_config import print_config_info
        print_config_info()
        
        print("Walk near the shopkeeper and press Enter to talk!")
        
        while self.running:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)
        
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = GameWithLLMNPC()
    game.run()