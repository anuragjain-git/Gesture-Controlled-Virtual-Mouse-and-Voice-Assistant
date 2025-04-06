# File: threads.py
# Purpose: Manage all thread-related functionalities

import queue
import time
from threading import Thread
import app

from voice_assistant.features.speech_engine import record_audio
from voice_assistant.features.constants import WAKE_WORDS

# A thread-safe queue for commands from both audio and chat.
command_queue = queue.Queue()

def audio_listener():
    """Continuously listens for audio commands and puts them in the queue."""
    while True:
        voice_data = record_audio()
        if voice_data:
            # Only add if wake word is present to reduce unnecessary processing.
            if any(wake in voice_data for wake in WAKE_WORDS):
                command_queue.put(voice_data)

def chat_reader():
    """Continuously checks for new chat input and puts them in the queue."""
    while True:
        if app.ChatBot.isUserInput():
            voice_data = app.ChatBot.popUserInput()
            if voice_data:
                command_queue.put(voice_data)
        time.sleep(0.2)  # Check frequently without overloading the CPU.

def start_threads():
    """Start the threads for handling audio and chat input."""
    Thread(target=audio_listener, daemon=True).start()
    Thread(target=chat_reader, daemon=True).start()
    print("Background threads started.")