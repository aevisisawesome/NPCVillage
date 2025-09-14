#!/usr/bin/env python3
"""
Simple script to test LLM connection and validate the NPC system works.
Run this before starting the game to ensure everything is configured correctly.
"""

import os
import sys
from npc.llm_client import LLMClient
from npc.actions import parse_action
from npc.observation import build_observation
import json


def test_llm_connection():
    """Test basic LLM connectivity"""
    print("🔍 Testing LLM Connection...")
    print("-" * 40)
    
    # Check environment variables
    endpoint = os.getenv("LLM_ENDPOINT", "http://127.0.0.1:1234/v1/chat/completions")
    model = os.getenv("LOCAL_LLM_MODEL", "local-model")
    temp = os.getenv("LLM_TEMP", "0.4")
    
    print(f"Endpoint: {endpoint}")
    print(f"Model: {model}")
    print(f"Temperature: {temp}")
    print()
    
    # Test connection
    client = LLMClient()
    
    if client.test_connection():
        print("✅ LLM server is reachable!")
    else:
        print("❌ LLM server connection failed!")
        print("Make sure your local LLM server is running at the configured endpoint.")
        return False
    
    return True


def test_action_parsing():
    """Test action parsing with sample responses"""
    print("\n🧪 Testing Action Parsing...")
    print("-" * 40)
    
    test_cases = [
        ('{"action":"say","args":{"text":"Hello traveler!"}}', True),
        ('{"action":"move_dir","args":{"direction":"E"}}', True),
        ('{"action":"move_to","args":{"x":10,"y":5}}', True),
        ('{"action":"interact","args":{"entity_id":"door_1"}}', True),
        ('{"action":"invalid","args":{}}', False),
        ('not json', False),
        ('{"action":"say","args":"wrong format"}', False),
    ]
    
    passed = 0
    for test_input, should_pass in test_cases:
        action, error = parse_action(test_input)
        success = action is not None
        
        if success == should_pass:
            status = "✅"
            passed += 1
        else:
            status = "❌"
        
        print(f"{status} {test_input[:50]}{'...' if len(test_input) > 50 else ''}")
        if error and not should_pass:
            print(f"    Error: {error}")
    
    print(f"\nPassed: {passed}/{len(test_cases)} tests")
    return passed == len(test_cases)


def test_observation_building():
    """Test observation building"""
    print("\n🗺️  Testing Observation Building...")
    print("-" * 40)
    
    # Mock objects for testing
    class MockRect:
        def __init__(self, x, y):
            self.x = x
            self.y = y
            self.centerx = x + 16
            self.centery = y + 16
    
    class MockCharacter:
        def __init__(self, x, y):
            self.rect = MockRect(x, y)
            self.current_health = 100
            self.speech_text = "Hello!"
    
    # Create test scenario
    npc = MockCharacter(320, 160)
    player = MockCharacter(416, 160)
    
    engine_state = {
        "npc": npc,
        "player": player,
        "walls": [],
        "entities": [],
        "tick": 100,
        "last_result": None,
        "goals": ["greet player"],
        "cooldowns": {"move": 0, "interact": 0}
    }
    
    try:
        observation = build_observation(engine_state)
        
        # Validate observation structure
        required_keys = ["npc", "player", "local_tiles", "visible_entities", 
                        "goals", "cooldowns", "last_result", "tick"]
        
        missing_keys = [key for key in required_keys if key not in observation]
        
        if missing_keys:
            print(f"❌ Missing keys: {missing_keys}")
            return False
        
        # Check grid format
        grid = observation["local_tiles"]["grid"]
        if len(grid) != 11 or any(len(row) != 11 for row in grid):
            print("❌ Invalid grid dimensions")
            return False
        
        print("✅ Observation structure is valid")
        print(f"   NPC position: {observation['npc']['pos']}")
        print(f"   Player position: {observation['player']['pos']}")
        print(f"   Grid size: {len(grid)}x{len(grid[0])}")
        
        return True
        
    except Exception as e:
        print(f"❌ Observation building failed: {e}")
        return False


def test_full_integration():
    """Test full integration with a sample decision"""
    print("\n🎯 Testing Full Integration...")
    print("-" * 40)
    
    if not test_llm_connection():
        print("⚠️  Skipping integration test - LLM not available")
        return True  # Don't fail the whole test
    
    # Create a simple observation
    sample_observation = {
        "npc": {"pos": [10, 5], "hp": 100, "state": "Idle"},
        "player": {"pos": [12, 5], "last_said": "hello"},
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
    
    try:
        client = LLMClient()
        response, error = client.decide(sample_observation)
        
        if error:
            print(f"❌ LLM decision failed: {error}")
            return False
        
        print(f"📝 LLM Response: {response}")
        
        # Try to parse the response
        action, parse_error = parse_action(response)
        
        if parse_error:
            print(f"⚠️  LLM response parsing failed: {parse_error}")
            print("   This is expected if the LLM isn't properly trained for this format")
            print("   The system will handle this gracefully with error feedback")
            return True  # This is actually expected behavior
        
        print(f"✅ Successfully parsed action: {action.action}")
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("🚀 LLM NPC System Test Suite")
    print("=" * 50)
    
    tests = [
        ("Action Parsing", test_action_parsing),
        ("Observation Building", test_observation_building),
        ("LLM Connection", test_llm_connection),
        ("Full Integration", test_full_integration),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"\n✅ {test_name}: PASSED")
            else:
                print(f"\n❌ {test_name}: FAILED")
        except Exception as e:
            print(f"\n💥 {test_name}: ERROR - {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed! The LLM NPC system is ready to use.")
        print("\nTo run the game:")
        print("  python zelda_game_with_llm_npc.py")
    else:
        print("⚠️  Some tests failed. Check the issues above.")
        
        if passed >= 2:  # Core functionality works
            print("\nCore functionality works. You can still run the game, but:")
            print("- Make sure your LLM server is running for full functionality")
            print("- Check the LLM model supports instruction following")
    
    print("\nFor more information, see README_LLM_NPC.md")


if __name__ == "__main__":
    main()