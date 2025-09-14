#!/usr/bin/env python3
"""
Test script to verify LM Studio tool calls setup for Qwen3 7B
"""

import json
from npc.llm_client_tool_calls import LLMClientToolCalls, test_llm_client_tool_calls

def main():
    print("=" * 60)
    print("LM Studio Tool Calls Test for Qwen3 7B")
    print("=" * 60)
    
    print("\n1. Testing basic connection and tool call support...")
    client = LLMClientToolCalls()
    
    if not client.test_connection():
        print("❌ FAILED: LM Studio doesn't support tool calls or isn't running")
        print("\nTroubleshooting:")
        print("1. Make sure LM Studio is running at http://127.0.0.1:1234")
        print("2. Load a model that supports function calling (like Qwen3 7B)")
        print("3. Check that the model is properly loaded")
        return False
    
    print("✅ SUCCESS: Tool calls are supported!")
    
    print("\n2. Testing NPC decision making with tool calls...")
    
    # Test greeting scenario
    greeting_observation = {
        "npc": {
            "pos": [10, 5], 
            "hp": 100, 
            "state": "idle",
            "inventory": ["5x Health Potion", "3x Mana Potion", "2x Iron Sword"]
        },
        "player": {
            "pos": [12, 5], 
            "last_said": "hello"
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
        "visible_entities": [],
        "goals": ["greet player"],
        "cooldowns": {"move": 0, "interact": 0},
        "last_result": None,
        "tick": 100
    }
    
    print("Testing greeting scenario...")
    response, error = client.decide(greeting_observation)
    
    if error:
        print(f"❌ FAILED: {error}")
        return False
    
    try:
        parsed = json.loads(response)
        print(f"✅ SUCCESS: {parsed}")
        
        if parsed.get("action") == "say":
            print("✅ Correctly chose 'say' action for greeting")
        else:
            print(f"⚠️  WARNING: Expected 'say' action, got '{parsed.get('action')}'")
            
    except json.JSONDecodeError as e:
        print(f"❌ FAILED: Invalid JSON response: {e}")
        return False
    
    print("\n3. Testing movement command...")
    
    # Test movement scenario
    movement_observation = {
        "npc": {
            "pos": [10, 5], 
            "hp": 100, 
            "state": "idle",
            "inventory": ["5x Health Potion"]
        },
        "player": {
            "pos": [12, 5], 
            "last_said": "move east"
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
        "visible_entities": [],
        "goals": ["follow player commands"],
        "cooldowns": {"move": 0, "interact": 0},
        "last_result": None,
        "tick": 200
    }
    
    print("Testing movement command...")
    response, error = client.decide(movement_observation)
    
    if error:
        print(f"❌ FAILED: {error}")
        return False
    
    try:
        parsed = json.loads(response)
        print(f"✅ SUCCESS: {parsed}")
        
        if parsed.get("action") == "move":
            args = parsed.get("args", {})
            if args.get("direction") == "E":
                print("✅ Correctly chose 'move' action with direction 'E'")
            else:
                print(f"⚠️  WARNING: Expected direction 'E', got '{args.get('direction')}'")
        else:
            print(f"⚠️  WARNING: Expected 'move' action, got '{parsed.get('action')}'")
            
    except json.JSONDecodeError as e:
        print(f"❌ FAILED: Invalid JSON response: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("Your LM Studio setup supports tool calls correctly.")
    print("You can now use the updated game with cleaner logs.")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        exit(1)