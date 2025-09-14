"""
Configuration for LLM integration modes
"""

# LLM Integration Mode
# Set to True to use tool calls (cleaner, structured)
# Set to False to use JSON parsing (fallback mode)
USE_TOOL_CALLS = True

# LLM Endpoint Configuration
LLM_ENDPOINT = "http://127.0.0.1:1234/v1/chat/completions"
LLM_MODEL = "local-model"
LLM_TEMPERATURE = 0.4

def get_llm_config():
    """Get current LLM configuration"""
    return {
        "use_tool_calls": USE_TOOL_CALLS,
        "endpoint": LLM_ENDPOINT,
        "model": LLM_MODEL,
        "temperature": LLM_TEMPERATURE
    }

def print_config_info():
    """Print current configuration info"""
    mode = "Tool Calls" if USE_TOOL_CALLS else "JSON Parsing"
    print(f"LLM Mode: {mode}")
    print(f"Endpoint: {LLM_ENDPOINT}")
    print(f"Model: {LLM_MODEL}")
    print(f"Temperature: {LLM_TEMPERATURE}")