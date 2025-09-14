import pygame
import sys
import random
import math
import requests
import json
import threading
from queue import Queue

# Initialize Pygame
pygame.init()

class Item:
    def __init__(self, item_id, item_data):
        self.id = item_id
        self.name = item_data["name"]
        self.type = item_data["type"]
        self.value = item_data["value"]
        self.description = item_data["description"]
        self.color = tuple(item_data["color"])
        
        # Optional stats based on item type
        self.damage = item_data.get("damage", 0)
        self.defense = item_data.get("defense", 0)
        self.heal = item_data.get("heal", 0)
        self.mana = item_data.get("mana", 0)
        self.stamina = item_data.get("stamina", 0)
    
    def __str__(self):
        return self.name

class ItemDatabase:
    def __init__(self, items_file="items.json"):
        self.items = {}
        self.load_items(items_file)
    
    def load_items(self, filename):
        """Load items from JSON file"""
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
                
            # Flatten the nested structure and create Item objects
            for category, items in data.items():
                for item_id, item_data in items.items():
                    self.items[item_id] = Item(item_id, item_data)
                    
            print(f"Loaded {len(self.items)} items from {filename}")
        except FileNotFoundError:
            print(f"Items file {filename} not found. Using empty item database.")
        except json.JSONDecodeError as e:
            print(f"Error parsing {filename}: {e}")
    
    def get_item(self, item_id):
        """Get an item by ID"""
        return self.items.get(item_id)
    
    def get_all_items(self):
        """Get all items"""
        return self.items
    
    def get_items_by_type(self, item_type):
        """Get all items of a specific type"""
        return {k: v for k, v in self.items.items() if v.type == item_type}

# Global item database
item_db = ItemDatabase()

