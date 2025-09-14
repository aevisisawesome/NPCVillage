"""
Tests for parse error handling.
Verifies that invalid LLM outputs result in "parse_error" feedback.
"""

import pytest
from npc.actions import parse_action
from npc.controller import NPCController


class MockNPC:
    """Mock NPC for testing"""
    def __init__(self):
        self.rect = type('Rect', (), {'x': 100, 'y': 100, 'centerx': 116, 'centery': 116})()
        self.current_health = 100
        self.is_moving = False
        self.speech_text = ""
        self.current_action = "idle"
        self.speed = 4
        
    def say(self, text):
        self.speech_text = text
    
    def move(self, dx, dy, walls, characters):
        pass
    
    def has_item(self, item_id):
        return False
    
    def remove_item(self, item_id, qty):
        return 0
    
    def add_item(self, item_id, qty):
        return True


class MockLLMClient:
    """Mock LLM client that returns configurable responses"""
    def __init__(self, response="", error=""):
        self.response = response
        self.error = error
    
    def decide(self, observation, memory=None):
        return self.response, self.error


class TestParseErrorHandling:
    """Test parse error scenarios"""
    
    def test_parse_error_invalid_json(self):
        """Test that invalid JSON returns parse_error"""
        
        invalid_json_cases = [
            "This is not JSON at all",
            "I think the player wants me to move north",
            '{"action":"say","args":{"text":"hello"}',  # Missing closing brace
            '{"action":"say""args":{"text":"hello"}}',  # Missing comma
            'null',
            '[]',
            'undefined',
            '',  # Empty string
        ]
        
        for invalid_json in invalid_json_cases:
            action, error = parse_action(invalid_json)
            assert action is None, f"Should fail for: {invalid_json}"
            assert error.startswith("parse_error"), f"Should be parse_error for: {invalid_json}, got: {error}"
    
    def test_parse_error_prose_response(self):
        """Test that prose responses return parse_error"""
        
        prose_responses = [
            "I should move north to get closer to the player.",
            "The player said hello, so I'll greet them back.",
            "Let me think about this... I'll move east.",
            "Based on the observation, I need to approach the player.",
            "```\nI'll say hello\n```",  # Code fence without JSON
        ]
        
        for prose in prose_responses:
            action, error = parse_action(prose)
            assert action is None, f"Should fail for prose: {prose}"
            assert error.startswith("parse_error"), f"Should be parse_error for prose: {prose}, got: {error}"
    
    def test_parse_error_mixed_content(self):
        """Test responses that mix prose with JSON"""
        
        mixed_responses = [
            'I think I should say hello. {"action":"say","args":{"text":"hello"}}',
            '{"action":"say","args":{"text":"hello"}} This is my response.',
            'Let me respond with: {"action":"say","args":{"text":"hello"}} to greet them.',
        ]
        
        for mixed in mixed_responses:
            action, error = parse_action(mixed)
            # These might succeed if JSON extraction works, or fail with parse_error
            if action is None:
                assert error.startswith("parse_error") or error.startswith("invalid")
    
    def test_parse_error_feedback_in_controller(self):
        """Test that parse errors are properly fed back through controller"""
        
        npc = MockNPC()
        controller = NPCController(npc, llm_endpoint="mock://test")
        
        # Mock LLM client that returns invalid JSON
        controller.llm_client = MockLLMClient(response="This is not JSON", error="")
        
        engine_state = {
            "npc": npc,
            "player": MockNPC(),
            "walls": [],
            "entities": [],
            "characters": [npc],
            "current_time": 5000,
            "player_spoke": True,
            "tick": 100
        }
        
        result = controller.npc_decision_tick(engine_state)
        
        assert result is not None
        assert result.startswith("parse_error")
        # Should be stored as last_result for next decision
        assert controller.last_result.startswith("parse_error")
    
    def test_consecutive_parse_errors_trigger_backoff(self):
        """Test that consecutive parse errors trigger error backoff"""
        
        npc = MockNPC()
        controller = NPCController(npc, llm_endpoint="mock://test")
        controller.llm_client = MockLLMClient(response="Invalid JSON", error="")
        
        engine_state = {
            "npc": npc,
            "player": MockNPC(),
            "walls": [],
            "entities": [],
            "characters": [npc],
            "current_time": 1000,
            "player_spoke": True,
            "tick": 100
        }
        
        # Trigger multiple parse errors
        for i in range(controller.max_consecutive_errors + 1):
            engine_state["current_time"] += 1000
            result = controller.npc_decision_tick(engine_state)
            if result:
                assert result.startswith("parse_error")
        
        # Should now be in backoff mode
        assert controller.consecutive_errors >= controller.max_consecutive_errors
        
        # Next decision should be skipped due to backoff (need to wait less than backoff time)
        engine_state["current_time"] += 1500  # Less than error_backoff_time (2000ms)
        engine_state["player_spoke"] = False  # No player speech to bypass backoff
        result = controller.npc_decision_tick(engine_state)
        assert result is None  # Should skip decision due to backoff
    
    def test_parse_error_recovery(self):
        """Test recovery from parse errors when valid JSON is provided"""
        
        npc = MockNPC()
        controller = NPCController(npc, llm_endpoint="mock://test")
        
        # Start with parse error
        controller.llm_client = MockLLMClient(response="Invalid JSON", error="")
        
        engine_state = {
            "npc": npc,
            "player": MockNPC(),
            "walls": [],
            "entities": [],
            "characters": [npc],
            "current_time": 1000,
            "player_spoke": True,
            "tick": 100
        }
        
        # First decision should fail
        result1 = controller.npc_decision_tick(engine_state)
        assert result1.startswith("parse_error")
        assert controller.consecutive_errors == 1
        
        # Now provide valid JSON
        controller.llm_client = MockLLMClient(
            response='{"action":"say","args":{"text":"hello"}}', 
            error=""
        )
        
        engine_state["current_time"] += 5000  # Advance time
        result2 = controller.npc_decision_tick(engine_state)
        
        # Should succeed and reset error count
        assert result2 == "ok"
        assert controller.consecutive_errors == 0
    
    def test_malformed_json_edge_cases(self):
        """Test various malformed JSON edge cases"""
        
        malformed_cases = [
            '{"action":}',  # Missing value
            '{"action":"say","args":}',  # Missing args value
            '{"action":"say","args":{"text":}}',  # Missing text value
            '{action:"say","args":{"text":"hello"}}',  # Unquoted key
            '{"action":"say","args":{"text":"hello",}}',  # Trailing comma
            '{"action":"say","args":{"text":"hello"}}extra',  # Extra content
            '{"action":"say","args":{"text":"hello"}} {"extra":"object"}',  # Multiple objects
        ]
        
        for malformed in malformed_cases:
            action, error = parse_action(malformed)
            assert action is None, f"Should fail for malformed JSON: {malformed}"
            assert error.startswith("parse_error") or error.startswith("invalid"), \
                f"Should be parse_error or invalid for: {malformed}, got: {error}"
    
    def test_code_fence_with_invalid_json(self):
        """Test code fences containing invalid JSON"""
        
        invalid_fenced_cases = [
            '```json\nThis is not JSON\n```',
            '```\n{"action":"say"\n```',  # Incomplete JSON in fence
            '```json\n{"action":"invalid_action","args":{}}\n```',  # Valid JSON, invalid action
        ]
        
        for fenced in invalid_fenced_cases:
            action, error = parse_action(fenced)
            assert action is None, f"Should fail for fenced invalid JSON: {fenced}"
            # Could be parse_error or invalid depending on what's wrong
            assert error.startswith("parse_error") or error.startswith("invalid"), \
                f"Should be error for: {fenced}, got: {error}"


def test_error_message_clarity():
    """Test that error messages are clear and helpful"""
    
    test_cases = [
        ("not json", "parse_error"),
        ('{"missing":"action"}', "invalid"),
        ('{"action":"invalid_type","args":{}}', "invalid"),
        ('{"action":"say","args":{"text":""}}', "invalid"),  # Empty text
    ]
    
    for test_input, expected_prefix in test_cases:
        action, error = parse_action(test_input)
        assert action is None
        assert error.startswith(expected_prefix)
        assert len(error) > len(expected_prefix)  # Should have descriptive message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])