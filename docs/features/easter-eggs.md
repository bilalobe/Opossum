# Easter Eggs

## National Opossum Day (October 18)

Every year on October 18, Opossum Search celebrates National Opossum Day with a special Easter egg that activates automatically for all users.

### Activation

This Easter egg is time-triggered and automatically activates when:
- The date is October 18 (any year)
- Any search query is performed

### Features

When activated, the following special features appear:

1. **Festive UI Elements**
   - The standard logo is replaced with a party hat-wearing opossum
   - Search results are accompanied by small animated opossums that scurry across the screen
   - Confetti animation plays on the first search of the day

2. **Special Responses**
   - Queries receive opossum-themed responses, regardless of the question
   - The system adds "playing possum" jokes to responses
   - Easter egg text appears in a special purple font

3. **Hidden Command: "possum party"**
   - Typing "possum party" triggers a full-screen animation of dancing opossums
   - This command unlocks a temporary "opossum mode" for the remainder of the session
   - In "opossum mode", all error messages are replaced with opossum memes

### Technical Implementation

```python
# app/features/easter_eggs.py
def check_for_easter_eggs(request_date, query):
    """Check if any Easter eggs should be activated"""
    
    # Check for National Opossum Day (October 18)
    if request_date.month == 10 and request_date.day == 18:
        return {
            "easter_egg": "national_opossum_day",
            "activate": True,
            "ui_theme": "party_opossum",
            "response_modifiers": ["opossum_jokes", "purple_text"],
            "animations": ["confetti", "scurrying_opossums"]
        }
    
    # Check for "possum party" command
    if query.lower() == "possum party":
        return {
            "easter_egg": "possum_party",
            "activate": True,
            "special_mode": "opossum_mode",
            "animation": "dancing_opossums",
            "duration": "session"
        }
    
    return {"activate": False}
```

### User Discovery

This Easter egg is deliberately undocumented in the user-facing documentation to encourage discovery. However, subtle hints appear throughout the application starting on October 1:

- The 'O' in the Opossum Search logo subtly changes to have a small tail
- The loading animation occasionally shows a brief opossum silhouette
- Help documentation updated with the cryptic message "Something special happens when opossums celebrate..."

### History

This Easter egg was added in version 0.8.3 (September 2024) and has been a beloved tradition ever since. Each year, new opossum animations and jokes are added to keep the experience fresh.

## Additional Easter Eggs

Opossum Search contains several other Easter eggs:

- April Fool's Day Reversal - All search results are delivered in reverse order
- Developer Mode - Activated by the Konami code
- Hidden Terminal - A simulated terminal accessed through a specific key combination