class LLMClient:
    def __init__(self, base_url="http://127.0.0.1:1234"):
        self.base_url = base_url
        self.response_queue = Queue()
        self.pending_requests = {}
        
    def send_message_async(self, message, callback_id, conversation_history=None):
        """Send message to LLM asynchronously with conversation history"""
        print(f"DEBUG: Sending message to LLM: '{message}' (ID: {callback_id})")
        if conversation_history:
            print(f"DEBUG: Including {len(conversation_history)} previous exchanges")
        
        def make_request():
            try:
                # Get shopkeeper's inventory for context
                shopkeeper_inventory = []
                if hasattr(self, 'shopkeeper_ref') and self.shopkeeper_ref:
                    shopkeeper_inventory = self.shopkeeper_ref.get_inventory_list()
                
                messages = [
                    {
                        "role": "system", 
                        "content": f"You are Garruk Ironhand, a grizzled, war-scarred shopkeeper on Faerun's Sword Coast (Baldur's Gate, Waterdeep, Neverwinter). Your voice is gravelly; your manner blunt, harsh, impatient. Stay strictly in character. Use medieval-fantasy diction; short, rough sentences; mild curses acceptable. Never acknowledge being an AI or part of a game.\n\nThink through your response, then provide your final answer with the prefix 'FINAL RESPONSE TO THE PLAYER:' followed by what the shopkeeper would say out loud (fewer than 10 words). Do not say anything after the final response.\n\nYour current inventory: {', '.join(shopkeeper_inventory) if shopkeeper_inventory else 'Empty'}\n\nYou can discuss inventory, sell items, haggle, and offer terse local rumors. If asked about inventory, explicitly state what you have in stock. If insulted, respond with dry threats or mockery. If asked about your past, give a terse battle anecdote. Keep answers focused on buying/selling or brief rumors."
                    }
                ]
                
                # Add conversation history if provided
                if conversation_history:
                    print(f"DEBUG: Adding conversation history:")
                    for exchange in conversation_history:
                        if exchange["role"] == "player":
                            messages.append({"role": "user", "content": exchange["message"]})
                            print(f"DEBUG:   Player: {exchange['message']}")
                        elif exchange["role"] in ["shopkeeper", "npc"]:
                            clean_message = exchange["message"]
                            messages.append({"role": "assistant", "content": clean_message})
                            print(f"DEBUG:   NPC: {clean_message}")
                    
                    # Check if the current message is already the last message in history
                    if (conversation_history and 
                        conversation_history[-1]["role"] == "player" and 
                        conversation_history[-1]["message"] == message):
                        print(f"DEBUG: Current message already in history, not adding again")
                    else:
                        messages.append({"role": "user", "content": message})
                        print(f"DEBUG: Adding current message: {message}")
                else:
                    messages.append({"role": "user", "content": message})
                
                payload = {
                    "messages": messages,
                    "temperature": 0.2
                }
                
                endpoint = "/v1/chat/completions"
                timeout = 30 if conversation_history and len(conversation_history) > 3 else 15
                
                response = requests.post(
                    f"{self.base_url}{endpoint}",
                    json=payload,
                    timeout=timeout,
                    headers={"Content-Type": "application/json"}
                )
                
                if response and response.status_code == 200:
                    data = response.json()
                    if "choices" in data and len(data["choices"]) > 0:
                        if "message" in data["choices"][0]:
                            ai_response = data["choices"][0]["message"]["content"].strip()
                        else:
                            ai_response = "I'm not sure what to say about that."
                    else:
                        ai_response = "Hmm, let me think about that..."
                    
                    print(f"DEBUG: Raw LLM response: '{ai_response}'")
                    
                    # Extract content after "FINAL RESPONSE TO THE PLAYER:"
                    if "FINAL RESPONSE TO THE PLAYER:" in ai_response:
                        parts = ai_response.split("FINAL RESPONSE TO THE PLAYER:")
                        if len(parts) > 1:
                            ai_response = parts[-1].strip()
                            print(f"DEBUG: Extracted final response: '{ai_response}'")
                    
                    # Clean up response
                    lines = ai_response.split('\n')
                    cleaned_lines = []
                    for line in lines:
                        line = line.strip()
                        if not any(line.lower().startswith(pattern) for pattern in [
                            'thinking:', 'note:', 'mental note:', 'remember:', 'as a', 'i should',
                            'the user', 'keeping it', 'this is', 'must remember'
                        ]):
                            cleaned_lines.append(line)
                    
                    ai_response = ' '.join(cleaned_lines).strip()
                    ai_response = ' '.join(ai_response.split())
                    
                    if ai_response and len(ai_response) > 3:
                        words = ai_response.split()
                        if len(words) > 15:
                            ai_response = ' '.join(words[:15])
                            if not ai_response.endswith(('.', '!', '?')):
                                ai_response += "!"
                        
                        if not ai_response.endswith(('.', '!', '?')):
                            ai_response += "!"
                    else:
                        ai_response = "What can I help you with?"
                    
                    print(f"DEBUG: Cleaned AI response: '{ai_response}'")
                else:
                    ai_response = "Sorry, I'm having trouble thinking right now."
                    
            except Exception as e:
                print(f"LLM request failed: {e}")
                ai_response = "I'm a bit distracted right now."
            
            self.response_queue.put((callback_id, ai_response))
        
        thread = threading.Thread(target=make_request)
        thread.daemon = True
        thread.start()
    
    def get_responses(self):
        """Get any completed responses"""
        responses = []
        while not self.response_queue.empty():
            responses.append(self.response_queue.get())
        return responses

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

