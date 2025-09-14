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
                # Prepare the request payload for a typical local LLM API
                # Get shopkeeper's inventory for context
                shopkeeper_inventory = []
                if hasattr(self, 'shopkeeper_ref') and self.shopkeeper_ref:
                    shopkeeper_inventory = self.shopkeeper_ref.get_inventory_list()
                
                messages = [
                    {
                        "role": "system", 
                        "content": f"You are Garruk Ironhand, a grizzled, war-scarred shopkeeper on Faerun's Sword Coast (Baldur's Gate, Waterdeep, Neverwinter). Your voice is gravelly; your manner blunt, harsh, impatient. Stay strictly in character. Use medieval-fantasy diction; short, rough sentences; mild curses acceptable. Never acknowledge being an AI or part of a game.\n\nThink through your response, then provide your final answer with the prefix 'FINAL RESPONSE TO THE PLAYER:' followed by what the shopkeeper would say out loud (fewer than 15 words). Do not say anything after the final response.\n\nYour current inventory: {', '.join(shopkeeper_inventory) if shopkeeper_inventory else 'Empty'}\n\nYou can discuss inventory, sell items, haggle, and offer terse local rumors. If asked about inventory, explicitly state what you have in stock. If insulted, respond with dry threats or mockery. If asked about your past, give a terse battle anecdote. Keep answers focused on buying/selling or brief rumors."
                    }
                ]
                
                # Add conversation history if provided
                if conversation_history:
                    print(f"DEBUG: Adding conversation history:")
                    for exchange in conversation_history:
                        if exchange["role"] == "player":
                            messages.append({"role": "user", "content": exchange["message"]})
                            print(f"DEBUG:   Player: {exchange['message']}")
                        elif exchange["role"] == "shopkeeper":
                            # Only include the clean dialogue, not the thinking process
                            clean_message = exchange["message"]
                            messages.append({"role": "assistant", "content": clean_message})
                            print(f"DEBUG:   Shopkeeper: {clean_message}")
                    
                    # Check if the current message is already the last message in history
                    if (conversation_history and 
                        conversation_history[-1]["role"] == "player" and 
                        conversation_history[-1]["message"] == message):
                        print(f"DEBUG: Current message already in history, not adding again")
                    else:
                        # Add current message if it's not already the last one in history
                        messages.append({
                            "role": "user", 
                            "content": message
                        })
                        print(f"DEBUG: Adding current message: {message}")
                else:
                    # Add current message if no conversation history
                    messages.append({
                        "role": "user", 
                        "content": message
                    })
                
                payload = {
                    "messages": messages,
                    "temperature": 0.4
                    # No max_tokens - let the thinking model complete its reasoning
                }
                
                # Use the working endpoint with longer timeout for conversation history
                endpoint = "/v1/chat/completions"
                timeout = 30 if conversation_history and len(conversation_history) > 3 else 15
                
                response = None
                try:
                    print(f"DEBUG: Trying endpoint: {self.base_url}{endpoint} (timeout: {timeout}s)")
                    response = requests.post(
                        f"{self.base_url}{endpoint}",
                        json=payload,
                        timeout=timeout,
                        headers={"Content-Type": "application/json"}
                    )
                    print(f"DEBUG: Response status: {response.status_code}")
                except Exception as e:
                    print(f"DEBUG: Endpoint {endpoint} failed: {e}")
                    response = None
                
                if response and response.status_code == 200:
                    data = response.json()
                    print(f"DEBUG: LLM response data: {data}")
                    # Extract response text from common response formats
                    if "choices" in data and len(data["choices"]) > 0:
                        if "message" in data["choices"][0]:
                            ai_response = data["choices"][0]["message"]["content"].strip()
                        elif "text" in data["choices"][0]:
                            ai_response = data["choices"][0]["text"].strip()
                        else:
                            ai_response = "I'm not sure what to say about that."
                    else:
                        ai_response = "Hmm, let me think about that..."
                    
                    # Extract final response from thinking model
                    import re
                    
                    print(f"DEBUG: Raw LLM response: '{ai_response}'")
                    
                    # Extract content after "FINAL RESPONSE TO THE PLAYER:"
                    if "FINAL RESPONSE TO THE PLAYER:" in ai_response:
                        parts = ai_response.split("FINAL RESPONSE TO THE PLAYER:")
                        if len(parts) > 1:
                            ai_response = parts[-1].strip()
                            print(f"DEBUG: Extracted final response: '{ai_response}'")
                    
                    # # Remove any remaining XML-like tags - commenting for now, as i am interested to get the thinking content extraction working as well as possible for now.
                    # ai_response = re.sub(r'<[^>]*>', '', ai_response).strip()
                    
                    # Remove meta-commentary lines that start with common thinking patterns
                    lines = ai_response.split('\n')
                    cleaned_lines = []
                    for line in lines:
                        line = line.strip()
                        # Skip lines that look like meta-commentary
                        if not any(line.lower().startswith(pattern) for pattern in [
                            'thinking:', 'note:', 'mental note:', 'remember:', 'as a', 'i should',
                            'the user', 'keeping it', 'this is', 'must remember'
                        ]):
                            cleaned_lines.append(line)
                    
                    # Join remaining lines and clean up
                    ai_response = ' '.join(cleaned_lines).strip()
                    ai_response = ' '.join(ai_response.split())  # Clean up whitespace
                    
                    # If we have a good response, use it
                    if ai_response and len(ai_response) > 3:
                        # Limit to approximately 20 tokens (rough estimate: ~15 words)
                        words = ai_response.split()
                        if len(words) > 15:
                            ai_response = ' '.join(words[:15])
                            # Add punctuation if missing
                            if not ai_response.endswith(('.', '!', '?')):
                                ai_response += "!"
                        
                        # Ensure it ends with proper punctuation
                        if not ai_response.endswith(('.', '!', '?')):
                            ai_response += "!"
                    else:
                        # Fallback to contextual responses only if no valid response found
                        print(f"DEBUG: No valid response found, using contextual fallback")
                        message_lower = message.lower()
                        if any(word in message_lower for word in ['god', 'worship', 'religion', 'faith', 'deity', 'pray']):
                            fallbacks = [
                                "FALLBACK: I pray to the merchant gods for good fortune!",
                                "FALLBACK: The gods of trade watch over my shop.",
                                "FALLBACK: I honor the old gods, as any wise merchant should."
                            ]
                        elif any(word in message_lower for word in ['stock', 'have', 'sell', 'inventory', 'items', 'buy', 'purchase']):
                            # Get actual inventory for fallback
                            if hasattr(self, 'shopkeeper_ref') and self.shopkeeper_ref:
                                inventory_items = self.shopkeeper_ref.get_inventory_list()
                                if inventory_items and inventory_items != ["Empty"]:
                                    fallbacks = [
                                        f"FALLBACK: I have {', '.join(inventory_items[:3])} and more!",
                                        f"FALLBACK: Check out my {inventory_items[0]} - it's quality!",
                                        "FALLBACK: I've got what adventurers need!"
                                    ]
                                else:
                                    fallbacks = [
                                        "FALLBACK: Sorry, I'm out of stock right now!",
                                        "FALLBACK: Come back later for fresh supplies!"
                                    ]
                            else:
                                fallbacks = [
                                    "FALLBACK: I've got weapons, armor, potions, and gear!",
                                    "FALLBACK: Plenty of fine equipment for adventurers!",
                                    "FALLBACK: I stock everything an adventurer needs!"
                                ]
                        elif any(word in message_lower for word in ['hello', 'hi', 'hey', 'greetings']):
                            fallbacks = [
                                "FALLBACK: Hello there, traveler!",
                                "FALLBACK: Welcome to my shop!",
                                "FALLBACK: Greetings, adventurer!"
                            ]
                        else:
                            fallbacks = [
                                "FALLBACK: What can I help you with?",
                                "FALLBACK: Looking for something specific?",
                                "FALLBACK: How may I assist you?"
                            ]
                        ai_response = random.choice(fallbacks)
                    
                    print(f"DEBUG: Cleaned AI response: '{ai_response}'")
                    
                    # print(f"DEBUG: Cleaned AI response: '{ai_response}'")
                else:
                    ai_response = "Sorry, I'm having trouble thinking right now."
                    print(f"DEBUG: LLM request failed, using fallback response")
                    # print(f"DEBUG: LLM request failed, using fallback response")
                    
            except Exception as e:
                print(f"LLM request failed: {e}")
                ai_response = "LLM request failed: I'm a bit distracted right now."
            
            # Put response in queue with callback ID
            print(f"DEBUG: Putting response in queue: '{ai_response}' (ID: {callback_id})")
            self.response_queue.put((callback_id, ai_response))
        
        # Start request in background thread
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
        self.animation_speed = 200  # milliseconds between frames
        
        # Speech system
        self.speech_text = ""
        self.speech_timer = 0
        self.speech_duration = 3000  # 3 seconds
        
        # Stats system
        self.max_health = 100
        self.current_health = 100
        self.inventory_size = 6
        self.inventory = [None] * self.inventory_size
        self.gold = 100
        
        # Visual system
        self.hud_color = (255, 255, 255)  # Default white
        self.show_inventory = False
        
        # Character appearance colors (can be overridden)
        self.shirt_color = (200, 50, 50)
        self.hair_color = (80, 80, 80)
        self.skin_color = (255, 220, 177)
        self.pants_color = (150, 150, 150)
    
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
        print(f"DEBUG: Player saying: '{message}', notify_characters: {notify_characters is not None}")
        self.speech_text = message
        self.speech_timer = 0
        
        # Notify nearby characters if provided
        if notify_characters:
            self.notify_nearby_characters(message, notify_characters)
    
    def notify_nearby_characters(self, message, characters):
        """Notify nearby characters that this character spoke"""
        print(f"DEBUG: Player notifying nearby characters of message: '{message}'")
        hearing_distance = 300  # pixels - increased so shopkeeper can hear from anywhere in shop
        
        for char in characters:
            if char != self:
                # Calculate distance
                dx = char.rect.centerx - self.rect.centerx
                dy = char.rect.centery - self.rect.centery
                distance = math.sqrt(dx*dx + dy*dy)
                print(f"DEBUG: Distance to {char.name}: {distance} pixels")
                
                # If character is close enough and has a reaction method
                if distance <= hearing_distance and hasattr(char, 'react_to_speech'):
                    print(f"DEBUG: {char.name} is close enough, calling react_to_speech")
                    char.react_to_speech(message, self)
                else:
                    print(f"DEBUG: {char.name} is too far or doesn't have react_to_speech method")
    
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
        
        # Draw inventory slots (show first 3 slots in HUD)
        slot_size = 8
        slot_spacing = 2
        inventory_y = 26
        
        for i in range(min(3, self.inventory_size)):
            slot_x = 4 + i * (slot_size + slot_spacing)
            slot_rect = (slot_x, inventory_y, slot_size, slot_size)
            
            # Draw slot background
            pygame.draw.rect(hud_surface, (50, 50, 50), slot_rect)
            pygame.draw.rect(hud_surface, border_color, slot_rect, 1)
            
            # Draw item if present
            if i < len(self.inventory) and self.inventory[i] is not None:
                item_color = self.inventory[i]["item"].color
                pygame.draw.rect(hud_surface, item_color, (slot_x + 1, inventory_y + 1, slot_size - 2, slot_size - 2))
        
        # Blit HUD to screen
        screen.blit(hud_surface, (hud_x, hud_y))
    
    def add_item(self, item_id, quantity=1):
        """Add an item to inventory"""
        if isinstance(item_id, str):
            item = item_db.get_item(item_id)
            if not item:
                print(f"Item {item_id} not found in database")
                return False
        else:
            item = item_id  # Already an Item object
        
        # Find empty slot
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
                    print(f"Removed {removed_item['quantity']}x {removed_item['item'].name}")
                    return removed_item["quantity"]
                else:
                    self.inventory[i]["quantity"] -= quantity
                    print(f"Removed {quantity}x {self.inventory[i]['item'].name}")
                    return quantity
        
        print(f"Item {item_id} not found in {self.name}'s inventory")
        return 0
    
    def has_item(self, item_id):
        """Check if player has an item"""
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
                # Apply item effects
                if item.heal > 0:
                    old_health = self.current_health
                    self.current_health = min(self.max_health, self.current_health + item.heal)
                    healed = self.current_health - old_health
                    self.say(f"Used {item.name}! Healed {healed} HP")
                
                # Remove one from inventory
                if item_slot["quantity"] <= 1:
                    self.inventory[slot_index] = None
                else:
                    item_slot["quantity"] -= 1
                
                return True
            else:
                self.say(f"Can't use {item.name} right now")
                return False
        return False
    
    def draw_inventory_screen(self, screen):
        """Draw full inventory screen"""
        if not self.show_inventory:
            return
        
        # Semi-transparent overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(128)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))
        
        # Inventory window
        inv_width = 400
        inv_height = 300
        inv_x = (SCREEN_WIDTH - inv_width) // 2
        inv_y = (SCREEN_HEIGHT - inv_height) // 2
        
        # Draw inventory background
        pygame.draw.rect(screen, (50, 50, 50), (inv_x, inv_y, inv_width, inv_height))
        pygame.draw.rect(screen, WHITE, (inv_x, inv_y, inv_width, inv_height), 3)
        
        # Title
        font = pygame.font.Font(None, 36)
        title = font.render(f"{self.name}'s Inventory", True, WHITE)
        screen.blit(title, (inv_x + 10, inv_y + 10))
        
        # Gold display
        gold_text = font.render(f"Gold: {self.gold}", True, YELLOW)
        screen.blit(gold_text, (inv_x + inv_width - 150, inv_y + 10))
        
        # Draw inventory slots
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
            
            # Draw slot background
            pygame.draw.rect(screen, (30, 30, 30), (slot_x, slot_y, slot_size, slot_size))
            pygame.draw.rect(screen, WHITE, (slot_x, slot_y, slot_size, slot_size), 2)
            
            # Draw item if present
            if self.inventory[i]:
                item = self.inventory[i]["item"]
                quantity = self.inventory[i]["quantity"]
                
                # Draw item color
                pygame.draw.rect(screen, item.color, (slot_x + 5, slot_y + 5, slot_size - 10, slot_size - 10))
                
                # Draw quantity
                if quantity > 1:
                    qty_text = font_small.render(str(quantity), True, WHITE)
                    screen.blit(qty_text, (slot_x + slot_size - 15, slot_y + slot_size - 15))
                
                # Draw item name below slot
                name_text = font_small.render(item.name[:8], True, WHITE)
                screen.blit(name_text, (slot_x, slot_y + slot_size + 2))
        
        # Instructions
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
        
        # Player-specific settings
        self.speed = 4
        self.hud_color = (0, 255, 0)  # Green for player
        self.inventory_size = 6
        self.inventory = [None] * self.inventory_size
        self.gold = 100
        
        # Player appearance
        self.shirt_color = (200, 50, 50)  # Red shirt
        self.hair_color = (80, 80, 80)   # Dark gray hair
        self.pants_color = (150, 150, 150)  # Gray pants

