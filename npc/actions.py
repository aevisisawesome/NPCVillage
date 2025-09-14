"""
Action schema and validation for LLM-driven NPC behavior.
Defines strict JSON schemas for NPC actions and validates LLM outputs.
"""

from pydantic import BaseModel, Field, ValidationError
from typing import Literal, Union
import json


class SayArgs(BaseModel):
    text: str = Field(..., min_length=1, max_length=100, description="Text to say (1-100 chars)")


class MoveArgs(BaseModel):
    direction: Literal["N", "E", "S", "W"] = Field(..., description="Direction to move")
    distance: float = Field(..., ge=0.1, le=5.0, description="Distance in tiles (0.5=short, 1.0=medium, 3.0=long)")


class MoveToArgs(BaseModel):
    x: int = Field(..., description="Target X coordinate")
    y: int = Field(..., description="Target Y coordinate")


class InteractArgs(BaseModel):
    entity_id: str = Field(..., description="ID of entity to interact with")


class TransferItemArgs(BaseModel):
    entity_id: str = Field(..., description="ID of entity to transfer item to")
    item_id: str = Field(..., description="ID of item to transfer")


class Action(BaseModel):
    action: Literal["say", "move", "move_to", "interact", "transfer_item"]
    args: Union[SayArgs, MoveArgs, MoveToArgs, InteractArgs, TransferItemArgs]

    model_config = {"extra": "forbid"}  # Reject any extra fields
    
    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs):
        super().__pydantic_init_subclass__(**kwargs)
        cls.model_config = {"extra": "forbid"}


def parse_action(raw_text: str) -> tuple[Action, str]:
    """
    Parse raw LLM output into a validated Action object.
    
    Args:
        raw_text: Raw text from LLM (should be JSON)
        
    Returns:
        tuple: (Action object, error_message)
        If successful: (action, "")
        If failed: (None, error_description)
    """
    try:
        # Clean the input - remove code fences and extra whitespace
        cleaned_text = raw_text.strip()
        if cleaned_text.startswith("```"):
            lines = cleaned_text.split('\n')
            # Find first line that looks like JSON
            for i, line in enumerate(lines):
                if line.strip().startswith('{'):
                    # Take from this line until we find closing }
                    json_lines = []
                    brace_count = 0
                    for j in range(i, len(lines)):
                        json_lines.append(lines[j])
                        brace_count += lines[j].count('{') - lines[j].count('}')
                        if brace_count == 0 and '{' in lines[j]:
                            break
                    cleaned_text = '\n'.join(json_lines)
                    break
        
        # Parse JSON
        try:
            data = json.loads(cleaned_text)
        except json.JSONDecodeError as e:
            return None, f"parse_error: Invalid JSON - {str(e)}"
        
        # Validate required fields
        if not isinstance(data, dict):
            return None, "parse_error: Root must be JSON object"
        
        if "action" not in data:
            return None, "invalid: Missing 'action' field"
        
        if "args" not in data:
            return None, "invalid: Missing 'args' field"
        
        action_type = data["action"]
        args_data = data["args"]
        
        # Validate action type and create appropriate args object
        if action_type == "say":
            args = SayArgs(**args_data)
        elif action_type == "move":
            args = MoveArgs(**args_data)
        elif action_type == "move_to":
            args = MoveToArgs(**args_data)
        elif action_type == "interact":
            args = InteractArgs(**args_data)
        elif action_type == "transfer_item":
            args = TransferItemArgs(**args_data)
        else:
            return None, f"invalid: Unknown action type '{action_type}'"
        
        # Check for extra fields at the root level
        allowed_fields = {"action", "args"}
        extra_fields = set(data.keys()) - allowed_fields
        if extra_fields:
            return None, f"invalid: Extra fields not allowed: {', '.join(extra_fields)}"
        
        # Create and validate the full action
        action = Action(action=action_type, args=args)
        return action, ""
        
    except ValidationError as e:
        # Extract the first error for a cleaner message
        error_details = e.errors()[0]
        field = error_details.get('loc', ['unknown'])[0]
        msg = error_details.get('msg', 'validation error')
        return None, f"invalid: {field} - {msg}"
    
    except Exception as e:
        return None, f"parse_error: {str(e)}"


def validate_action_schema():
    """Test function to validate the action schema works correctly"""
    test_cases = [
        # Valid cases
        ('{"action":"say","args":{"text":"Hello!"}}', True),
        ('{"action":"move_dir","args":{"direction":"N"}}', True),
        ('{"action":"move_to","args":{"x":10,"y":5}}', True),
        ('{"action":"interact","args":{"entity_id":"door_1"}}', True),
        
        # Invalid cases
        ('{"action":"invalid","args":{}}', False),
        ('{"args":{"text":"Hello!"}}', False),  # Missing action
        ('{"action":"say"}', False),  # Missing args
        ('{"action":"say","args":{"text":""}}', False),  # Empty text
        ('{"action":"move_dir","args":{"direction":"NORTH"}}', False),  # Invalid direction
        ('not json', False),
        ('{"action":"say","args":{"text":"Hello!"},"extra":"field"}', False),  # Extra field
    ]
    
    for test_input, should_succeed in test_cases:
        action, error = parse_action(test_input)
        success = action is not None
        print(f"Input: {test_input}")
        print(f"Expected: {'SUCCESS' if should_succeed else 'FAIL'}, Got: {'SUCCESS' if success else 'FAIL'}")
        if not success:
            print(f"Error: {error}")
        print("---")


if __name__ == "__main__":
    validate_action_schema()