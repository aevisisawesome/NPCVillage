#!/usr/bin/env python3
"""
Test the specific issue with 'navigate to player position' command.
"""

from npc.actions import parse_action
import json

def test_current_issue():
    """Test the specific parsing issue"""
    
    print("🔍 Current Issue Analysis")
    print("=" * 50)
    
    # This is what the LLM returned
    llm_response = '{"action":"move_to","args":{"direction":"S","distance":3.0}}'
    
    print(f"LLM Response: {llm_response}")
    
    # Try to parse it
    action, error = parse_action(llm_response)
    
    if error:
        print(f"❌ Parse Error: {error}")
        print("\n🔍 Problem Analysis:")
        print("- LLM used 'move_to' action")
        print("- But provided 'direction' and 'distance' args")
        print("- 'move_to' expects 'x' and 'y' coordinates")
        print("- 'direction' and 'distance' are for 'move' action")
    else:
        print(f"✅ Parsed successfully: {action}")
    
    print(f"\n✅ Correct Responses for 'navigate to player position':")
    
    # Show correct formats
    correct_responses = [
        '{"action":"move","args":{"direction":"S","distance":2.0}}',
        '{"action":"move","args":{"direction":"E","distance":1.5}}',
        '{"action":"move","args":{"direction":"W","distance":1.0}}',
    ]
    
    for i, response in enumerate(correct_responses, 1):
        print(f"\nOption {i}: {response}")
        action, error = parse_action(response)
        if action:
            print(f"  ✅ Parses correctly: {action.action} {action.args.direction} {action.args.distance} tiles")
        else:
            print(f"  ❌ Error: {error}")
    
    print(f"\n❌ Incorrect Response (what LLM did):")
    print(f"{llm_response}")
    print("  ❌ Wrong: move_to action with direction/distance args")
    
    print(f"\n🎯 Solution:")
    print("1. Update LM Studio system prompt with the corrected version")
    print("2. The updated prompt clarifies when to use 'move' vs 'move_to'")
    print("3. 'navigate to player' should use 'move' action with direction")
    print("4. 'move_to' is only for exact coordinates like 'go to 10,5'")


def test_move_to_correct_usage():
    """Test correct move_to usage"""
    
    print(f"\n🎯 Correct move_to Usage Examples")
    print("-" * 40)
    
    correct_move_to_examples = [
        '{"action":"move_to","args":{"x":10,"y":5}}',
        '{"action":"move_to","args":{"x":15,"y":20}}',
        '{"action":"move_to","args":{"x":0,"y":0}}',
    ]
    
    for example in correct_move_to_examples:
        print(f"\nTesting: {example}")
        action, error = parse_action(example)
        if action:
            print(f"  ✅ Valid: move_to to ({action.args.x}, {action.args.y})")
        else:
            print(f"  ❌ Error: {error}")


if __name__ == "__main__":
    test_current_issue()
    test_move_to_correct_usage()