class NPC(Character):
    """Non-player character with AI behavior"""
    def __init__(self, x, y, name="NPC", npc_role="generic"):
        super().__init__(x, y, name, "npc")
        
        # NPC-specific settings
        self.npc_role = npc_role
        self.speed = 2  # Generally slower than player
        self.hud_color = (0, 100, 255)  # Blue for NPCs
        self.inventory_size = 8  # NPCs can have larger inventories
        self.inventory = [None] * self.inventory_size
        self.gold = 200
        
        # AI behavior variables
        self.ai_timer = 0
        self.ai_action_duration = 2000  # 2 seconds per action
        self.current_action = "idle"
        self.target_x = x
        self.target_y = y
        self.patrol_points = []
        self.current_patrol_index = 0
        
        # Speech system for AI
        self.speech_timer_ai = 0
        self.speech_interval = 8000  # Speak every 8 seconds
        
        # Reaction system
        self.reaction_delay = 1000  # 1 second delay before reacting
        self.pending_reaction = None
        self.reaction_timer = 0
        
        # LLM integration
        self.llm_client = None
        self.waiting_for_llm = False
        self.llm_request_id = 0
        
        # Conversation history
        self.conversation_history = []
        self.max_history_length = 6
        
        # NPC appearance (can be customized per role)
        self.shirt_color = (128, 0, 128)  # Purple shirt
        self.hair_color = (128, 128, 128)  # Gray hair
        self.pants_color = (139, 69, 19)   # Brown pants
    
    def set_role_appearance(self, role):
        """Set appearance based on NPC role"""
        if role == "shopkeeper":
            self.shirt_color = (128, 0, 128)  # Purple shirt
            self.hair_color = (128, 128, 128)  # Gray hair
            self.pants_color = (139, 69, 19)   # Brown apron/pants
            self.inventory_size = 12  # Shopkeepers have large inventories
            self.inventory = [None] * self.inventory_size
            self.gold = 500
            self.patrol_points = [
                (370, 250),  # Behind counter left
                (420, 250),  # Behind counter right
                (400, 240),  # Behind counter center
            ]
        elif role == "guard":
            self.shirt_color = (100, 100, 100)  # Gray armor
            self.hair_color = (139, 69, 19)     # Brown hair
            self.pants_color = (100, 100, 100)  # Gray armor
            self.speed = 3
        elif role == "villager":
            self.shirt_color = (139, 69, 19)    # Brown shirt
            self.hair_color = (205, 133, 63)    # Light brown hair
            self.pants_color = (160, 82, 45)    # Saddle brown pants
    
    def stock_shop(self):
        """Stock the shop with initial items (for shopkeeper NPCs)"""
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
            # Choose new action
            actions = ["idle", "patrol", "wander"]
            self.current_action = random.choice(actions)
            self.ai_timer = 0
            
            if self.current_action == "patrol" and self.patrol_points:
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
        
        # Check for LLM responses
        if self.llm_client:
            responses = self.llm_client.get_responses()
            for request_id, response in responses:
                if request_id == self.llm_request_id:
                    self.pending_reaction = response
                    self.waiting_for_llm = False
                    break
        
        # Handle pending reactions
        if self.pending_reaction:
            self.reaction_timer += dt
            if self.reaction_timer >= self.reaction_delay:
                # Add NPC's response to conversation history
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
        
        # Handle special inventory commands
        message_lower = message.lower()
        if "check inventory" in message_lower or "my inventory" in message_lower:
            player_items = speaker.get_inventory_list()
            response = f"You have: {', '.join(player_items)}"
            self.pending_reaction = response
            self.reaction_timer = 0
            return
        
        # Don't react if already speaking, have a pending reaction, or waiting for LLM
        if self.speech_text or self.pending_reaction or self.waiting_for_llm:
            return
        
        # If LLM is available, use it for responses
        if self.llm_client:
            self.waiting_for_llm = True
            self.llm_request_id += 1
            self.add_to_conversation_history("player", message)
            self.llm_client.send_message_async(message, self.llm_request_id, self.conversation_history)
        else:
            # Fallback responses
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
    
    def draw_sprite_frame(self, screen, frame):
        """Draw NPC sprite based on their role"""
        # Base position
        x, y = self.rect.x, self.rect.y
        
        # Draw character based on frame (pixel art style)
        if frame == 0:  # Standing/Frame 1
            # Head
            pygame.draw.rect(screen, self.skin_color, (x + 10, y + 2, 8, 8))
            # Hair
            pygame.draw.rect(screen, self.hair_color, (x + 8, y, 12, 6))
            # Body (shirt)
            pygame.draw.rect(screen, self.shirt_color, (x + 8, y + 10, 12, 10))
            # Arms
            pygame.draw.rect(screen, self.skin_color, (x + 4, y + 12, 4, 8))
            pygame.draw.rect(screen, self.skin_color, (x + 20, y + 12, 4, 8))
            # Legs
            pygame.draw.rect(screen, self.pants_color, (x + 10, y + 20, 8, 8))
            # Feet
            pygame.draw.rect(screen, self.hair_color, (x + 8, y + 26, 4, 2))
            pygame.draw.rect(screen, self.hair_color, (x + 16, y + 26, 4, 2))
        else:  # Walking frame 2
            # Head
            pygame.draw.rect(screen, self.skin_color, (x + 10, y + 2, 8, 8))
            # Hair
            pygame.draw.rect(screen, self.hair_color, (x + 8, y, 12, 6))
            # Body (shirt)
            pygame.draw.rect(screen, self.shirt_color, (x + 8, y + 10, 12, 10))
            # Arms (slightly different position)
            pygame.draw.rect(screen, self.skin_color, (x + 6, y + 12, 4, 8))
            pygame.draw.rect(screen, self.skin_color, (x + 18, y + 12, 4, 8))
            # Legs (walking position)
            pygame.draw.rect(screen, self.pants_color, (x + 8, y + 20, 4, 8))
            pygame.draw.rect(screen, self.pants_color, (x + 16, y + 20, 4, 8))
            # Feet (walking position)
            pygame.draw.rect(screen, self.hair_color, (x + 6, y + 26, 4, 2))
            pygame.draw.rect(screen, self.hair_color, (x + 18, y + 26, 4, 2))