class Character:
    """Base class for all characters (players and NPCs)"""
    def __init__(self, x, y, name="Character", character_type="generic"):
        # Position and physics
        self.x = x
        self.y = y
        self.width = TILE_SIZE - 4
        self.height = TILE_SIZE - 4
        self.speed = 4
        self.rect = pygame.Rect(x, y, self.width, self.height)
        
        # Character identity
        self.name = name
        self.character_type = character_type
        
        # Animation variables
        self.is_moving = False
        self.animation_frame = 0
        self.animation_timer = 0
        self.animation_speed = 200
        
        # Speech system
        self.speech_text = ""
        self.speech_timer = 0
        self.speech_duration = 3000
        
        # Stats system
        self.max_health = 100
        self.current_health = 100
        self.inventory_size = 6
        self.inventory = [None] * self.inventory_size
        self.gold = 100
        
        # Visual system
        self.hud_color = (255, 255, 255)
        self.show_inventory = False
        
        # Character appearance colors
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
    
    def add_item(self, item_id, quantity=1):
        """Add an item to inventory"""
        if isinstance(item_id, str):
            item = item_db.get_item(item_id)
            if not item:
                print(f"Item {item_id} not found in database")
                return False
        else:
            item = item_id
        
        for i in range(self.inventory_size):
            if self.inventory[i] is None:
                self.inventory[i] = {"item": item, "quantity": quantity}
                print(f"Added {quantity}x {item.name} to {self.name}'s inventory")
                return True
        
        print(f"{self.name}'s inventory is full!")
        return False
    
    def remove_item(self, item_id, quantity=1):
        """Remove an item from inventory"""
        for i in range(self.inventory_size):
            if (self.inventory[i] and 
                self.inventory[i]["item"].id == item_id):
                
                if self.inventory[i]["quantity"] <= quantity:
                    removed_item = self.inventory[i]
                    self.inventory[i] = None
                    return removed_item["quantity"]
                else:
                    self.inventory[i]["quantity"] -= quantity
                    return quantity
        return 0
    
    def has_item(self, item_id):
        """Check if character has an item"""
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
    
    def use_item(self, slot_index):
        """Use an item from inventory"""
        if 0 <= slot_index < self.inventory_size and self.inventory[slot_index]:
            item_slot = self.inventory[slot_index]
            item = item_slot["item"]
            
            if item.type == "consumable":
                if item.heal > 0:
                    old_health = self.current_health
                    self.current_health = min(self.max_health, self.current_health + item.heal)
                    healed = self.current_health - old_health
                    self.say(f"Used {item.name}! Healed {healed} HP")
                
                if item_slot["quantity"] <= 1:
                    self.inventory[slot_index] = None
                else:
                    item_slot["quantity"] -= 1
                
                return True
            else:
                self.say(f"Can't use {item.name} right now")
                return False
        return False
    
    def say(self, message, notify_characters=None):
        """Make the character say something"""
        print(f"DEBUG: {self.name} saying: '{message}'")
        self.speech_text = message
        self.speech_timer = 0
        
        if notify_characters:
            self.notify_nearby_characters(message, notify_characters)
    
    def notify_nearby_characters(self, message, characters):
        """Notify nearby characters that this character spoke"""
        hearing_distance = 300
        
        for char in characters:
            if char != self:
                dx = char.rect.centerx - self.rect.centerx
                dy = char.rect.centery - self.rect.centery
                distance = math.sqrt(dx*dx + dy*dy)
                
                if distance <= hearing_distance and hasattr(char, 'react_to_speech'):
                    char.react_to_speech(message, self)
    
    def draw_sprite_frame(self, screen, frame):
        """Draw character sprite"""
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
        """Draw speech bubble above character"""
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
    
    def draw_hud(self, screen):
        """Draw character HUD"""
        hud_x = self.rect.x
        hud_y = self.rect.y + self.rect.height + 5
        hud_width = max(80, len(self.name) * 8)
        
        bg_color = (0, 0, 0, 100)
        border_color = self.hud_color
        text_color = (255, 255, 255)
        health_bg_color = (100, 100, 100)
        health_percentage = self.current_health / self.max_health
        health_color = (255, 0, 0) if health_percentage < 0.3 else (255, 255, 0) if health_percentage < 0.6 else (0, 255, 0)
        
        hud_surface = pygame.Surface((hud_width, 40), pygame.SRCALPHA)
        hud_surface.fill(bg_color)
        
        pygame.draw.rect(hud_surface, border_color, (0, 0, hud_width, 40), 2)
        
        font = pygame.font.Font(None, 16)
        name_text = font.render(self.name, True, text_color)
        hud_surface.blit(name_text, (4, 2))
        
        health_bar_width = hud_width - 8
        health_bar_height = 6
        health_bar_y = 16
        
        pygame.draw.rect(hud_surface, health_bg_color, (4, health_bar_y, health_bar_width, health_bar_height))
        
        health_fill_width = int(health_bar_width * health_percentage)
        pygame.draw.rect(hud_surface, health_color, (4, health_bar_y, health_fill_width, health_bar_height))
        
        pygame.draw.rect(hud_surface, border_color, (4, health_bar_y, health_bar_width, health_bar_height), 1)
        
        slot_size = 8
        slot_spacing = 2
        inventory_y = 26
        
        for i in range(min(3, self.inventory_size)):
            slot_x = 4 + i * (slot_size + slot_spacing)
            slot_rect = (slot_x, inventory_y, slot_size, slot_size)
            
            pygame.draw.rect(hud_surface, (50, 50, 50), slot_rect)
            pygame.draw.rect(hud_surface, border_color, slot_rect, 1)
            
            if i < len(self.inventory) and self.inventory[i] is not None:
                item_color = self.inventory[i]["item"].color
                pygame.draw.rect(hud_surface, item_color, (slot_x + 1, inventory_y + 1, slot_size - 2, slot_size - 2))
        
        screen.blit(hud_surface, (hud_x, hud_y))
    
    def draw_inventory_screen(self, screen):
        """Draw full inventory screen"""
        if not self.show_inventory:
            return
        
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(128)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))
        
        inv_width = 400
        inv_height = 300
        inv_x = (SCREEN_WIDTH - inv_width) // 2
        inv_y = (SCREEN_HEIGHT - inv_height) // 2
        
        pygame.draw.rect(screen, (50, 50, 50), (inv_x, inv_y, inv_width, inv_height))
        pygame.draw.rect(screen, WHITE, (inv_x, inv_y, inv_width, inv_height), 3)
        
        font = pygame.font.Font(None, 36)
        title = font.render(f"{self.name}'s Inventory", True, WHITE)
        screen.blit(title, (inv_x + 10, inv_y + 10))
        
        gold_text = font.render(f"Gold: {self.gold}", True, YELLOW)
        screen.blit(gold_text, (inv_x + inv_width - 150, inv_y + 10))
        
        slot_size = 50
        slots_per_row = 6
        start_x = inv_x + 20
        start_y = inv_y + 60
        
        font_small = pygame.font.Font(None, 20)
        
        for i in range(self.inventory_size):
            row = i // slots_per_row
            col = i % slots_per_row
            
            slot_x = start_x + col * (slot_size + 10)
            slot_y = start_y + row * (slot_size + 30)
            
            pygame.draw.rect(screen, (30, 30, 30), (slot_x, slot_y, slot_size, slot_size))
            pygame.draw.rect(screen, WHITE, (slot_x, slot_y, slot_size, slot_size), 2)
            
            if self.inventory[i]:
                item = self.inventory[i]["item"]
                quantity = self.inventory[i]["quantity"]
                
                pygame.draw.rect(screen, item.color, (slot_x + 5, slot_y + 5, slot_size - 10, slot_size - 10))
                
                if quantity > 1:
                    qty_text = font_small.render(str(quantity), True, WHITE)
                    screen.blit(qty_text, (slot_x + slot_size - 15, slot_y + slot_size - 15))
                
                name_text = font_small.render(item.name[:8], True, WHITE)
                screen.blit(name_text, (slot_x, slot_y + slot_size + 2))
        
        inst_text = font_small.render("Press I to close, 1-6 to use items", True, WHITE)
        screen.blit(inst_text, (inv_x + 10, inv_y + inv_height - 30))
    
    def draw(self, screen):
        self.draw_sprite_frame(screen, self.animation_frame)
        self.draw_speech_bubble(screen)
        self.draw_hud(screen)
        self.draw_inventory_screen(screen)

