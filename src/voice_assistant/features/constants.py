# File: constants.py
# Purpose: Store all constants used throughout the application

# Wake words
WAKE_WORDS = ["echo", "eco", "ecco", "eko", "eoco", "eeco", "hey echo", "hey eco"]

# Command synonyms for intent recognition
COMMAND_SYNONYMS = {
    "search": ["search", "find", "look"],
    "open": ["open", "launch", "start"],
    "time": ["time", "clock"],
    "date": ["date", "today"],
    "copy": ["copy"],
    "paste": ["paste"],
    "exit": ["exit", "terminate", "stop", "close"],
    # Add more intents and synonyms as needed
}