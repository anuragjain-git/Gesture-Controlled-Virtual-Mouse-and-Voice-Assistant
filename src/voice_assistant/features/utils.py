# File: utils.py
# Purpose: Utility functions used across the assistant

import pyttsx3
from datetime import date, datetime
import app
import sys

# Global objects
engine = pyttsx3.init()
voices = engine.getProperty("voices")
engine.setProperty("voice", voices[0].id)
today = date.today()

def reply(text):
    """Sends a response to both the GUI and TTS, and logs output to the console."""
    try:
        app.ChatBot.addAppMsg(text)
    except Exception as e:
        print("GUI Error:", e)
    print("[Reply]:", text)
    try:
        engine.say(text)
        engine.runAndWait()
    except Exception as e:
        print("TTS Error:", e)

def wish():
    """Greets the user based on current time."""
    hour = datetime.now().hour
    greeting = (
        "Good Morning"
        if hour < 12
        else "Good Afternoon" if hour < 18 else "Good Evening"
    )
    reply(f"{greeting}! I am Echo, how can I assist you?")

def warm_up():
    """Primes the TTS engine with a quick test phrase."""
    try:
        engine.say("Initialization complete.")
        engine.runAndWait()
    except Exception as e:
        print("TTS warm-up error:", e)
    print("Warm-up complete.")