class Player(Character):
    """Player character controlled by user input"""
    def __init__(self, x, y, name="Player"):
        super().__init__(x, y, name, "player")
        
        self.speed = 4
        self.hud_color = (0, 255, 0)
        self.inventory_size = 6
        self.inventory = [None] * self.inventory_size
        self.gold = 100
        
        self.shirt_color = (200, 50, 50)
        self.hair_color = (80, 80, 80)
        self.pants_color = (150, 150, 150)

class NPC(Character):
    """Non-player character with AI behavior"""
    def __init__(self, x, y, name="NPC", npc_role="generic"):
        super().__init__(x, y, name, "npc")
        
        self.npc_role = npc_role
        self.speed = 2
        self.hud_color = (0, 100, 255)
        self.inventory_size = 8
        self.inventory = [None] * self.inventory_size
        self.gold = 200
        
        # AI behavior variables
        self.ai_timer = 0
        self.ai_action_duration = 2000
        self.current_action = "idle"
        self.target_x = x
        self.target_y = y
        self.patrol_points = []
        self.current_patrol_index = 0
        
        # Speech system for AI
        self.speech_timer_ai = 0
        self.speech_interval = 8000
        
        # Reaction system
        self.reaction_delay = 1000
        self.pending_reaction = None
        self.reaction_timer = 0
        
        # LLM integration
        self.llm_client = None
        self.waiting_for_llm = False
        self.llm_request_id = 0
        
        # Conversation history
        self.conversation_history = []
        self.max_history_length = 6
        
        # NPC appearance
        self.shirt_color = (128, 0, 128)
        self.hair_color = (128, 128, 128)
        self.pants_color = (139, 69, 19)
    
    def set_role_appearance(self, role):
        """Set appearance based on NPC role"""
        if role == "shopkeeper":
            self.shirt_color = (128, 0, 128)
            self.hair_color = (128, 128, 128)
            self.pants_color = (139, 69, 19)
            self.inventory_size = 12
            self.inventory = [None] * self.inventory_size
            self.gold = 500
            self.patrol_points = [
                (370, 250),
                (420, 250),
                (400, 240),
            ]
    
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
    
    def ai_update(self, dt, walls, other_characters):
        """Update AI behavior"""
        self.ai_timer += dt
        
        if self.ai_timer >= self.ai_action_duration:
            actions = ["idle", "patrol", "wander"]
            self.current_action = random.choice(actions)
            self.ai_timer = 0
            
            if self.current_action == "patrol" and self.patrol_points:
                self.target_x, self.target_y = self.patrol_points[self.current_patrol_index]
                self.current_patrol_index = (self.current_patrol_index + 1) % len(self.patrol_points)
            elif self.current_action == "wander":
                self.target_x = random.randint(330, 470)
                self.target_y = random.randint(230, 270)
        
        if self.current_action == "patrol" or self.current_action == "wander":
            self.move_towards_target(walls, other_characters)
        
        self.update(dt)
        
        if self.llm_client:
            responses = self.llm_client.get_responses()
            for request_id, response in responses:
                if request_id == self.llm_request_id:
                    self.pending_reaction = response
                    self.waiting_for_llm = False
                    break
        
        if self.pending_reaction:
            self.reaction_timer += dt
            if self.reaction_timer >= self.reaction_delay:
                self.add_to_conversation_history(self.npc_role, self.pending_reaction)
                self.say(self.pending_reaction)
                self.pending_reaction = None
                self.reaction_timer = 0
    
    def move_towards_target(self, walls, other_characters):
        """Move towards the current target"""
        dx = self.target_x - self.rect.centerx
        dy = self.target_y - self.rect.centery
        
        distance = math.sqrt(dx*dx + dy*dy)
        
        if distance > 5:
            if distance > 0:
                dx = (dx / distance) * self.speed
                dy = (dy / distance) * self.speed
                self.move(dx, dy, walls, other_characters)
        else:
            self.is_moving = False
    
    def react_to_speech(self, message, speaker):
        """React to what another character said using LLM"""
        print(f"DEBUG: {self.name} heard message: '{message}' from {speaker.name}")
        
        message_lower = message.lower()
        if "check inventory" in message_lower or "my inventory" in message_lower:
            player_items = speaker.get_inventory_list()
            response = f"You have: {', '.join(player_items)}"
            self.pending_reaction = response
            self.reaction_timer = 0
            return
        
        if self.speech_text or self.pending_reaction or self.waiting_for_llm:
            return
        
        if self.llm_client:
            self.waiting_for_llm = True
            self.llm_request_id += 1
            self.add_to_conversation_history("player", message)
            self.llm_client.send_message_async(message, self.llm_request_id, self.conversation_history)
        else:
            if any(word in message_lower for word in ['hello', 'hi', 'hey', 'greetings']):
                responses = ["Hello there, traveler!", "Greetings! Welcome!", "Well hello!"]
            elif any(word in message_lower for word in ['stock', 'have', 'sell', 'inventory', 'items']):
                responses = ["I've got quality goods!", "Take a look around!", "Plenty of fine equipment!"]
            else:
                responses = ["What can I help you with?", "Looking for something?", "How may I assist you?"]
            
            self.pending_reaction = random.choice(responses)
            self.reaction_timer = 0
    
    def add_to_conversation_history(self, role, message):
        """Add a message to conversation history"""
        self.conversation_history.append({"role": role, "message": message})
        
        if len(self.conversation_history) > self.max_history_length:
            self.conversation_history = self.conversation_history[-self.max_history_length:]

