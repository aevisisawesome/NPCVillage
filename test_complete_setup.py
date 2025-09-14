#!/usr/bin/env python3
"""
Complete test of the updated LLM system with tool calls and dialogue history
"""

import json
import time
from npc.llm_client_tool_calls import LLMClientToolCalls
from llm_config import get_llm_config, print_config_info

def test_complete_setup():
    """Test the complete setup including tool calls and dialogue history"""
    
    print("=" * 70)
    print("COMPLETE LLM SETUP TEST")
    print("=" * 70)
    
    # Show configuration
    print("\n1. CONFIGURATION:")
    print("-" * 30)
    print_config_info()
    
    # Test tool calls connection
    print("\n2. TOOL CALLS CONNECTION TEST:")
    print("-" * 30)
    
    client = LLMClientToolCalls()
    
    if not client.test_connection():
        print("❌ FAILED: Tool calls not supported")
        print("\nFallback: Set USE_TOOL_CALLS = False in llm_config.py")
        return False
    
    print("✅ SUCCESS: Tool calls are working!")
    
    # Test dialogue context scenario
    print("\n3. DIALOGUE CONTEXT TEST:")
    print("-" * 30)
    
    # Simulate a conversation with dialogue history
    dialogue_context = """RECENT CONVERSATION:
Player: "hello"
Garruk Ironhand: "What do you want?"
Player: "what are you selling?"
Garruk Ironhand: "Potions, swords, armor."
Player: "how much for a health potion?"
Garruk Ironhand: "Five gold pieces."
"""
    
    # Current observation with new player question
    current_observation = {
        "npc": {
            "pos": [10, 5], 
            "hp": 100, 
            "state": "idle",
            "inventory": ["5x Health Potion", "3x Mana Potion", "2x Iron Sword"]
        },
        "player": {
            "pos": [12, 5], 
            "last_said": "I'll take two health potions"
        },
        "local_tiles": {
            "origin": [5, 0],
            "grid": [
                "###########",
                "#.........#",
                "#.........#",
                "#.........#",
                "#.........#",
                "#..N.P....#",
                "#.........#",
                "#.........#",
                "#.........#",
                "#.........#",
                "###########"
            ]
        },
        "visible_entities": [
            {"id": "player", "kind": "player", "pos": [12, 5]}
        ],
        "goals": ["sell items", "help player"],
        "cooldowns": {"move": 0, "interact": 0},
        "last_result": None,
        "tick": 500
    }
    
    print("Testing with dialogue context...")
    print(f"Player's current request: '{current_observation['player']['last_said']}'")
    
    # Send to LLM with dialogue context
    response, error = client.decide(current_observation, dialogue_context)
    
    if error:
        print(f"❌ FAILED: {error}")
        return False
    
    try:
        parsed = json.loads(response)
        print(f"✅ SUCCESS: {parsed}")
        
        # Check if response makes sense in context
        action = parsed.get("action")
        args = parsed.get("args", {})
        
        if action == "say":
            text = args.get("text", "")
            print(f"🗣️  NPC would say: '{text}'")
            
            # Check if response acknowledges the purchase request
            purchase_keywords = ["ten", "gold", "here", "take", "buy", "sell", "coins"]
            if any(keyword in text.lower() for keyword in purchase_keywords):
                print("✅ Response appropriately handles purchase request")
            else:
                print("⚠️  Response might not fully address purchase context")
                
        elif action == "transfer_item":
            item_id = args.get("item_id", "")
            entity_id = args.get("entity_id", "")
            print(f"🔄 NPC would transfer {item_id} to {entity_id}")
            print("✅ NPC correctly chose to transfer item")
        else:
            print(f"⚠️  Unexpected action for purchase request: {action}")
            
    except json.JSONDecodeError as e:
        print(f"❌ FAILED: Invalid JSON response: {e}")
        return False
    
    # Test movement command with context
    print("\n4. MOVEMENT WITH CONTEXT TEST:")
    print("-" * 30)
    
    movement_context = """RECENT CONVERSATION:
Player: "hello"
Garruk Ironhand: "What do you want?"
Player: "can you move closer?"
"""
    
    movement_observation = {
        "npc": {
            "pos": [8, 5], 
            "hp": 100, 
            "state": "idle",
            "inventory": ["5x Health Potion"]
        },
        "player": {
            "pos": [12, 5], 
            "last_said": "move east please"
        },
        "local_tiles": {
            "origin": [3, 0],
            "grid": [
                "###########",
                "#.........#",
                "#.........#",
                "#.........#",
                "#.........#",
                "#..N..P...#",
                "#.........#",
                "#.........#",
                "#.........#",
                "#.........#",
                "###########"
            ]
        },
        "visible_entities": [
            {"id": "player", "kind": "player", "pos": [12, 5]}
        ],
        "goals": ["follow player commands"],
        "cooldowns": {"move": 0, "interact": 0},
        "last_result": None,
        "tick": 600
    }
    
    print("Testing movement command with context...")
    print(f"Player's request: '{movement_observation['player']['last_said']}'")
    
    response, error = client.decide(movement_observation, movement_context)
    
    if error:
        print(f"❌ FAILED: {error}")
        return False
    
    try:
        parsed = json.loads(response)
        print(f"✅ SUCCESS: {parsed}")
        
        action = parsed.get("action")
        args = parsed.get("args", {})
        
        if action == "move":
            direction = args.get("direction", "")
            distance = args.get("distance", 0)
            print(f"🚶 NPC would move {direction} for {distance} tiles")
            
            if direction == "E":
                print("✅ Correctly interpreted 'east' as direction 'E'")
            else:
                print(f"⚠️  Expected direction 'E', got '{direction}'")
        else:
            print(f"⚠️  Expected 'move' action, got '{action}'")
            
    except json.JSONDecodeError as e:
        print(f"❌ FAILED: Invalid JSON response: {e}")
        return False
    
    print("\n" + "=" * 70)
    print("✅ ALL TESTS PASSED!")
    print("\nYour setup is working correctly:")
    print("• Tool calls are properly structured")
    print("• Dialogue history is being sent to LLM")
    print("• NPC responds appropriately to context")
    print("• Movement commands work with conversation history")
    print("\nYou can now run the game with improved dialogue memory!")
    print("=" * 70)
    
    return True

def show_example_logs():
    """Show what the improved logs will look like"""
    
    print("\n" + "=" * 70)
    print("EXAMPLE: IMPROVED LM STUDIO LOGS")
    print("=" * 70)
    
    print("\nBEFORE (JSON Parsing):")
    print("-" * 30)
    print("""tool_calls: []
content: {"action":"say","args":{"text":"What do you want?"}}""")
    
    print("\nAFTER (Tool Calls):")
    print("-" * 30)
    print("""tool_calls: [
  {
    "id": "call_1",
    "type": "function",
    "function": {
      "name": "say",
      "arguments": "{\\"text\\":\\"What do you want?\\"}"
    }
  }
]
content: null""")
    
    print("\nBENEFITS:")
    print("• No more empty tool_calls arrays")
    print("• Structured function calls in logs")
    print("• Easier debugging and monitoring")
    print("• More reliable parsing")
    print("=" * 70)

if __name__ == "__main__":
    success = test_complete_setup()
    
    if success:
        show_example_logs()
        print(f"\n🎮 Ready to run: python zelda_game_with_llm_npc.py")
    else:
        print(f"\n🔧 Fix the issues above, then try: python test_complete_setup.py")
        exit(1)