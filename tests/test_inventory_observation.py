#!/usr/bin/env python3
"""
Test script to verify that inventory information is included in observations.
"""

from zelda_game_llm_integration import create_llm_shopkeeper
from npc.observation import build_observation
import json


def test_inventory_in_observation():
    """Test that shopkeeper inventory appears in LLM observations"""
    
    print("🧪 Testing Inventory in Observations")
    print("-" * 50)
    
    # Create shopkeeper
    shopkeeper = create_llm_shopkeeper(400, 250)
    
    # Mock player
    class MockPlayer:
        def __init__(self):
            self.rect = type('Rect', (), {'centerx': 450, 'centery': 250})()
            self.speech_text = "what do you have in stock"
    
    player = MockPlayer()
    
    # Build observation
    engine_state = {
        "npc": shopkeeper,
        "player": player,
        "walls": [],
        "entities": [],
        "tick": 100,
        "last_result": None,
        "goals": ["sell items"],
        "cooldowns": {"move": 0, "interact": 0}
    }
    
    observation = build_observation(engine_state)
    
    print("📦 Shopkeeper's Actual Inventory:")
    actual_inventory = shopkeeper.get_inventory_list()
    for item in actual_inventory:
        print(f"  - {item}")
    
    print(f"\n🔍 Inventory in Observation:")
    if "inventory" in observation["npc"]:
        obs_inventory = observation["npc"]["inventory"]
        for item in obs_inventory:
            print(f"  - {item}")
        
        # Check if they match
        if set(actual_inventory) == set(obs_inventory):
            print("\n✅ Inventory correctly included in observation!")
        else:
            print("\n❌ Inventory mismatch!")
            print(f"Actual: {actual_inventory}")
            print(f"Observed: {obs_inventory}")
    else:
        print("❌ No inventory found in observation!")
    
    print(f"\n📋 Full Observation:")
    print(json.dumps(observation, indent=2))
    
    # Test with LLM if available
    print(f"\n🤖 Testing LLM Response:")
    try:
        from npc.llm_client import LLMClient
        client = LLMClient()
        
        if client.test_connection():
            response, error = client.decide(observation)
            if error:
                print(f"❌ LLM Error: {error}")
            else:
                print(f"📝 LLM Response: {response}")
                
                # Check if response mentions actual inventory items
                response_lower = response.lower()
                actual_items = [item.lower() for item in actual_inventory]
                
                mentioned_items = []
                for item in actual_items:
                    if any(word in response_lower for word in item.split()):
                        mentioned_items.append(item)
                
                if mentioned_items:
                    print(f"✅ LLM mentioned actual inventory items: {mentioned_items}")
                else:
                    print("⚠️  LLM didn't mention specific inventory items")
        else:
            print("⚠️  LLM server not available")
            
    except Exception as e:
        print(f"⚠️  LLM test failed: {e}")


if __name__ == "__main__":
    test_inventory_in_observation()