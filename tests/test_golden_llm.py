"""
Golden test for LLM decision-making.
Tests that given a simple map + observation, LLM chooses a legal move_dir.
This test requires a running LLM server and may be skipped in CI.
"""

import pytest
import json
import os
from npc.llm_client import LLMClient
from npc.actions import parse_action


@pytest.mark.skipif(
    os.getenv("SKIP_LLM_TESTS", "false").lower() == "true",
    reason="LLM tests skipped (set SKIP_LLM_TESTS=false to enable)"
)
class TestGoldenLLM:
    """Golden tests for LLM decision-making"""
    
    def setup_method(self):
        """Set up LLM client for testing"""
        self.llm_client = LLMClient()
        
        # Test connection first
        if not self.llm_client.test_connection():
            pytest.skip("LLM server not available")
    
    def test_simple_approach_scenario(self):
        """Golden test: NPC should move toward player"""
        
        # Simple scenario: NPC at (10,5), Player at (13,5), clear path east
        observation = {
            "npc": {"pos": [10, 5], "hp": 100, "state": "Idle"},
            "player": {"pos": [13, 5], "last_said": "hello"},
            "local_tiles": {
                "origin": [5, 0],
                "grid": [
                    "###########",
                    "#.........#",
                    "#.........#",
                    "#.........#",
                    "#.........#",
                    "#..N..P...#",  # NPC at col 2, Player at col 5
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
        
        # Get LLM decision
        response, error = self.llm_client.decide(observation)
        
        assert error == "", f"LLM request failed: {error}"
        assert response, "LLM returned empty response"
        
        # Parse the action
        action, parse_error = parse_action(response)
        
        assert parse_error == "", f"Failed to parse LLM response: {parse_error}\nResponse: {response}"
        assert action is not None, "Parsed action is None"
        
        # Verify it's a legal action
        assert action.action in ["say", "move_dir", "move_to", "interact"], \
            f"Invalid action type: {action.action}"
        
        # For this scenario, expect movement toward player (east)
        if action.action == "move_dir":
            assert action.args.direction == "E", \
                f"Expected eastward movement, got: {action.args.direction}"
        elif action.action == "move_to":
            # Should target a position closer to or at the player
            target_x = action.args.x
            assert target_x > 10, f"Expected eastward target, got x={target_x}"
        elif action.action == "say":
            # Saying something is also reasonable for greeting
            assert len(action.args.text) > 0, "Say action has empty text"
            assert len(action.args.text) <= 100, "Say text too long"
    
    def test_blocked_path_scenario(self):
        """Golden test: NPC should find alternate route when direct path blocked"""
        
        # Scenario: NPC at (10,5), Player at (13,5), wall blocking direct east path
        observation = {
            "npc": {"pos": [10, 5], "hp": 100, "state": "Idle"},
            "player": {"pos": [13, 5], "last_said": None},
            "local_tiles": {
                "origin": [5, 0],
                "grid": [
                    "###########",
                    "#.........#",
                    "#.........#",
                    "#.........#",
                    "#..#......#",  # Wall blocking row 4
                    "#..N#.P...#",  # NPC at (10,5), wall at (11,5), Player at (13,5)
                    "#..#......#",  # Wall blocking row 6
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
            "tick": 200
        }
        
        response, error = self.llm_client.decide(observation)
        
        assert error == "", f"LLM request failed: {error}"
        
        action, parse_error = parse_action(response)
        
        assert parse_error == "", f"Failed to parse LLM response: {parse_error}\nResponse: {response}"
        assert action is not None
        
        # Should not try to move directly east (blocked)
        if action.action == "move_dir":
            assert action.args.direction != "E", \
                "Should not move east into wall"
            # Should try north or south to go around
            assert action.args.direction in ["N", "S"], \
                f"Expected north/south movement to go around wall, got: {action.args.direction}"
    
    def test_player_speech_response(self):
        """Golden test: NPC should respond to player speech"""
        
        observation = {
            "npc": {"pos": [10, 5], "hp": 100, "state": "Idle"},
            "player": {"pos": [11, 5], "last_said": "What do you have for sale?"},
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
            "tick": 300
        }
        
        response, error = self.llm_client.decide(observation)
        
        assert error == "", f"LLM request failed: {error}"
        
        action, parse_error = parse_action(response)
        
        assert parse_error == "", f"Failed to parse LLM response: {parse_error}\nResponse: {response}"
        assert action is not None
        
        # Should respond with speech when player asks about inventory
        assert action.action == "say", \
            f"Expected 'say' action in response to player question, got: {action.action}"
        
        # Response should be relevant to shopkeeper role
        response_text = action.args.text.lower()
        assert any(word in response_text for word in ["have", "sell", "stock", "goods", "items"]), \
            f"Response should mention inventory/goods: {action.args.text}"
    
    def test_cooldown_respect(self):
        """Golden test: NPC should respect cooldowns"""
        
        observation = {
            "npc": {"pos": [10, 5], "hp": 100, "state": "Idle"},
            "player": {"pos": [13, 5], "last_said": None},
            "local_tiles": {
                "origin": [5, 0],
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
            "visible_entities": [],
            "goals": ["greet player"],
            "cooldowns": {"move": 1000, "interact": 500},  # Both on cooldown
            "last_result": None,
            "tick": 400
        }
        
        response, error = self.llm_client.decide(observation)
        
        assert error == "", f"LLM request failed: {error}"
        
        action, parse_error = parse_action(response)
        
        assert parse_error == "", f"Failed to parse LLM response: {parse_error}\nResponse: {response}"
        assert action is not None
        
        # Should not try actions that are on cooldown
        assert action.action not in ["move_dir", "move_to", "interact"], \
            f"Should not use actions on cooldown, got: {action.action}"
        
        # Should use say action instead
        assert action.action == "say", \
            f"Expected 'say' action when movement/interact on cooldown, got: {action.action}"
    
    def test_last_result_adaptation(self):
        """Golden test: NPC should adapt based on last_result feedback"""
        
        observation = {
            "npc": {"pos": [10, 5], "hp": 100, "state": "Idle"},
            "player": {"pos": [13, 5], "last_said": None},
            "local_tiles": {
                "origin": [5, 0],
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
            "visible_entities": [],
            "goals": ["greet player"],
            "cooldowns": {"move": 0, "interact": 0},
            "last_result": "blocked:wall",  # Previous action was blocked
            "tick": 500
        }
        
        response, error = self.llm_client.decide(observation)
        
        assert error == "", f"LLM request failed: {error}"
        
        action, parse_error = parse_action(response)
        
        assert parse_error == "", f"Failed to parse LLM response: {parse_error}\nResponse: {response}"
        assert action is not None
        
        # Should be a valid action
        assert action.action in ["say", "move_dir", "move_to", "interact"]
        
        # If choosing movement, should try a different direction or approach
        # (This is harder to test definitively without knowing the previous action)


@pytest.mark.skipif(
    os.getenv("SKIP_LLM_TESTS", "false").lower() == "true",
    reason="LLM tests skipped"
)
def test_llm_output_format_consistency():
    """Test that LLM consistently outputs valid JSON format"""
    
    client = LLMClient()
    
    if not client.test_connection():
        pytest.skip("LLM server not available")
    
    # Test multiple similar scenarios to check consistency
    base_observation = {
        "npc": {"pos": [10, 5], "hp": 100, "state": "Idle"},
        "player": {"pos": [12, 5], "last_said": None},
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
    
    # Test multiple requests
    for i in range(3):
        observation = base_observation.copy()
        observation["tick"] = 100 + i * 100
        
        response, error = client.decide(observation)
        
        assert error == "", f"Request {i+1} failed: {error}"
        
        action, parse_error = parse_action(response)
        
        assert parse_error == "", f"Request {i+1} parse failed: {parse_error}\nResponse: {response}"
        assert action is not None, f"Request {i+1} returned None action"
        
        # Should be consistent format
        assert hasattr(action, 'action'), "Action missing 'action' field"
        assert hasattr(action, 'args'), "Action missing 'args' field"


if __name__ == "__main__":
    # Run with: python -m pytest tests/test_golden_llm.py -v
    # Or skip LLM tests: SKIP_LLM_TESTS=true python -m pytest tests/test_golden_llm.py -v
    pytest.main([__file__, "-v"])