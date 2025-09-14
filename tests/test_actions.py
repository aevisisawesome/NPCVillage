"""
Unit tests for action schema validation.
Tests happy paths and edge cases for LLM action parsing.
"""

import pytest
from npc.actions import parse_action, Action


class TestActionParsing:
    """Test action parsing and validation"""
    
    def test_valid_say_action(self):
        """Test valid say action"""
        json_input = '{"action":"say","args":{"text":"Hello traveler!"}}'
        action, error = parse_action(json_input)
        
        assert error == ""
        assert action is not None
        assert action.action == "say"
        assert action.args.text == "Hello traveler!"
    
    def test_valid_move_dir_actions(self):
        """Test all valid move_dir actions"""
        directions = ["N", "E", "S", "W"]
        
        for direction in directions:
            json_input = f'{{"action":"move_dir","args":{{"direction":"{direction}"}}}}'
            action, error = parse_action(json_input)
            
            assert error == "", f"Failed for direction {direction}: {error}"
            assert action is not None
            assert action.action == "move_dir"
            assert action.args.direction == direction
    
    def test_valid_move_to_action(self):
        """Test valid move_to action"""
        json_input = '{"action":"move_to","args":{"x":10,"y":5}}'
        action, error = parse_action(json_input)
        
        assert error == ""
        assert action is not None
        assert action.action == "move_to"
        assert action.args.x == 10
        assert action.args.y == 5
    
    def test_valid_interact_action(self):
        """Test valid interact action"""
        json_input = '{"action":"interact","args":{"entity_id":"door_1"}}'
        action, error = parse_action(json_input)
        
        assert error == ""
        assert action is not None
        assert action.action == "interact"
        assert action.args.entity_id == "door_1"
    
    def test_valid_transfer_item_action(self):
        """Test valid transfer_item action"""
        json_input = '{"action":"transfer_item","args":{"entity_id":"player","item_id":"health_potion"}}'
        action, error = parse_action(json_input)
        
        assert error == ""
        assert action is not None
        assert action.action == "transfer_item"
        assert action.args.entity_id == "player"
        assert action.args.item_id == "health_potion"
    
    def test_invalid_json(self):
        """Test invalid JSON input"""
        invalid_inputs = [
            "not json at all",
            '{"action":"say"',  # Incomplete JSON
            '{"action":"say","args":{"text":"hello"}',  # Missing closing brace
            'null',
            '[]',  # Array instead of object
        ]
        
        for invalid_input in invalid_inputs:
            action, error = parse_action(invalid_input)
            assert action is None
            assert error.startswith("parse_error")
    
    def test_missing_required_fields(self):
        """Test missing required fields"""
        test_cases = [
            ('{"args":{"text":"hello"}}', "action"),  # Missing action
            ('{"action":"say"}', "args"),  # Missing args
            ('{}', "action"),  # Empty object
        ]
        
        for json_input, expected_field in test_cases:
            action, error = parse_action(json_input)
            assert action is None
            assert error.startswith("invalid")
            assert expected_field in error.lower()
    
    def test_invalid_action_types(self):
        """Test invalid action types"""
        invalid_actions = [
            "invalid_action",
            "MOVE_DIR",  # Wrong case
            "move",  # Incomplete
            "say_something",  # Wrong format
        ]
        
        for invalid_action in invalid_actions:
            json_input = f'{{"action":"{invalid_action}","args":{{}}}}'
            action, error = parse_action(json_input)
            assert action is None
            assert error.startswith("invalid")
            assert "action type" in error.lower()
    
    def test_invalid_direction(self):
        """Test invalid directions for move_dir"""
        invalid_directions = [
            "NORTH",  # Full word
            "n",      # Lowercase
            "UP",     # Wrong direction
            "NE",     # Diagonal
            "",       # Empty
        ]
        
        for invalid_dir in invalid_directions:
            json_input = f'{{"action":"move_dir","args":{{"direction":"{invalid_dir}"}}}}'
            action, error = parse_action(json_input)
            assert action is None
            assert error.startswith("invalid")
    
    def test_invalid_coordinates(self):
        """Test invalid coordinates for move_to"""
        invalid_coords = [
            ('{"action":"move_to","args":{"x":"ten","y":5}}', "string instead of int"),
            ('{"action":"move_to","args":{"x":10}}', "missing y"),
            ('{"action":"move_to","args":{"y":5}}', "missing x"),
            ('{"action":"move_to","args":{}}', "missing both"),
        ]
        
        for json_input, description in invalid_coords:
            action, error = parse_action(json_input)
            assert action is None, f"Should fail for {description}"
            assert error.startswith("invalid")
    
    def test_empty_text_in_say(self):
        """Test empty text in say action"""
        json_input = '{"action":"say","args":{"text":""}}'
        action, error = parse_action(json_input)
        assert action is None
        assert error.startswith("invalid")
    
    def test_extra_fields_rejected(self):
        """Test that extra fields are rejected"""
        json_input = '{"action":"say","args":{"text":"hello"},"extra_field":"value"}'
        action, error = parse_action(json_input)
        assert action is None
        assert error.startswith("invalid") or error.startswith("parse_error")
    
    def test_code_fence_removal(self):
        """Test that code fences are properly removed"""
        json_with_fences = '''```json
{"action":"say","args":{"text":"Hello!"}}
```'''
        
        action, error = parse_action(json_with_fences)
        assert error == ""
        assert action is not None
        assert action.action == "say"
        assert action.args.text == "Hello!"
    
    def test_whitespace_handling(self):
        """Test that extra whitespace is handled"""
        json_with_whitespace = '''
        
        {"action":"say","args":{"text":"Hello!"}}
        
        '''
        
        action, error = parse_action(json_with_whitespace)
        assert error == ""
        assert action is not None
        assert action.action == "say"


def test_schema_validation_comprehensive():
    """Comprehensive test of the schema validation"""
    from npc.actions import validate_action_schema
    
    # This will print results but not assert - just make sure it runs
    validate_action_schema()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])