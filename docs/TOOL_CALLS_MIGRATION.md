# Tool Calls Migration Guide

## Overview

This update converts your Zelda game from manual JSON parsing to proper LM Studio tool calls for Qwen3 7B. This provides:

- ✅ Cleaner logs (no more empty `tool_calls: []` messages)
- ✅ More reliable JSON parsing (LM Studio handles it)
- ✅ Better structured function calls
- ✅ Less chance of malformed responses

## What Changed

### Before (JSON Parsing)
- Model outputs text that looks like JSON
- You parse it manually in Python
- LM Studio shows `tool_calls: []` because it doesn't recognize function calls
- Risk of malformed JSON or extra text

### After (Tool Calls)
- You declare available functions upfront
- Model is guided to emit structured calls
- LM Studio parses automatically into `tool_calls`
- Cleaner logs and more reliable parsing

## Files Added/Modified

### New Files
- `npc/llm_client_tool_calls.py` - New LLM client using tool calls
- `lm_studio_system_prompt_tool_calls.txt` - Updated system prompt for tool calls
- `llm_config.py` - Configuration to switch between modes
- `test_tool_calls.py` - Test script to verify setup
- `TOOL_CALLS_MIGRATION.md` - This guide

### Modified Files
- `npc/controller.py` - Updated to support both modes
- `zelda_game_llm_integration.py` - Uses configuration
- `zelda_game_with_llm_npc.py` - Shows current mode on startup

## How to Use

### 1. Test Your Setup
```bash
python test_tool_calls.py
```

This will verify that:
- LM Studio is running
- Your model supports tool calls
- The NPC responds correctly to commands

### 2. Configure Mode
Edit `llm_config.py`:

```python
# Use tool calls (recommended)
USE_TOOL_CALLS = True

# Or fallback to JSON parsing
USE_TOOL_CALLS = False
```

### 3. Run the Game
```bash
python zelda_game_with_llm_npc.py
```

The startup will show which mode is active.

## LM Studio Setup for Tool Calls

### 1. Model Requirements
- Use a model that supports function calling (Qwen3 7B works well)
- Make sure the model is properly loaded

### 2. Expected Behavior
- **Before**: You see `tool_calls: []` in LM Studio logs
- **After**: You see proper `tool_calls` with function names and arguments

### 3. Troubleshooting

**If tool calls test fails:**
1. Check LM Studio is running at `http://127.0.0.1:1234`
2. Verify your model supports function calling
3. Try reloading the model in LM Studio
4. Set `USE_TOOL_CALLS = False` as fallback

**If responses seem wrong:**
1. Check the system prompt is loading correctly
2. Verify the function definitions match your needs
3. Look at the debug output to see what the model is receiving

## Benefits You'll See

### Cleaner LM Studio Logs
**Before:**
```
tool_calls: []
content: {"action":"say","args":{"text":"What do you want?"}}
```

**After:**
```
tool_calls: [
  {
    "function": {
      "name": "say",
      "arguments": "{\"text\":\"What do you want?\"}"
    }
  }
]
```

### More Reliable Parsing
- No more malformed JSON issues
- No extra text before/after JSON
- Structured function calls guaranteed

### Better Development Experience
- Easier to debug function calls
- Clear separation between dialogue and actions
- More predictable model behavior

## Rollback Plan

If you need to go back to the old system:

1. Set `USE_TOOL_CALLS = False` in `llm_config.py`
2. The game will automatically use the old JSON parsing method
3. All existing functionality remains the same

## New Feature: Dialogue History

### What's New
The NPCs now have **conversation memory**! They remember what was said earlier and respond appropriately.

### How It Works
- Tracks last 10 dialogue exchanges between player and NPC
- Sends conversation context to LLM with each decision
- NPCs can reference previous parts of the conversation
- No more repetitive or confused responses

### Example
```
Player: "hello"
NPC: "What do you want?"
Player: "what are you selling?"
NPC: "Potions, swords, armor."
Player: "how much for a health potion?"
NPC: "Five gold pieces."
Player: "I'll take two"
NPC: "That'll be ten gold. Here you go." // ← Remembers the price!
```

### Debug Output
You'll see dialogue context in the debug logs:
```
DEBUG: Dialogue context being sent to LLM:
RECENT CONVERSATION:
Player: "hello"
Garruk Ironhand: "What do you want?"
Player: "what are you selling?"
Garruk Ironhand: "Potions, swords, armor."
```

## Next Steps

Once tool calls are working:

1. You can customize the functions in `npc/llm_client_tool_calls.py`
2. Add new actions by updating the `_define_tools()` method
3. Modify the system prompt in `lm_studio_system_prompt_tool_calls.txt`
4. Consider adding more sophisticated function parameters
5. Test the dialogue history with `python test_dialogue_history.py`

The system is designed to be backward compatible, so you can switch modes anytime during development.