def create_shopkeeper(x, y):
    """Factory function to create a shopkeeper NPC"""
    shopkeeper = NPC(x, y, "Shopkeeper", "shopkeeper")
    shopkeeper.set_role_appearance("shopkeeper")
    shopkeeper.stock_shop()
    return shopkeeper

class Shop:
    def __init__(self):
        # Shop walls
        self.walls = [
            pygame.Rect(300, 200, 200, 10),  # Top wall
            pygame.Rect(300, 390, 80, 10),   # Bottom left
            pygame.Rect(420, 390, 80, 10),   # Bottom right
            pygame.Rect(300, 200, 10, 190),  # Left wall
            pygame.Rect(490, 200, 10, 190),  # Right wall
        ]
        
        # Shop counter
        self.counter = pygame.Rect(350, 240, 100, 20)
        
        # Interaction zone
        self.interact_zone = pygame.Rect(350, 260, 100, 40)
        
        # Floor area
        self.floor_area = pygame.Rect(310, 210, 180, 180)
    
    def draw_wooden_floor(self, screen):
        """Draw wooden plank flooring with horizontal planks in zig-zag pattern"""
        plank_height = 12
        plank_width = 60  # Width of individual planks
        colors = [(180, 120, 80), (200, 140, 100), (220, 180, 120)]
        seam_color = (150, 110, 70)
        
        # Draw planks row by row
        for row_index, y in enumerate(range(self.floor_area.top, self.floor_area.bottom, plank_height)):
            # Offset every other row to create zig-zag pattern
            offset = (plank_width // 2) if row_index % 2 == 1 else 0
            
            # Start drawing planks from left edge with offset
            x = self.floor_area.left - offset
            plank_count = 0
            
            while x < self.floor_area.right:
                # Determine plank color (random but consistent based on position)
                # Use position as seed to ensure same plank always has same color
                random.seed(row_index * 1000 + plank_count)
                color = random.choice(colors)
                random.seed()  # Reset seed for other random operations
                
                # Create plank rectangle, clipped to floor area
                plank_rect = pygame.Rect(x, y, plank_width, plank_height)
                clipped_rect = plank_rect.clip(self.floor_area)
                
                if clipped_rect.width > 0 and clipped_rect.height > 0:
                    # Draw the plank
                    pygame.draw.rect(screen, color, clipped_rect)
                    
                    # Draw vertical seam line at the end of this plank
                    seam_x = x + plank_width
                    if (seam_x >= self.floor_area.left and seam_x < self.floor_area.right and 
                        clipped_rect.height > 0):
                        pygame.draw.line(screen, seam_color, 
                                       (seam_x, clipped_rect.top), 
                                       (seam_x, clipped_rect.bottom), 1)
                
                x += plank_width
                plank_count += 1
            
            # Draw horizontal seam line between rows
            if y + plank_height < self.floor_area.bottom:
                pygame.draw.line(screen, seam_color, 
                               (self.floor_area.left, y + plank_height), 
                               (self.floor_area.right, y + plank_height), 1)
    
    def draw(self, screen):
        self.draw_wooden_floor(screen)
        
        # Draw walls
        for wall in self.walls:
            pygame.draw.rect(screen, BROWN, wall)
        
        # Draw counter
        pygame.draw.rect(screen, BROWN, self.counter)
        pygame.draw.rect(screen, BLACK, self.counter, 2)

class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Zelda-style RPG with Inventory System")
        self.clock = pygame.time.Clock()
        self.running = True
        
        # Game objects
        self.player = Player(400, 450)
        self.shopkeeper = create_shopkeeper(400, 250)
        self.shop = Shop()
        self.characters = [self.player, self.shopkeeper]
        
        # Give player some starting items
        self.player.add_item("health_potion", 2)
        self.player.add_item("gold_coin", 50)
        
        # Initialize LLM client
        self.llm_client = LLMClient("http://127.0.0.1:1234")
        self.llm_client.shopkeeper_ref = self.shopkeeper
        self.shopkeeper.llm_client = self.llm_client
        
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
                    elif event.key == pygame.K_i:
                        self.player.show_inventory = not self.player.show_inventory
                    elif event.key == pygame.K_1:
                        self.player.use_item(0)
                    elif event.key == pygame.K_2:
                        self.player.use_item(1)
                    elif event.key == pygame.K_3:
                        self.player.use_item(2)
                    elif event.key == pygame.K_4:
                        self.player.use_item(3)
                    elif event.key == pygame.K_5:
                        self.player.use_item(4)
                    elif event.key == pygame.K_6:
                        self.player.use_item(5)
    
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
        self.shopkeeper.ai_update(dt, self.shop.walls, self.characters)
    
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
        
        font = pygame.font.Font(None, 24)
        instructions = [
            "Arrow Keys: Move",
            "Space: Interact (when near counter)",
            "Enter: Say something",
            "I: Toggle inventory",
            "1-6: Use items"
        ]
        for i, instruction in enumerate(instructions):
            text = font.render(instruction, True, WHITE)
            self.screen.blit(text, (10, 10 + i * 25))
        
        pygame.display.flip()
    
    def draw_text_input(self):
        """Draw the text input interface"""
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