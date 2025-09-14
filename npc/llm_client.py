"""
LLM client for NPC decision-making.
Handles communication with local LLM endpoint and enforces strict JSON output.
"""

import requests
import json
import os
import time
from typing import Dict, Any, Optional, Tuple


class LLMClient:
    """Client for communicating with local LLM for NPC decisions"""
    
    def __init__(self, endpoint: str = None):
        self.endpoint = endpoint or os.getenv("LLM_ENDPOINT", "http://127.0.0.1:1234/v1/chat/completions")
        self.model = os.getenv("LOCAL_LLM_MODEL", "local-model")
        self.temperature = float(os.getenv("LLM_TEMP", "0.4"))
        self.timeout = 10
        self.max_retries = 2
        
        # Load system prompt from file
        try:
            with open("lm_studio_system_prompt_new.txt", "r", encoding="utf-8") as f:
                self.system_prompt = f.read().strip()
                print(f"DEBUG: Loaded system prompt ({len(self.system_prompt)} characters)")
        except FileNotFoundError:
            print("WARNING: System prompt file not found, using empty prompt")
            self.system_prompt = ""
    
    def decide(self, observation: Dict[str, Any], memory: Optional[str] = None) -> Tuple[str, str]:
        """
        Get LLM decision based on observation.
        
        Args:
            observation: World observation dictionary
            memory: Optional memory/context string
            
        Returns:
            tuple: (raw_response, error_message)
            If successful: (json_string, "")
            If failed: ("", error_description)
        """
        
        # Format observation for LLM
        obs_json = json.dumps(observation, indent=2)
        
        # Build user message
        user_message = f"OBSERVATION:\n{obs_json}"
        if memory:
            user_message = f"MEMORY:\n{memory}\n\n{user_message}"
        
        # *** DEBUG: Log the complete user message being sent to LLM ***
        print("=" * 80)
        print("DEBUG: SYSTEM PROMPT:")
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
        """Make HTTP request to LLM endpoint"""
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": 150,  # Keep responses short
            "stop": ["\n\n", "```"]  # Stop on double newline or code fences
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
        
        content = data["choices"][0].get("message", {}).get("content", "").strip()
        
        if not content:
            raise Exception("Empty response content")
        
        # Clean up response - remove any non-JSON content
        content = self._extract_json(content)
        
        return content
    
    def _extract_json(self, text: str) -> str:
        """Extract JSON from potentially messy LLM output"""
        
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
        """Test if LLM endpoint is reachable"""
        try:
            test_messages = [
                {"role": "system", "content": "You are a test assistant."},
                {"role": "user", "content": "Respond with exactly: {\"test\":\"ok\"}"}
            ]
            
            response = self._make_request(test_messages)
            return response is not None and "test" in response
            
        except Exception as e:
            print(f"LLM connection test failed: {e}")
            return False


def test_llm_client():
    """Test the LLM client with sample observation"""
    
    client = LLMClient()
    
    # Test connection first
    print("Testing LLM connection...")
    if not client.test_connection():
        print("❌ LLM connection failed - make sure your local LLM server is running")
        return
    
    print("✅ LLM connection successful")
    
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
    
    print("\nTesting LLM decision-making...")
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
    test_llm_client()