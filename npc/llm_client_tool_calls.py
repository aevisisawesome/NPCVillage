"""
Updated LLM client for NPC decision-making using proper tool calls.
Handles communication with local LLM endpoint using function calling instead of JSON parsing.
"""

import requests
import json
import os
import time
from typing import Dict, Any, Optional, Tuple, List


class LLMClientToolCalls:
    """Client for communicating with local LLM using tool calls for NPC decisions"""
    
    def __init__(self, endpoint: str = None):
        self.endpoint = endpoint or os.getenv("LLM_ENDPOINT", "http://127.0.0.1:1234/v1/chat/completions")
        self.model = os.getenv("LOCAL_LLM_MODEL", "local-model")
        self.temperature = float(os.getenv("LLM_TEMP", "0.4"))
        self.timeout = 10
        self.max_retries = 2
        
        # Load system prompt from file
        try:
            with open("lm_studio_system_prompt_tool_calls.txt", "r", encoding="utf-8") as f:
                self.system_prompt = f.read().strip()
                print(f"DEBUG: Loaded tool calls system prompt ({len(self.system_prompt)} characters)")
        except FileNotFoundError:
            print("WARNING: Tool calls system prompt file not found, using default")
            self.system_prompt = self._get_default_system_prompt()
        
        # Define available tools/functions
        self.tools = self._define_tools()
    
    def _get_default_system_prompt(self) -> str:
        """Default system prompt for tool calls"""
        return """You are Garruk Ironhand, a grizzled shopkeeper in a fantasy world. You're blunt, impatient, and speak in short sentences. Stay in character - never acknowledge being an AI or part of a game.

BEHAVIOR:
- When player greets you → use say function to greet back
- When player asks questions → use say function to answer
- When player asks you to move in a direction → use move function
- When player asks you to move to a location → use move_to function
- When player asks about items → use say function to list what you have
- Keep spoken responses under 10 words
- Don't interact with objects unless specifically asked

INVENTORY RULES:
- Your current inventory is listed in the observation under "npc.inventory"
- Only mention items that are actually in your inventory
- Don't make up items that aren't listed

Use the appropriate function for each action. Choose movement distances based on context:
- Small movements: 0.5 tiles
- Normal movements: 1.0 tiles  
- Large movements: 3.0 tiles"""
    
    def _define_tools(self) -> List[Dict[str, Any]]:
        """Define the available tools/functions for the NPC"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "say",
                    "description": "Make the NPC say something to the player",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "text": {
                                "type": "string",
                                "description": "What the NPC should say (keep under 10 words)",
                                "minLength": 1,
                                "maxLength": 100
                            }
                        },
                        "required": ["text"],
                        "additionalProperties": False
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "move",
                    "description": "Move the NPC in a specific direction",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "direction": {
                                "type": "string",
                                "enum": ["N", "E", "S", "W"],
                                "description": "Direction to move (N=North, E=East, S=South, W=West)"
                            },
                            "distance": {
                                "type": "number",
                                "minimum": 0.1,
                                "maximum": 5.0,
                                "description": "Distance in tiles (0.5=short, 1.0=medium, 3.0=long)"
                            }
                        },
                        "required": ["direction", "distance"],
                        "additionalProperties": False
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "move_to",
                    "description": "Move the NPC to specific coordinates",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "x": {
                                "type": "integer",
                                "description": "Target X coordinate"
                            },
                            "y": {
                                "type": "integer",
                                "description": "Target Y coordinate"
                            }
                        },
                        "required": ["x", "y"],
                        "additionalProperties": False
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "interact",
                    "description": "Interact with an entity (door, chest, etc.)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "entity_id": {
                                "type": "string",
                                "description": "ID of the entity to interact with"
                            }
                        },
                        "required": ["entity_id"],
                        "additionalProperties": False
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "transfer_item",
                    "description": "Transfer an item to another entity",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "entity_id": {
                                "type": "string",
                                "description": "ID of the entity to transfer item to"
                            },
                            "item_id": {
                                "type": "string",
                                "description": "ID of the item to transfer"
                            }
                        },
                        "required": ["entity_id", "item_id"],
                        "additionalProperties": False
                    }
                }
            }
        ]
    
    def decide(self, observation: Dict[str, Any], memory: Optional[str] = None) -> Tuple[str, str]:
        """
        Get LLM decision based on observation using tool calls.
        
        Args:
            observation: World observation dictionary
            memory: Optional memory/context string
            
        Returns:
            tuple: (json_string, error_message)
            If successful: (json_string_of_action, "")
            If failed: ("", error_description)
        """
        
        # Format observation for LLM
        obs_json = json.dumps(observation, indent=2)
        
        # Extract player message from observation
        player_message = observation.get("player", {}).get("last_said", "")
        
        # Build user message with consistent format
        user_message_parts = [
            "SYSTEM_REMINDER:",
            "- Output **one** JSON object. No extra text.",
            "- If unsure, ask a 1-line question via `say`.",
            ""
        ]
        
        # Add dialogue context if available
        if memory and "RECENT CONVERSATION:" in memory:
            user_message_parts.extend([
                memory,
                ""
            ])
        
        # Add observation
        user_message_parts.extend([
            "OBSERVATION:",
            obs_json,
            ""
        ])
        
        # Add player message
        if player_message:
            user_message_parts.extend([
                "PLAYER_MESSAGE:",
                f'"{player_message}"'
            ])
        
        user_message = "\n".join(user_message_parts)
        
        # *** DEBUG: Log the complete user message being sent to LLM ***
        print("=" * 80)
        print("DEBUG: TOOL CALLS SYSTEM PROMPT:")
        print("=" * 80)
        print(self.system_prompt[:200] + "..." if len(self.system_prompt) > 200 else self.system_prompt)
        print("=" * 80)
        print("DEBUG: USER MESSAGE BEING SENT TO LLM:")
        print("=" * 80)
        print(user_message)
        print("=" * 80)
        
        # Prepare messages
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        # Try request with retries
        for attempt in range(self.max_retries + 1):
            try:
                response = self._make_request(messages)
                if response:
                    return response, ""
                    
            except Exception as e:
                print(f"LLM request attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries:
                    time.sleep(0.5 * (attempt + 1))  # Exponential backoff
                    continue
                else:
                    return "", f"request_failed: {str(e)}"
        
        return "", "request_failed: Max retries exceeded"
    
    def _make_request(self, messages) -> Optional[str]:
        """Make HTTP request to LLM endpoint with tool calls"""
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": 150,
            "tools": self.tools,
            "tool_choice": "auto"  # Let the model decide when to use tools
        }
        
        response = requests.post(
            self.endpoint,
            json=payload,
            timeout=self.timeout,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code != 200:
            raise Exception(f"HTTP {response.status_code}: {response.text}")
        
        data = response.json()
        
        if "choices" not in data or not data["choices"]:
            raise Exception("No choices in response")
        
        choice = data["choices"][0]
        message = choice.get("message", {})
        
        # Check if the model used tool calls
        tool_calls = message.get("tool_calls", [])
        
        if tool_calls:
            # Process the first tool call (NPCs should only make one action at a time)
            tool_call = tool_calls[0]
            function_name = tool_call["function"]["name"]
            function_args = json.loads(tool_call["function"]["arguments"])
            
            print(f"DEBUG: Tool call received - {function_name}: {function_args}")
            
            # Convert tool call back to our expected JSON format
            result = {
                "action": function_name,
                "args": function_args
            }
            
            return json.dumps(result)
        
        # Fallback to regular content if no tool calls (shouldn't happen with proper setup)
        content = message.get("content", "").strip()
        if content:
            print(f"DEBUG: Received regular content instead of tool call: {content}")
            # Try to extract JSON from content as fallback
            return self._extract_json(content)
        
        raise Exception("No tool calls or content in response")
    
    def _extract_json(self, text: str) -> str:
        """Extract JSON from potentially messy LLM output (fallback method)"""
        
        # Remove code fences
        if "```" in text:
            parts = text.split("```")
            for part in parts:
                part = part.strip()
                if part.startswith("json"):
                    part = part[4:].strip()
                if part.startswith("{") and part.endswith("}"):
                    return part
        
        # Find JSON object boundaries
        start_idx = text.find("{")
        if start_idx == -1:
            return text.strip()
        
        # Find matching closing brace
        brace_count = 0
        end_idx = start_idx
        
        for i in range(start_idx, len(text)):
            if text[i] == "{":
                brace_count += 1
            elif text[i] == "}":
                brace_count -= 1
                if brace_count == 0:
                    end_idx = i
                    break
        
        if brace_count == 0:
            return text[start_idx:end_idx + 1]
        
        return text.strip()
    
    def test_connection(self) -> bool:
        """Test if LLM endpoint is reachable and supports tool calls"""
        try:
            test_messages = [
                {"role": "system", "content": "You are a test assistant. Use the test_function when asked."},
                {"role": "user", "content": "Please call the test function with message 'hello'"}
            ]
            
            test_tools = [
                {
                    "type": "function",
                    "function": {
                        "name": "test_function",
                        "description": "A test function",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "message": {"type": "string"}
                            },
                            "required": ["message"]
                        }
                    }
                }
            ]
            
            payload = {
                "model": self.model,
                "messages": test_messages,
                "temperature": 0.1,
                "max_tokens": 50,
                "tools": test_tools,
                "tool_choice": "auto"
            }
            
            response = requests.post(
                self.endpoint,
                json=payload,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code != 200:
                return False
            
            data = response.json()
            choice = data.get("choices", [{}])[0]
            message = choice.get("message", {})
            tool_calls = message.get("tool_calls", [])
            
            return len(tool_calls) > 0
            
        except Exception as e:
            print(f"LLM tool calls connection test failed: {e}")
            return False


def test_llm_client_tool_calls():
    """Test the LLM client with tool calls using sample observation"""
    
    client = LLMClientToolCalls()
    
    # Test connection first
    print("Testing LLM connection with tool calls...")
    if not client.test_connection():
        print("❌ LLM tool calls connection failed - make sure your local LLM server supports function calling")
        return
    
    print("✅ LLM tool calls connection successful")
    
    # Test with sample observation
    sample_observation = {
        "npc": {"pos": [10, 5], "hp": 7, "state": "Approach"},
        "player": {"pos": [13, 5], "last_said": "hello"},
        "local_tiles": {
            "origin": [5, 0],
            "grid": [
                "###########",
                "#.........#",
                "#...D.....#",
                "#....#....#",
                "#....#....#",
                "#..N.P....#",
                "#.........#",
                "#.........#",
                "#.........#",
                "#.........#",
                "###########"
            ]
        },
        "visible_entities": [{"id": "door_12_2", "kind": "door", "pos": [12, 2]}],
        "goals": ["greet player"],
        "cooldowns": {"move": 0, "interact": 0},
        "last_result": None,
        "tick": 12345
    }
    
    print("\nTesting LLM decision-making with tool calls...")
    print("Sample observation:")
    print(json.dumps(sample_observation, indent=2))
    
    response, error = client.decide(sample_observation)
    
    if error:
        print(f"❌ LLM decision failed: {error}")
    else:
        print(f"✅ LLM response: {response}")
        
        # Try to parse the response
        try:
            parsed = json.loads(response)
            print(f"✅ Valid JSON structure: {parsed}")
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON in response: {e}")


if __name__ == "__main__":
    test_llm_client_tool_calls()