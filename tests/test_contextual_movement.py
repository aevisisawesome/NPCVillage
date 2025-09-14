#!/usr/bin/env python3
"""
Demonstrate how the LLM should choose different movement distances based on context.
"""

def demonstrate_contextual_movement():
    """Show examples of how different phrases should map to movement types"""
    
    print("🎭 Contextual Movement Examples")
    print("=" * 50)
    
    examples = [
        # Short movements (0.5 tiles = 16 pixels)
        ("step aside", "move_short", "Polite request for small adjustment"),
        ("move a bit", "move_short", "Small distance implied"),
        ("scoot over", "move_short", "Casual, small movement"),
        ("shift slightly", "move_short", "Minimal adjustment"),
        
        # Medium movements (1.0 tiles = 32 pixels) 
        ("move east", "move_dir", "Standard directional command"),
        ("go north", "move_dir", "Basic movement request"),
        ("move over there", "move_dir", "General movement"),
        ("walk to the side", "move_dir", "Normal walking distance"),
        
        # Long movements (3.0 tiles = 96 pixels)
        ("walk away", "move_long", "Significant distance implied"),
        ("move far", "move_long", "Explicitly requesting distance"),
        ("go over there", "move_long", "Pointing to distant location"),
        ("back up", "move_long", "Creating substantial space"),
        ("get out of the way", "move_long", "Dramatic movement needed"),
    ]
    
    print("Player Phrase → Expected Action → Reasoning")
    print("-" * 50)
    
    for phrase, action, reasoning in examples:
        distance = {
            "move_short": "16px (0.5 tiles)",
            "move_dir": "32px (1.0 tiles)", 
            "move_long": "96px (3.0 tiles)"
        }[action]
        
        print(f"'{phrase}' → {action} → {distance}")
        print(f"  Reasoning: {reasoning}")
        print()
    
    print("🎯 LLM Decision Process:")
    print("1. Analyze player's language for distance cues")
    print("2. Consider context (politeness, urgency, space needed)")
    print("3. Choose appropriate movement action:")
    print("   - Subtle words → move_short")
    print("   - Standard words → move_dir") 
    print("   - Dramatic words → move_long")
    
    print(f"\n📋 JSON Schema Updated:")
    print("The LLM now has these movement options:")
    print('- {"action":"move_short","args":{"direction":"N|E|S|W"}}')
    print('- {"action":"move_dir","args":{"direction":"N|E|S|W"}}')
    print('- {"action":"move_long","args":{"direction":"N|E|S|W"}}')
    
    print(f"\n🎮 In Practice:")
    print("Player: 'Could you step aside please?'")
    print("→ LLM chooses move_short")
    print("→ NPC moves 16 pixels (subtle, polite)")
    print()
    print("Player: 'Move east'") 
    print("→ LLM chooses move_dir")
    print("→ NPC moves 32 pixels (standard movement)")
    print()
    print("Player: 'Get out of my way!'")
    print("→ LLM chooses move_long") 
    print("→ NPC moves 96 pixels (dramatic, creates space)")


if __name__ == "__main__":
    demonstrate_contextual_movement()