# Create a Shopkeeper as a specific NPC instance
def create_shopkeeper(x, y):
    """Factory function to create a shopkeeper NPC"""
    shopkeeper = NPC(x, y, "Shopkeeper", "shopkeeper")
    shopkeeper.set_role_appearance("shopkeeper")
    shopkeeper.stock_shop()
    return shopkeeper
    def __init__(self, x, y):
        super().__init__(x, y)
        self.speed = 2  # Slower than player
        
        # Override HUD properties for NPC
        self.name = "Shopkeeper"
        self.max_health = 80
        self.current_health = 44  # 55% health to test yellow bar
        self.inventory_size = 12  # Shopkeepers have larger inventories
        self.inventory = [None] * self.inventory_size
        self.gold = 500  # Shopkeepers start with more gold
        self.hud_color = (0, 100, 255)  # Blue for NPC
        self.show_inventory = False
        
        # Stock the shop with items
        self.stock_shop()
        
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
        
        # LLM integration
        self.llm_client = None  # Will be set by game
        self.waiting_for_llm = False
        self.llm_request_id = 0
        
        # Conversation history - store recent exchanges
        self.conversation_history = []  # List of {"role": "player/shopkeeper", "message": "text"}
        self.max_history_length = 6  # Keep last 6 exchanges (3 back-and-forth)
    
    def stock_shop(self):
        """Stock the shop with initial items"""
        # Add some basic items to the shop
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
        
        # Check for LLM responses
        if self.llm_client:
            responses = self.llm_client.get_responses()
            if responses:
                print(f"DEBUG: Got {len(responses)} LLM responses")
            for request_id, response in responses:
                print(f"DEBUG: Processing response ID {request_id}, expecting {self.llm_request_id}")
                if request_id == self.llm_request_id:
                    print(f"DEBUG: Setting pending reaction: '{response}'")
                    self.pending_reaction = response
                    self.waiting_for_llm = False
                    break
        
        # AI speech system disabled - shopkeeper only speaks when spoken to
        # if not self.pending_reaction and not self.waiting_for_llm:
        #     self.speech_timer_ai += dt
        #     if self.speech_timer_ai >= self.speech_interval:
        #         self.ai_speak()
        #         self.speech_timer_ai = 0
        
        # Handle pending reactions
        if self.pending_reaction:
            self.reaction_timer += dt
            if self.reaction_timer >= self.reaction_delay:
                # Add shopkeeper's response to conversation history
                self.add_to_conversation_history("shopkeeper", self.pending_reaction)
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
        """React to what another character said using LLM"""
        print(f"DEBUG: Shopkeeper heard message: '{message}' from {speaker.name}")
        
        # Handle special inventory commands
        message_lower = message.lower()
        if "check inventory" in message_lower or "my inventory" in message_lower:
            player_items = speaker.get_inventory_list()
            response = f"You have: {', '.join(player_items)}"
            self.pending_reaction = response
            self.reaction_timer = 0
            return
        
        # Don't react if already speaking, have a pending reaction, or waiting for LLM
        if self.speech_text or self.pending_reaction or self.waiting_for_llm:
            print(f"DEBUG: Shopkeeper can't react - speech_text: {bool(self.speech_text)}, pending_reaction: {bool(self.pending_reaction)}, waiting_for_llm: {self.waiting_for_llm}")
            return
        
        # If LLM is available, use it for responses
        if self.llm_client:
            print(f"DEBUG: Using LLM for response with conversation history")
            self.waiting_for_llm = True
            self.llm_request_id += 1
            # Add player's message to conversation history BEFORE sending to LLM
            self.add_to_conversation_history("player", message)
            self.llm_client.send_message_async(message, self.llm_request_id, self.conversation_history)
        else:
            print(f"DEBUG: No LLM client available, using fallback responses")
            # Fallback to original hardcoded responses if LLM is not available
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
            
            # Default responses for anything else
            else:
                responses = [
                    "Is that so?",
                    "Interesting...",
                    "I see.",
                    "Hmm, indeed."
                ]
            
            # Set a random response with delay
            self.pending_reaction = random.choice(responses)
            self.reaction_timer = 0
    
    def add_to_conversation_history(self, role, message):
        """Add a message to conversation history"""
        self.conversation_history.append({"role": role, "message": message})
        
        # Keep only the most recent exchanges
        if len(self.conversation_history) > self.max_history_length:
            self.conversation_history = self.conversation_history[-self.max_history_length:]
        
        print(f"DEBUG: Added to conversation history ({role}): '{message}'")
        print(f"DEBUG: Conversation history now has {len(self.conversation_history)} exchanges")

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
        self.shopkeeper = create_shopkeeper(400, 250)  # Start behind counter
        self.shop = Shop()
        self.characters = [self.player, self.shopkeeper]
        
        # Give player some starting items
        self.player.add_item("health_potion", 2)
        self.player.add_item("gold_coin", 50)
        
        # Initialize LLM client and connect to shopkeeper
        self.llm_client = LLMClient("http://127.0.0.1:1234")
        self.llm_client.shopkeeper_ref = self.shopkeeper  # Add reference for inventory context
        self.shopkeeper.llm_client = self.llm_client
        
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
                    elif event.key == pygame.K_i:
                        # Toggle inventory
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