#!/usr/bin/env python3
"""
Test script to verify dialogue history is working correctly
"""

import json
import time
from npc.controller import NPCController
from llm_config import get_llm_config

def create_mock_npc():
    """Create a mock NPC for testing"""
    class MockRect:
        def __init__(self, x, y):
            self.x = x
            self.y = y
            self.centerx = x + 16
            self.centery = y + 16
    
    class MockNPC:
        def __init__(self):
            self.rect = MockRect(320, 160)
            self.current_health = 100
            self.is_moving = False
            self.speech_text = ""
            self.current_action = "idle"
            self.speed = 4
            self.name = "Garruk Ironhand"
            
        def say(self, text):
            self.speech_text = text
            print(f"🗣️  {self.name}: '{text}'")
            
        def move(self, dx, dy, walls, characters):
            self.rect.x += dx
            self.rect.y += dy
            self.rect.centerx = self.rect.x + 16
            self.rect.centery = self.rect.y + 16
            self.is_moving = True
            
        def has_item(self, item_id):
            return item_id in ["health_potion", "iron_sword"]
            
        def remove_item(self, item_id, qty):
            return 1 if self.has_item(item_id) else 0
            
        def add_item(self, item_id, qty):
            return True
            
        def get_inventory_list(self):
            return ["5x Health Potion", "3x Mana Potion", "2x Iron Sword"]
    
    return MockNPC()

def create_mock_player(speech_text=""):
    """Create a mock player for testing"""
    class MockRect:
        def __init__(self, x, y):
            self.x = x
            self.y = y
            self.centerx = x + 16
            self.centery = y + 16
    
    class MockPlayer:
        def __init__(self, speech_text):
            self.rect = MockRect(400, 160)
            self.speech_text = speech_text
    
    return MockPlayer(speech_text)

def simulate_conversation():
    """Simulate a conversation to test dialogue history"""
    
    print("=" * 60)
    print("DIALOGUE HISTORY TEST")
    print("=" * 60)
    
    # Create NPC and controller
    npc = create_mock_npc()
    config = get_llm_config()
    controller = NPCController(npc, 
                             llm_endpoint=config["endpoint"],
                             use_tool_calls=config["use_tool_calls"])
    
    # Test conversation sequence
    conversation_steps = [
        ("hello", "Player greets NPC"),
        ("what are you selling?", "Player asks about inventory"),
        ("how much for a health potion?", "Player asks about pricing"),
        ("I'll take two health potions", "Player wants to buy items"),
        ("thanks", "Player says thanks")
    ]
    
    current_time = 1000
    
    for i, (player_speech, description) in enumerate(conversation_steps):
        print(f"\n--- Step {i+1}: {description} ---")
        print(f"👤 Player: '{player_speech}'")
        
        # Create player with current speech
        player = create_mock_player(player_speech)
        
        # Create engine state
        engine_state = {
            "npc": npc,
            "player": player,
            "walls": [],
            "entities": [],
            "characters": [npc, player],
            "current_time": current_time,
            "player_spoke": True,
            "tick": 100 + i * 10
        }
        
        # Make NPC decision
        result = controller.npc_decision_tick(engine_state)
        
        if result:
            print(f"✅ NPC Decision Result: {result}")
        else:
            print("❌ No decision made")
        
        # Show current dialogue history
        print(f"📚 Dialogue History ({len(controller.dialogue_history)} entries):")
        for entry in controller.dialogue_history:
            speaker = entry["speaker"]
            message = entry["message"]
            print(f"   {speaker}: \"{message}\"")
        
        current_time += 5000  # Advance time
        time.sleep(0.5)  # Small delay for readability
    
    print("\n" + "=" * 60)
    print("DIALOGUE CONTEXT TEST")
    print("=" * 60)
    
    # Test the dialogue context building
    context = controller._build_dialogue_context()
    print("Final dialogue context that would be sent to LLM:")
    print(context)
    
    print("\n" + "=" * 60)
    print("✅ DIALOGUE HISTORY TEST COMPLETE")
    print("The NPC should now remember the conversation context!")
    print("=" * 60)

def test_dialogue_memory_persistence():
    """Test that dialogue memory persists across multiple interactions"""
    
    print("\n" + "=" * 60)
    print("DIALOGUE MEMORY PERSISTENCE TEST")
    print("=" * 60)
    
    npc = create_mock_npc()
    config = get_llm_config()
    controller = NPCController(npc, 
                             llm_endpoint=config["endpoint"],
                             use_tool_calls=config["use_tool_calls"])
    
    # Add some dialogue history manually
    controller._add_to_dialogue_history("Player", "hello")
    controller._add_to_dialogue_history("Garruk Ironhand", "What do you want?")
    controller._add_to_dialogue_history("Player", "what are you selling?")
    controller._add_to_dialogue_history("Garruk Ironhand", "Potions, swords, armor.")
    
    print("Added dialogue history manually...")
    
    # Now test a new interaction
    player = create_mock_player("how much for the sword?")
    
    engine_state = {
        "npc": npc,
        "player": player,
        "walls": [],
        "entities": [],
        "characters": [npc, player],
        "current_time": 10000,
        "player_spoke": True,
        "tick": 200
    }
    
    print(f"👤 Player: '{player.speech_text}'")
    
    # Check that dialogue context includes previous conversation
    context = controller._build_dialogue_context()
    print("\nDialogue context being sent to LLM:")
    print(context)
    
    # Verify the context includes previous exchanges
    if "hello" in context and "What do you want?" in context:
        print("✅ Previous conversation is included in context")
    else:
        print("❌ Previous conversation missing from context")
    
    print("=" * 60)

if __name__ == "__main__":
    simulate_conversation()
    test_dialogue_memory_persistence()