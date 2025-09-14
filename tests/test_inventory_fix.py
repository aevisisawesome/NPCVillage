#!/usr/bin/env python3
"""
Test the inventory fix by simulating the exact scenario from the user's debug output.
"""

from zelda_game_llm_integration import create_llm_shopkeeper
from npc.observation import build_observation
from npc.llm_client import LLMClient
from npc.actions import parse_action
import json


def simulate_conversation():
    """Simulate the conversation that was having issues"""
    
    print("🎭 Simulating Inventory Conversation")
    print("=" * 50)
    
    # Create shopkeeper
    shopkeeper = create_llm_shopkeeper(400, 250)
    
    # Mock player
    class MockPlayer:
        def __init__(self):
            self.rect = type('Rect', (), {'centerx': 450, 'centery': 250})()
            self.speech_text = None
    
    player = MockPlayer()
    
    # Test the problematic conversation
    test_messages = [
        "hi",
        "weapons", 
        "what do you have in stock"
    ]
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n--- Turn {i}: Player says '{message}' ---")
        
        # Update player speech
        player.speech_text = message
        
        # Build observation
        engine_state = {
            "npc": shopkeeper,
            "player": player,
            "walls": [],
            "entities": [],
            "characters": [shopkeeper, player],
            "current_time": i * 1000,
            "player_spoke": True,
            "tick": i * 100
        }
        
        observation = build_observation(engine_state)
        
        print(f"📦 NPC Inventory in Observation:")
        for item in observation["npc"]["inventory"]:
            print(f"  - {item}")
        
        # Test with LLM if available
        try:
            client = LLMClient()
            if client.test_connection():
                print(f"\n🤖 Sending to LLM...")
                response, error = client.decide(observation)
                
                if error:
                    print(f"❌ LLM Error: {error}")
                    continue
                
                print(f"📝 Raw LLM Response: {response}")
                
                # Parse the response
                action, parse_error = parse_action(response)
                if parse_error:
                    print(f"❌ Parse Error: {parse_error}")
                    continue
                
                if action.action == "say":
                    npc_response = action.args.text
                    print(f"💬 Garruk says: '{npc_response}'")
                    
                    # Check if response mentions actual inventory
                    response_lower = npc_response.lower()
                    actual_items = ["health potion", "mana potion", "iron sword", "leather armor", "rope", "torch"]
                    fake_items = ["steel blade", "chainmail", "war hammer"]
                    
                    mentioned_real = [item for item in actual_items if item in response_lower]
                    mentioned_fake = [item for item in fake_items if item in response_lower]
                    
                    if mentioned_real:
                        print(f"✅ Mentioned real items: {mentioned_real}")
                    if mentioned_fake:
                        print(f"❌ Mentioned fake items: {mentioned_fake}")
                    if not mentioned_real and not mentioned_fake:
                        print("ℹ️  Generic response (no specific items mentioned)")
                
            else:
                print("⚠️  LLM server not available - using mock response")
                # Show what the observation looks like
                print(f"📋 Observation would include:")
                print(f"   Player said: '{observation['player']['last_said']}'")
                print(f"   NPC inventory: {observation['npc']['inventory']}")
                
        except Exception as e:
            print(f"❌ Test failed: {e}")
    
    print(f"\n" + "=" * 50)
    print("🔧 TROUBLESHOOTING STEPS:")
    print("1. ✅ Inventory is now included in observations")
    print("2. ✅ LLM prompt updated to reference inventory")
    print("3. 🔄 Update your LM Studio system prompt with the new version")
    print("4. 🎮 Test in the actual game")
    
    print(f"\n📝 EXPECTED BEHAVIOR:")
    print("When asked 'what do you have in stock', Garruk should mention:")
    print("- Health potions, mana potions")
    print("- Iron sword, leather armor") 
    print("- Rope, torches")
    print("NOT: steel blades, chainmail, war hammers")


if __name__ == "__main__":
    simulate_conversation()