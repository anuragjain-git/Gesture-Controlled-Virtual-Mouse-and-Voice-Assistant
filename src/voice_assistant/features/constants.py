# File: constants.py
# Purpose: Store all constants used throughout the application

# Wake words
WAKE_WORDS = ["echo", "eco", "ecco", "eko", "eoco", "eeco", "hey echo", "hey eco"]

# Command synonyms for intent recognition
COMMAND_SYNONYMS = {
    "search": ["search", "find", "look"],
    "file":["file", "folder", "create", "move", "back", "go", "parent", "delete"],
    "open": ["open", "launch", "start"],
    "time": ["time", "clock"],
    "date": ["date", "today"],
    "copy": ["copy"],
    "paste": ["paste"],
    "exit": ["exit", "terminate", "stop", "close"],
    "mode": ["turn", "turn on", "turnon", "switch", "switchon", "switch on", "switch to"]
    # Add more intents and synonyms as needed
}

IS_BROWSING = False
SELF_MODE = False